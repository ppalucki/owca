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
import resource
from abc import ABC, abstractmethod
from typing import Optional, Dict, Tuple, List

from owca import platforms, nodes, storage
from owca.allocators import AllocationConfiguration, TasksAllocations
from owca.containers import ContainerManager, Container
from owca.detectors import TasksMeasurements, TasksResources, TasksLabels
from owca.logger import trace
from owca.mesos import create_metrics, sanitize_mesos_label
from owca.metrics import Metric, MetricType
from owca.nodes import Task
from owca.resctrl import check_resctrl, get_max_rdt_values, cleanup_resctrl
from owca.security import are_privileges_sufficient
from owca.storage import MetricPackage

log = logging.getLogger(__name__)


class Runner(ABC):
    """Base class for main loop run that is started by main entrypoint."""

    @abstractmethod
    def run(self):
        ...


class BaseRunnerMixin:
    """Provides common functionality for both Allocator and Detector.
    - configure_rdt based on self.rdt_enabled property
    - wait_or_finish based on self.action_delay property
    - includes container manager to sync container state
    - prepare necessary data for allocation and detection logic (_prepare_task_data)
    - metrics_storage and extra_labels for input data labeling and storing
    """

    def __init__(self,
                 rdt_enabled: bool,
                 rdt_mb_control_enabled: bool,
                 action_delay: float,
                 allocation_configuration: Optional[AllocationConfiguration] = None):
        platform_cpus, _, platform_sockets = platforms.collect_topology_information()
        self.containers_manager = ContainerManager(
            rdt_enabled,
            rdt_mb_control_enabled,
            platform_cpus=platform_cpus,
            allocation_configuration=allocation_configuration
        )

        # Special fields that are defined in is defined by mixed dataclass as well.
        # There are redefined again to make that explicit in BaseRunnerMixin
        self._rdt_enabled = rdt_enabled
        self._allocation_configuration = allocation_configuration
        self._action_delay = action_delay

        # statistics state
        self._anomaly_last_occurrence = None
        self._anomaly_counter = 0
        self._allocations_counter = 0
        self._allocations_errors = 0
        self._rdt_mb_control_enabled = rdt_mb_control_enabled
        self._last_iteration = time.time()

    def configure_rdt(self, rdt_enabled, ignore_privileges_check: bool) -> bool:
        """Check required permission for using rdt and initialize subsystem.
        Returns False, if rdt wasn't properly configured. """
        if rdt_enabled and not check_resctrl():
            return False
        elif not rdt_enabled:
            log.warning('Rdt disabled. Skipping collecting measurements '
                        'and resctrl synchronization')
            self._rdt_mb_control_enabled = False
        else:
            # Resctrl is enabled and available - cleanup after a previous run.
            platform, _, _ = platforms.collect_platform_information()

            if self._rdt_mb_control_enabled and not platform.rdt_mb_control_enabled:
                raise Exception("RDT MB control is not support by platform!")
            elif self._rdt_mb_control_enabled is None:
                self._rdt_mb_control_enabled = platform.rdt_mb_control_enabled
            else:
                assert self._rdt_mb_control_enabled is False

            root_rtd_l3, root_rdt_mb = get_max_rdt_values(platform.rdt_cbm_mask, platform.sockets)
            if self._allocation_configuration is not None:
                if self._allocation_configuration.default_rdt_l3 is not None:
                    root_rtd_l3 = self._allocation_configuration.default_rdt_l3
                if self._allocation_configuration.default_rdt_mb is not None:
                    root_rdt_mb = self._allocation_configuration.default_rdt_mb
            if not platform.rdt_mb_control_enabled:
                root_rdt_mb = None
                log.warning('Rdt enabled, but RDT memory bandwidth (MB) allocation does not work.')
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

    def get_internal_metrics(self, tasks, durations: Dict[str, float]) -> Dict[str, float]:
        """Internal owca metrics."""

        # Iteration_duration.
        now = time.time()
        iteration_duration = now - self._last_iteration
        self._last_iteration = now

        durations['iteration'] = iteration_duration
        durations['sleep'] = self._action_delay

        # Memory usage.
        memory_usage_rss_self = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        memory_usage_rss_children = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
        memory_usage_rss = memory_usage_rss_self + memory_usage_rss_children

        metrics = [
            Metric(name='owca_up', type=MetricType.COUNTER, value=time.time()),
            Metric(name='owca_tasks', type=MetricType.GAUGE, value=len(tasks)),
            Metric(name='owca_memory_usage_bytes', type=MetricType.GAUGE,
                   value=int(memory_usage_rss*1024)),
        ]

        for duration_name, duration_value in sorted(durations.items()):
            metrics.append(
                Metric(name='owca_duration_seconds',
                       type=MetricType.GAUGE, value=duration_value,
                       labels=dict(function=duration_name),
                       ),
            )

        return metrics

    def get_anomalies_statistics_metrics(self, anomalies, detect_duration=None):
        """Extra external plugin anomaly statistics."""
        if len(anomalies):
            self._anomaly_last_occurrence = time.time()
            self._anomaly_counter += len(anomalies)

        statistics_metrics = [
            Metric(name='anomaly_count', type=MetricType.COUNTER, value=self._anomaly_counter),
        ]
        if self._anomaly_last_occurrence:
            statistics_metrics.extend([
                Metric(name='_anomaly_last_occurrence', type=MetricType.COUNTER,
                       value=self._anomaly_last_occurrence),
            ])
        if detect_duration is not None:
            statistics_metrics.extend([
                Metric(name='detect_duration', type=MetricType.GAUGE, value=detect_duration)
            ])
        return statistics_metrics

    def get_allocations_statistics_metrics(self, tasks_allocations,
                                           allocation_duration, allocations_errors):
        """Extra external plugin allocaton statistics."""
        if len(tasks_allocations):
            self._allocations_counter += len(tasks_allocations)
            self._allocations_errors += len(allocations_errors)

        statistics_metrics = [
            Metric(name='allocations_count', type=MetricType.COUNTER,
                   value=self._allocations_counter),
            Metric(name='_allocations_errors', type=MetricType.COUNTER,
                   value=self._allocations_errors),
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
        get_tasks_start = time.time()
        tasks = node.get_tasks()
        get_tasks_duration = time.time() - get_tasks_start

        # Keep sync of found tasks and internally managed containers.
        sync_duration_start = time.time()
        containers = self.containers_manager.sync_containers_state(tasks)
        sync_duration = time.time() - sync_duration_start

        # Platform information
        collect_platform_information_start = time.time()
        platform, platform_metrics, platform_labels = platforms.collect_platform_information(
            self._rdt_enabled)
        collect_platform_information_duration = time.time() - collect_platform_information_start

        # Common labels
        common_labels = dict(platform_labels, **extra_labels)

        # Tasks informations
        prepare_task_data_start = time.time()
        (tasks_metrics, tasks_measurements, tasks_resources, tasks_labels,
         current_tasks_allocations) = _prepare_tasks_data(containers)
        prepare_task_data_duration = time.time() - prepare_task_data_start

        durations = dict(
            get_tasks=get_tasks_duration,
            sync=sync_duration,
            collect_platform_information=collect_platform_information_duration,
            prepare_task_data=prepare_task_data_duration,
        )
        internal_metrics = self.get_internal_metrics(tasks, durations)

        metrics_package = MetricPackage(metrics_storage)
        metrics_package.add_metrics(internal_metrics)
        metrics_package.add_metrics(platform_metrics)
        metrics_package.add_metrics(tasks_metrics)
        metrics_package.send(common_labels)

        return (platform, tasks_measurements, tasks_resources,
                tasks_labels, current_tasks_allocations, common_labels)

    def cleanup(self):
        self.containers_manager.cleanup()


@trace(log, verbose=False)
def _prepare_tasks_data(containers: Dict[Task, Container]) -> \
        Tuple[List[Metric], TasksMeasurements, TasksResources, TasksLabels, TasksAllocations]:
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
        if not task_measurements:
            log.warning('there is not measurments collected for container %r - ignoring!',
                        container)
            continue

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
