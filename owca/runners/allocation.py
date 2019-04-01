# Copyright (c) 2019 Intel Corporation
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
from owca import resctrl
from owca.allocations import AllocationsDict, InvalidAllocations, AllocationValue
from owca.allocators import TasksAllocations, AllocationConfiguration, AllocationType, Allocator, \
    TaskAllocations, RDTAllocation
from owca.cgroups_allocations import QuotaAllocationValue, SharesAllocationValue
from owca.containers import Container
from owca.detectors import convert_anomalies_to_metrics, \
    update_anomalies_metrics_with_task_information
from owca.metrics import Metric, MetricType
from owca.resctrl_allocations import (RDTAllocationValue, RDTGroups, validate_mb_string,
                                      validate_l3_string)
from owca.runners.detection import AnomalyStatistics
from owca.runners.measurement import MeasurementRunner
from owca.storage import MetricPackage

log = logging.getLogger(__name__)

# Helper type to have a mapping from type to callable that creates proper AllocationValue.
# Used by Allocation to AllocationValue converters. First argument is a raw (simple value)
# and third (dict) is an common_labels.
RegistryType = Dict[AllocationType, Callable[[Any, Container, dict], AllocationValue]]


class TaskAllocationsValues(AllocationsDict):
    """Subclass of generic AllocationsDict that is dedicated to be used only for specific case
    at second level mapping between, task and and its allocations.
    Provides an staticmethod as constructor.
    """

    @staticmethod
    def create(task_allocations: TaskAllocations,
               container: Container,
               registry: RegistryType,
               common_labels: Dict[str, str]) -> 'TaskAllocationsValues':
        """Factory function for TaskAllocationsValues based on raw task_allocations
        and container, registry and common_labels.

        Registry is used to map specific kinds of allocations to proper constructors.
        """
        simple_dict = {}
        for allocation_type, raw_value in task_allocations.items():
            if allocation_type not in registry:
                raise InvalidAllocations('unknown allocation type')
            constructor = registry[allocation_type]
            allocation_value = constructor(raw_value, container, common_labels)
            simple_dict[allocation_type] = allocation_value
        return TaskAllocationsValues(simple_dict)


class TasksAllocationsValues(AllocationsDict):
    """Subclass of AllocationsDict that is dedicate to be used only for specific case
    of first level mapping between, many tasks and TaskAllocationsValues.
    Provides an staticmethod as constructor.
    """

    @staticmethod
    def create(tasks_allocations: TasksAllocations, containers, platform) \
            -> 'TasksAllocationsValues':
        """Convert plain raw object TasksAllocations to boxed intelligent AllocationsDict
        that can be serialized to metrics, validated and can perform contained allocations.

        Beneath simple tasks allocations objects are augmented using data
        from runner: containers and platform to provide context
        to implement their responsibilities.

        Additionally local object rdt_groups is created to limit number of created RDTGroups
        and optimize writes for schemata file.
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
                container_labels = dict(container_name=container.container_name, task=task_id)
                allocation_value = TaskAllocationsValues.create(
                    task_allocations, container, registry, container_labels)
                allocation_value.validate()
                simple_dict[task_id] = allocation_value

        return TasksAllocationsValues(simple_dict)


class AllocationRunner(MeasurementRunner):
    """Runner responsible for getting information about tasks from node,
    calling allocate() callback on allocator, performing returning allocations
    and storing all allocation related metrics in allocations_storage.

    Because Allocator interface is also detector, we store serialized detected anomalies
    in anomalies_storage and all other measurements in metrics_storage.

    Switching rdt_enabled to False disables both monitoring and allocation of Intel RDT resources.
    rdt_mb_control_enabled allows to force enabling or disabling MBA control (default to auto
    detection based on platform capabilities).

    extra_labels are labels that are attached to every metric  and ignore_privileges_checks
    disabled checking precondition of having access to cgroups/resctrl.

    allocation_configuration - allow to specify parameters dedicated for allocation control.
    """

    def __init__(
            self,
            node: nodes.Node,
            allocator: Allocator,
            metrics_storage: storage.Storage,
            anomalies_storage: storage.Storage,
            allocations_storage: storage.Storage,
            action_delay: float = 1.,  # [s]
            rdt_enabled: bool = True,
            rdt_mb_control_enabled: bool = None,  # None means it will be based on availability
            # in platform (autodetect).
            extra_labels: Dict[str, str] = None,
            ignore_privileges_check: bool = False,
            allocation_configuration: AllocationConfiguration = None,
    ):

        self._allocation_configuration = allocation_configuration or AllocationConfiguration()

        super().__init__(node, metrics_storage, action_delay, rdt_enabled,
                         extra_labels, ignore_privileges_check,
                         allocation_configuration=self._allocation_configuration)

        # Allocation specific.
        self._allocator = allocator
        self._allocations_storage = allocations_storage
        self._rdt_mb_control_enabled = rdt_mb_control_enabled

        # Anomaly.
        self._anomalies_storage = anomalies_storage
        self._anomalies_statistics = AnomalyStatistics()

        # Internal allocation statistics
        self._allocations_counter = 0
        self._allocations_errors = 0

    def _initialize_rdt(self):
        platform, _, _ = platforms.collect_platform_information()

        if self._rdt_mb_control_enabled and not platform.rdt_information.rdt_mb_control_enabled:
            # Some wanted unavailable feature - halt.
            raise Exception("RDT MB control is not supported by platform!")
        elif self._rdt_mb_control_enabled is None:
            # Auto detection of rdt mb control.
            self._rdt_mb_control_enabled = platform.rdt_information.rdt_mb_control_enabled

        root_rdt_l3, root_rdt_mb = resctrl.get_max_rdt_values(
            platform.rdt_information.cbm_mask,
            platform.sockets
        )
        # override max values with values from allocation configuration
        if self._allocation_configuration.default_rdt_l3 is not None:
            root_rdt_l3 = self._allocation_configuration.default_rdt_l3
        if self._allocation_configuration.default_rdt_mb is not None:
            root_rdt_mb = self._allocation_configuration.default_rdt_mb

        # Do not set mb default value if feature is not available
        # (only for case that was auto detected)
        if not platform.rdt_information.rdt_mb_control_enabled:
            root_rdt_mb = None
            log.warning('RDT MB control enabled, but RDT memory'
                        'bandwidth (MB) allocation does not work.')
        else:
            # not enabled - so do not set it
            if not self._rdt_mb_control_enabled:
                root_rdt_mb = None

        if root_rdt_l3 is not None:
            validate_l3_string(root_rdt_l3, platform.sockets,
                               platform.rdt_information.cbm_mask,
                               platform.rdt_information.min_cbm_bits)

        if root_rdt_mb is not None:
            validate_mb_string(root_rdt_mb, platform.sockets)

        resctrl.cleanup_resctrl(root_rdt_l3, root_rdt_mb)

    def _run_body(self,
                  containers, platform,
                  tasks_measurements, tasks_resources,
                  tasks_labels, common_labels):
        """Allocator callback body."""

        current_allocations = _get_tasks_allocations(containers)

        # Allocator callback
        allocate_start = time.time()
        new_allocations, anomalies, extra_metrics = self._allocator.allocate(
            platform, tasks_measurements, tasks_resources, tasks_labels,
            current_allocations)
        allocate_duration = time.time() - allocate_start

        log.debug('Anomalies detected: %d', len(anomalies))
        log.debug('Current allocations: %s', current_allocations)

        # Create context aware allocations objects for current allocations.
        current_allocations_values = TasksAllocationsValues.create(
            current_allocations, self._containers_manager.containers, platform)

        # Handle allocations: calculate changeset and target allocations.
        allocations_changeset_values = None
        target_allocations_values = current_allocations_values
        try:
            # Create and validate context aware allocations objects for new allocations.
            log.debug('New allocations: %s', new_allocations)
            new_allocations_values = TasksAllocationsValues.create(
                new_allocations, self._containers_manager.containers, platform)
            new_allocations_values.validate()

            # Calculate changeset and target_allocations.
            if new_allocations_values is not None:
                target_allocations_values, allocations_changeset_values = \
                    new_allocations_values.calculate_changeset(current_allocations_values)
                target_allocations_values.validate()

            self._allocations_counter += len(new_allocations)

        except InvalidAllocations as e:
            # Handle any allocation validation error.
            # Log errors and restore current to generate proper metrics.
            log.error('Invalid allocations: %s', str(e))
            log.warning('Ignoring all allocations in this iteration due to validation error!')
            self._allocations_errors += 1
            target_allocations_values = current_allocations_values

        # Handle allocations: perform allocations based on changeset.
        if allocations_changeset_values:
            log.debug('Allocations changeset: %s', allocations_changeset_values)
            log.info('Performing allocations on %d tasks.', len(allocations_changeset_values))
            allocations_changeset_values.perform_allocations()

        # Prepare anomaly metrics.
        anomaly_metrics = convert_anomalies_to_metrics(anomalies, tasks_labels)
        update_anomalies_metrics_with_task_information(anomaly_metrics, tasks_labels)

        # Store anomalies information
        anomalies_package = MetricPackage(self._anomalies_storage)
        anomalies_package.add_metrics(
            anomaly_metrics,
            extra_metrics,
            self._anomalies_statistics.get_metrics(anomalies)
        )
        anomalies_package.send(common_labels)

        # Prepare allocations metrics.
        allocations_metrics = target_allocations_values.generate_metrics()
        allocations_statistic_metrics = _get_allocations_statistics_metrics(
            self._allocations_counter, self._allocations_errors, allocate_duration)

        # Store allocations metrics.
        allocations_package = MetricPackage(self._allocations_storage)
        allocations_package.add_metrics(
            allocations_metrics,
            extra_metrics,
            allocations_statistic_metrics,
        )
        allocations_package.send(common_labels)


def _get_tasks_allocations(containers) -> TasksAllocations:
    tasks_allocations: TasksAllocations = {}
    for task, container in containers.items():
        task_allocations = container.get_allocations()
        tasks_allocations[task.task_id] = task_allocations
    return tasks_allocations


def _get_allocations_statistics_metrics(allocations_count, allocations_errors, allocation_duration):
    """Extra external plugin allocations statistics."""

    metrics = [
        Metric(name='allocations_count', type=MetricType.COUNTER,
               value=allocations_count),
        Metric(name='allocations_errors', type=MetricType.COUNTER,
               value=allocations_errors),
    ]

    if allocation_duration is not None:
        metrics.extend([
            Metric(name='allocation_duration', type=MetricType.GAUGE,
                   value=allocation_duration)
        ])

    return metrics
