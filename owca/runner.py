# Copyright (c) 2018 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.


import logging
import time
from abc import ABC, abstractmethod
from typing import List, Dict, Optional, Tuple

from dataclasses import dataclass, field

from owca import detectors, nodes
from owca import platforms
from owca import storage
from owca.allocations import AllocationsDict
from owca.allocators import Allocator, TasksAllocations, AllocationConfiguration
from owca.containers import ContainerManager, Container
from owca.detectors import (TasksMeasurements, TasksResources,
                            TasksLabels, convert_anomalies_to_metrics,
                            update_anomalies_metrics_with_task_information
                            )
from owca.logger import trace
from owca.mesos import create_metrics, sanitize_mesos_label
from owca.metrics import Metric, MetricType
from owca.nodes import Task, TaskId
from owca.resctrl import check_resctrl, cleanup_resctrl, get_max_rdt_values
from owca.security import are_privileges_sufficient
from owca.storage import MetricPackage

log = logging.getLogger(__name__)


class Runner(ABC):
    """Base class for main loop run that is started by main entrypoint."""

    @abstractmethod
    def run(self):
        ...


class BaseRunnerMixin:
    """Provides common functionallity for both Allocator and Detector.
    - configure_rdt based on self.rdt_enabled property
    - wait_or_finish based on self.action_delay property
    - includes container manager to sync container state
    - prepare nessesary data for allocation and detection logic (_prepare_task_data)
    - metrics_storage and extra_labels for input data labeling and storing
    """

    def __init__(self,
                 rdt_enabled: bool,
                 rdt_mb_control_enabled: bool,
                 allocation_configuration: Optional[AllocationConfiguration] = None):
        platform_cpus, _, platform_sockets = platforms.collect_topology_information()
        self.containers_manager = ContainerManager(
            rdt_enabled,
            rdt_mb_control_enabled,
            platform_cpus=platform_cpus,
            allocation_configuration=allocation_configuration
        )

        # statistics state
        self.anomaly_last_occurence = None
        self.anomaly_counter = 0
        self.allocations_counter = 0
        self.rdt_enabled = rdt_enabled  # as mixin it can override the value from base class
        self.rdt_mb_control_enabled = rdt_mb_control_enabled
        self.allocation_configuration = allocation_configuration

    def configure_rdt(self, rdt_enabled, ignore_privileges_check: bool):
        """Check required permission for using rdt and initilize subsystem.
        Returns False, if rdt wasn't properly configured. """
        if rdt_enabled and not check_resctrl():
            return False
        elif not rdt_enabled:
            log.warning('Rdt disabled. Skipping collecting measurements '
                        'and resctrl synchronization')
        else:
            # Resctrl is enabled and available - cleanup previous runs.
            platform, _, _ = platforms.collect_platform_information()
            max_rdt_l3, max_rdt_mb = get_max_rdt_values(platform.rdt_cbm_mask, platform.sockets)
            root_rtd_l3 = self.allocation_configuration.default_rdt_l3 or max_rdt_l3
            if self.rdt_mb_control_enabled:
                root_rdt_mb = self.allocation_configuration.default_rdt_mb or max_rdt_mb
            else:
                root_rdt_mb = None
            cleanup_resctrl(root_rtd_l3, root_rdt_mb)

        if ignore_privileges_check:
            return True

        if not are_privileges_sufficient():
            log.critical("Impossible to use perf_event_open. You need to: adjust "
                         "/proc/sys/kernel/perf_event_paranoid; or has CAP_DAC_OVERRIDE capability"
                         " set. You can run process as root too. See man 2 perf_event_open for "
                         "details.")
            return False

        return True

    def wait_or_finish(self, delay):
        """Decides how long one run takes and when to finish.
        TODO: handle graceful shutdown on signal
        """
        time.sleep(delay)
        return True

    def get_internal_metrics(self, tasks):
        """Internal owca metrics."""
        return [
            Metric(name='owca_up', type=MetricType.COUNTER, value=time.time()),
            Metric(name='owca_tasks', type=MetricType.GAUGE, value=len(tasks)),
        ]

    def get_anomalies_statistics_metrics(self, anomalies, detect_duration=None):
        """Extra external plugin anomaly statistics."""
        if len(anomalies):
            self.anomaly_last_occurence = time.time()
            self.anomaly_counter += len(anomalies)

        statistics_metrics = [
            Metric(name='anomaly_count', type=MetricType.COUNTER, value=self.anomaly_counter),
        ]
        if self.anomaly_last_occurence:
            statistics_metrics.extend([
                Metric(name='anomaly_last_occurence', type=MetricType.COUNTER,
                       value=self.anomaly_last_occurence),
            ])
        if detect_duration is not None:
            statistics_metrics.extend([
                Metric(name='detect_duration', type=MetricType.GAUGE, value=detect_duration)
            ])
        return statistics_metrics

    def get_allocations_statistics_metrics(self, tasks_allocations,
                                           allocation_duration, ignored_allocations_count: int):
        """Extra external plugin allocaton statistics."""
        if len(tasks_allocations):
            self.allocations_counter += len(tasks_allocations)

        statistics_metrics = [
            Metric(name='allocations_count', type=MetricType.COUNTER,
                   value=self.allocations_counter),
        ]

        if allocation_duration is not None:
            statistics_metrics.extend([
                Metric(name='allocation_duration', type=MetricType.GAUGE,
                       value=allocation_duration)
            ])

        return statistics_metrics

    @trace(log, verbose=False)
    def _prepare_input_data_and_send_metrics_package(self, node: nodes.Node,
                                                     metrics_storage: storage.Storage,
                                                     extra_labels: Dict[str, str]) -> \
            Tuple[platforms.Platform, TasksMeasurements, TasksResources, TasksLabels,
                  TasksAllocations, Dict[str, str]]:
        """Prepare data required for both detect() and allocate() methods."""

        # Collect information about tasks running on node.
        tasks = node.get_tasks()

        # Keep sync of found tasks and internally managed containers.
        containers = self.containers_manager.sync_containers_state(tasks)

        metrics_package = MetricPackage(metrics_storage)
        metrics_package.add_metrics(self.get_internal_metrics(tasks))

        # Platform information
        platform, platform_metrics, platform_labels = platforms.collect_platform_information(
            self.rdt_enabled)
        platform.update()
        metrics_package.add_metrics(platform_metrics)

        # Common labels
        common_labels = dict(platform_labels, **extra_labels)

        # Tasks informations
        (tasks_metrics, tasks_measurements, tasks_resources, tasks_labels,
         current_tasks_allocations) = _prepare_tasks_data(containers)
        metrics_package.add_metrics(tasks_metrics)
        metrics_package.send(common_labels)

        return (platform, tasks_measurements, tasks_resources,
                tasks_labels, current_tasks_allocations, common_labels)

    def cleanup(self):
        self.containers_manager.cleanup()


@trace(log, verbose=False)
def _prepare_tasks_data(containers: Dict[Task, Container]) -> Tuple[
        List[Metric], TasksMeasurements, TasksResources, TasksLabels, TasksAllocations]:
    """ Based on containers, preapre all nessesary data for allocation and detection logic,
    including, measurements, resources, labels and derived metrics.
    In runner to fullfil common data requirments for Allocator and Detector class.
    """
    # Prepare empty structures for return all the information.
    tasks_measurements: TasksMeasurements = {}
    tasks_resources: TasksResources = {}
    tasks_labels: TasksLabels = {}
    tasks_metrics: List[Metric] = []
    current_tasks_allocations: TasksAllocations = {}

    for task, container in containers.items():
        # Task measurements and mesurements based metrics.
        task_measurements = container.get_measurements()
        task_metrics = create_metrics(task_measurements)

        # Prepare tasks labels based on tasks metadata labels and task id.
        task_labels = {
            sanitize_mesos_label(label_key): label_value
            for label_key, label_value
            in task.labels.items()
        }
        task_labels['task_id'] = task.task_id

        # Task allocations.
        task_allocations = container.get_allocations()

        # Decorate metrics with task specifc labels.
        for task_metric in task_metrics:
            task_metric.labels.update(task_labels)

        # Aggregate over all tasks.
        tasks_labels[task.task_id] = task_labels
        tasks_measurements[task.task_id] = task_measurements
        tasks_resources[task.task_id] = task.resources
        tasks_metrics += task_metrics
        current_tasks_allocations[task.task_id] = task_allocations

    return (tasks_metrics, tasks_measurements, tasks_resources, tasks_labels,
            current_tasks_allocations)


@dataclass
class DetectionRunner(Runner, BaseRunnerMixin):
    """Watch over tasks running on this cluster on this node, collect observation
    and report externally (using storage) detected anomalies.
    """
    node: nodes.Node
    metrics_storage: storage.Storage
    anomalies_storage: storage.Storage
    detector: detectors.AnomalyDetector
    action_delay: float = 0.  # [s]
    rdt_enabled: bool = True
    extra_labels: Dict[str, str] = field(default_factory=dict)
    ignore_privileges_check: bool = False

    def __post_init__(self):
        BaseRunnerMixin.__init__(
            self,
            rdt_enabled=self.rdt_enabled,
            rdt_mb_control_enabled=False,
            allocation_configuration=None
        )

    def run(self):
        if not self.configure_rdt(self.rdt_enabled, self.ignore_privileges_check):
            return

        while True:
            # Prepare algorithm input data and send input based metrics.
            platform, tasks_measurements, \
                tasks_resources, tasks_labels, tasks_allocations, common_labels = \
                self._prepare_input_data_and_send_metrics_package(
                    self.node, self.metrics_storage, self.extra_labels)

            # Detector callback
            detect_start = time.time()
            anomalies, extra_metrics = self.detector.detect(
                platform, tasks_measurements, tasks_resources, tasks_labels)
            detect_duration = time.time() - detect_start
            log.debug('Anomalies detected (in %.2fs): %d', detect_duration, len(anomalies))

            # Prepare anomaly metrics
            anomaly_metrics = convert_anomalies_to_metrics(anomalies)
            update_anomalies_metrics_with_task_information(anomaly_metrics, tasks_labels)

            # Prepare and send all output (anomalies) metrics.
            anomalies_package = MetricPackage(self.anomalies_storage)
            anomalies_package.add_metrics(
                anomaly_metrics,
                extra_metrics,
                self.get_anomalies_statistics_metrics(anomalies, detect_duration)
            )
            anomalies_package.send(common_labels)

            if not self.wait_or_finish(self.action_delay):
                break

        self.cleanup()


def convert_to_allocations(tasks_allocations: TasksAllocations,
                           containers: Dict[TaskId, Container]) -> AllocationsDict:
    # TODO: use containers to build intelighent Allocation Objects values like
    # RDTAllocationValue based on RDTAllocation
    # CgroupAllocationValue based on cgroup: 34.
    # CgroupAllocationValue based on cgroup: 34.o
    # and so on...
    return AllocationsDict(tasks_allocations)




@dataclass
class AllocationRunner(Runner, BaseRunnerMixin):
    node: nodes.Node
    allocator: Allocator
    metrics_storage: storage.Storage
    anomalies_storage: storage.Storage
    allocations_storage: storage.Storage
    action_delay: float = 1.  # [s]
    rdt_enabled: bool = True
    rdt_mb_control_enabled: bool = False
    extra_labels: Dict[str, str] = field(default_factory=dict)
    ignore_privileges_check: bool = False
    allocation_configuration: AllocationConfiguration = \
        field(default_factory=AllocationConfiguration)

    def __post_init__(self):
        BaseRunnerMixin.__init__(
            self, self.rdt_enabled, self.rdt_mb_control_enabled, self.allocation_configuration)

    @trace(log)
    def run(self):
        if not self.configure_rdt(self.rdt_enabled, self.ignore_privileges_check):
            return

        while True:
            # Prepare algorithm inputs and send input based metrics.
            platform, tasks_measurements, tasks_resources, \
                tasks_labels, current_tasks_allocations, common_labels = \
                self._prepare_input_data_and_send_metrics_package(
                    self.node, self.metrics_storage, self.extra_labels)

            # Allocator callback
            allocate_start = time.time()
            new_tasks_allocations, anomalies, extra_metrics = self.allocator.allocate(
                platform, tasks_measurements, tasks_resources, tasks_labels,
                current_tasks_allocations)
            allocate_duration = time.time() - allocate_start

            log.debug('Anomalies detected: %d', len(anomalies))


            current_allocations = convert_to_allocations(current_tasks_allocations, 
                                                         self.containers_manager.containers)
            new_allocations = convert_to_allocations(new_tasks_allocations,
                                                     self.containers_manager.containers)



            target_allocations, allocations_changeset = current_allocations.merge_with_current(
                new_allocations)


            #### MAIN function
            allocations_changeset.perform_allocations()

            # Note: anomaly metrics include metrics found in ContentionAnomaly.metrics.
            anomaly_metrics = convert_anomalies_to_metrics(anomalies)
            update_anomalies_metrics_with_task_information(anomaly_metrics, tasks_labels)

            anomalies_package = MetricPackage(self.anomalies_storage)
            anomalies_package.add_metrics(self.get_anomalies_statistics_metrics(anomalies))
            anomalies_package.add_metrics(extra_metrics)
            anomalies_package.send(common_labels)

            # Store allocations information
            allocations_metrics = target_allocations.generate_metrics()
            allocations_package = MetricPackage(self.allocations_storage)
            allocations_package.add_metrics(
                allocations_metrics,
                extra_metrics,
                self.get_allocations_statistics_metrics(new_tasks_allocations,
                                                        allocate_duration),
            )
            allocations_package.send(common_labels)

            if not self.wait_or_finish(self.action_delay):
                break

        self.cleanup()
