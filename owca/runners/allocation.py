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
from typing import Dict, Callable, Any

from owca import nodes, storage, platforms
from owca.allocations import AllocationsDict, InvalidAllocations, AllocationValue
from owca.allocators import TasksAllocations, AllocationConfiguration, AllocationType, Allocator, \
    TaskAllocations, RDTAllocation
from owca.cgroups_allocations import QuotaAllocationValue, SharesAllocationValue
from owca.containers import Container
from owca.detectors import convert_anomalies_to_metrics, \
    update_anomalies_metrics_with_task_information
from owca.metrics import Metric, MetricType
from owca.resctrl import get_max_rdt_values, cleanup_resctrl
from owca.resctrl_allocations import RDTAllocationValue, RDTGroups
from owca.runners.detection import AnomalyStatistics
from owca.runners.measurement import MeasuringRunner
from owca.storage import MetricPackage

log = logging.getLogger(__name__)

RegistryType = Dict[AllocationType, Callable[[Any, Container, dict], AllocationValue]]


class TaskAllocationsValues(AllocationsDict):

    @staticmethod
    def create(task_allocations: TaskAllocations,
               container: Container,
               registry: RegistryType,
               common_labels: Dict[str, str]):
        simple_dict = {}
        for allocation_type, raw_value in task_allocations.items():
            if allocation_type not in registry:
                raise InvalidAllocations('unknown allocation type')
            constructor = registry[allocation_type]
            allocation_value = constructor(raw_value, container, common_labels)
            simple_dict[allocation_type] = allocation_value
        return TaskAllocationsValues(simple_dict)


class TasksAllocationsValues(AllocationsDict):

    @staticmethod
    def create(tasks_allocations: TasksAllocations, containers, platform):
        """Convert plain raw object TasksAllocations to boxed intelligent AllocationsDict
        that can be serialized to metrics, validated and perform contained allocations.

        Simple tasks allocations objects are augmented using runner and container manager
        context to implement their responsibilities.
        """

        # Shared object to optimize schemata write and detect CLOSids exhaustion.
        rdt_groups = RDTGroups(closids_limit=platform.rdt_information.num_closids)

        def rdt_allocation_value_constructor(rdt_allocation: RDTAllocation, container,
                                             common_labels):
            return RDTAllocationValue(
                container.container_name,
                rdt_allocation,
                container.resgroup,
                container.cgroup.get_pids,
                platform.sockets,
                platform.rdt_information.rdt_mb_control_enabled,
                platform.rdt_information.cbm_mask,
                platform.rdt_information.min_cbm_bits,
                common_labels=common_labels,
                rdt_groups=rdt_groups,
            )

        registry = {
            AllocationType.RDT: rdt_allocation_value_constructor,
            AllocationType.QUOTA: QuotaAllocationValue,
            AllocationType.SHARES: SharesAllocationValue,
        }

        task_id_to_containers = {task.task_id: container for task, container in containers.items()}
        simple_dict = {}
        for task_id, task_allocations in tasks_allocations.items():
            if task_id not in task_id_to_containers:
                raise InvalidAllocations('invalid task id %r' % task_id)
            else:
                container = task_id_to_containers[task_id]
                this_container_labels = dict(container_name=container.container_name, task=task_id)
                allocation_value = TaskAllocationsValues.create(
                    task_allocations, container, registry, this_container_labels)
                allocation_value.validate()
                simple_dict[task_id] = allocation_value

        return TasksAllocationsValues(simple_dict)


class AllocationRunner(MeasuringRunner):

    def __init__(self,
                 node: nodes.Node,
                 allocator: Allocator,
                 metrics_storage: storage.Storage,
                 anomalies_storage: storage.Storage,
                 allocations_storage: storage.Storage,
                 action_delay: float = 1.,  # [s]
                 rdt_enabled: bool = True,
                 rdt_mb_control_enabled: bool = None,  # None means will
                 extra_labels: Dict[str, str] = None,
                 ignore_privileges_check: bool = False,
                 allocation_configuration: AllocationConfiguration = None,
                 ):

        super().__init__(node, metrics_storage, action_delay, rdt_enabled,
                         extra_labels, ignore_privileges_check)

        # Allocation specific.
        self.allocator = allocator
        self.allocations_storage = allocations_storage
        self.rdt_mb_control_enabled = rdt_mb_control_enabled
        self.allocation_configuration = allocation_configuration

        # Anomaly.
        self.anomalies_storage = anomalies_storage
        self.anomalies_statistics = AnomalyStatistics()

        # Internal allocation statistics
        self._allocations_counter = 0
        self._allocations_errors = 0

    def _rdt_initialization(self):
        platform, _, _ = platforms.collect_platform_information()

        if self.rdt_mb_control_enabled and not platform.rdt_information.rdt_mb_control_enabled:
            raise Exception("RDT MB control is not support by platform!")
        elif self.rdt_mb_control_enabled is None:
            self.rdt_mb_control_enabled = platform.rdt_information.rdt_mb_control_enabled
        else:
            assert self.rdt_mb_control_enabled is False, 'assert explicit disabling'

        root_rtd_l3, root_rdt_mb = get_max_rdt_values(platform.rdt_information.cbm_mask,
                                                      platform.sockets)
        if self.allocation_configuration is not None:
            if self.allocation_configuration.default_rdt_l3 is not None:
                root_rtd_l3 = self.allocation_configuration.default_rdt_l3
            if self.allocation_configuration.default_rdt_mb is not None:
                root_rdt_mb = self.allocation_configuration.default_rdt_mb
        if not platform.rdt_information.rdt_mb_control_enabled:
            root_rdt_mb = None
            log.warning('Rdt enabled, but RDT memory bandwidth (MB) allocation does not work.')
        cleanup_resctrl(root_rtd_l3, root_rdt_mb)

    def _get_tasks_allocations(self, containers) -> TasksAllocations:
        tasks_allocations: TasksAllocations = {}
        for task, container in containers.items():
            task_allocations = container.get_allocations()
            tasks_allocations[task.task_id] = task_allocations
        return tasks_allocations

    def get_allocations_statistics_metrics(self, tasks_allocations,
                                           allocation_duration, allocations_errors):
        """Extra external plugin allocaton statistics."""
        if len(tasks_allocations):
            self._allocations_counter += len(tasks_allocations)
            self._allocations_errors += len(allocations_errors)

        statistics_metrics = [
            Metric(name='allocations_count', type=MetricType.COUNTER,
                   value=self._allocations_counter),
            Metric(name='allocations_errors', type=MetricType.COUNTER,
                   value=self._allocations_errors),
        ]

        if allocation_duration is not None:
            statistics_metrics.extend([
                Metric(name='allocation_duration', type=MetricType.GAUGE,
                       value=allocation_duration)
            ])

        return statistics_metrics

    def _run_body(self,
                  containers, platform,
                  tasks_measurements, tasks_resources,
                  tasks_labels, common_labels):
        """Allocator callback body."""

        current_tasks_allocations = self._get_tasks_allocations(containers)

        # Allocator callback
        allocate_start = time.time()
        new_tasks_allocations, anomalies, extra_metrics = self.allocator.allocate(
            platform, tasks_measurements, tasks_resources, tasks_labels,
            current_tasks_allocations)
        allocate_duration = time.time() - allocate_start

        log.debug('Anomalies detected: %d', len(anomalies))
        log.debug('Current allocations: %s', current_tasks_allocations)

        # Create context allocations objects for current allocations.
        current_allocations = TasksAllocationsValues.create(
            current_tasks_allocations, self.containers_manager.containers, platform)

        allocations_changeset = None
        target_allocations = current_allocations
        errors = []
        try:
            # Create and validate context allocations objects for new allocations.
            log.debug('New allocations: %s', new_tasks_allocations)
            new_allocations = TasksAllocationsValues.create(
                new_tasks_allocations, self.containers_manager.containers, platform)
            new_allocations.validate()

            # Update changeset and target_allocations, using information about new allocations.
            if new_allocations is not None:
                target_allocations, allocations_changeset = new_allocations.calculate_changeset(
                    current_allocations)
                target_allocations.validate()

        except InvalidAllocations as e:
            log.error('Invalid allocations: %s', str(e))
            errors = [str(e)]
            target_allocations = TasksAllocationsValues.create(
                current_tasks_allocations, self.containers_manager.containers, platform)

        if allocations_changeset:
            log.debug('Allocations changeset: %s', allocations_changeset)
            log.info('Performing allocations on %d tasks.', len(allocations_changeset))
            allocations_changeset.perform_allocations()

        # Note: anomaly metrics include metrics found in ContentionAnomaly.metrics.
        anomaly_metrics = convert_anomalies_to_metrics(anomalies)
        update_anomalies_metrics_with_task_information(anomaly_metrics, tasks_labels)

        # Store anomalies information
        anomalies_package = MetricPackage(self.anomalies_storage)
        anomalies_package.add_metrics(
            anomaly_metrics,
            extra_metrics,
            self.anomalies_statistics.get_metrics(anomalies)
        )
        anomalies_package.send(common_labels)

        # Store allocations information
        allocations_metrics = target_allocations.generate_metrics()
        allocations_package = MetricPackage(self.allocations_storage)

        allocations_statistic_metrics = self.get_allocations_statistics_metrics(
            new_tasks_allocations, allocate_duration, errors)
        allocations_package.add_metrics(
            allocations_metrics,
            extra_metrics,
            allocations_statistic_metrics,
        )
        allocations_package.send(common_labels)
