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
import copy
import logging
import math
from abc import ABC, abstractmethod
from enum import Enum
from pprint import pformat
from typing import List, Dict, Union, Tuple, Optional, Any, Type

from dataclasses import dataclass

from owca import platforms
from owca.detectors import TasksMeasurements, TasksResources, TasksLabels, Anomaly
from owca.logger import trace, TRACE
from owca.mesos import TaskId
from owca.metrics import Metric, MetricType
from owca.platforms import Platform

log = logging.getLogger(__name__)


class AllocationType(str, Enum):
    QUOTA = 'cpu_quota'
    SHARES = 'cpu_shares'
    RDT = 'rdt'


class AllocationValue:

    @abstractmethod
    def merge_with_current(self, current: 'AllocationValue') -> Tuple[
            'AllocationValue', Optional['AllocationValue']]:
        ...

    @abstractmethod
    def generate_metrics(self) -> List[Metric]:
        ...

    @abstractmethod
    def validate(self) -> List[str]:
        """Returns list of errors, empty list indicates that value is ok."""
        ...


TaskAllocations = Dict[AllocationType, Union[float, AllocationValue]]
TasksAllocations = Dict[TaskId, TaskAllocations]


@dataclass
class AllocationConfiguration:
    # Default value for cpu.cpu_period [ms] (used as denominator).
    cpu_quota_period: int = 1000

    # Number of minimum shares, when ``cpu_shares`` allocation is set to 0.0.
    cpu_shares_min: int = 2
    # Number of shares to set, when ``cpu_shares`` allocation is set to 1.0.
    cpu_shares_max: int = 10000

    # Default Allocation for default root group during initilization.
    # It will be used as default for all tasks (None will set to maximum available value).
    default_rdt_l3: str = None
    default_rdt_mb: str = None


class Allocator(ABC):

    @abstractmethod
    def allocate(
            self,
            platform: Platform,
            tasks_measurements: TasksMeasurements,
            tasks_resources: TasksResources,
            tasks_labels: TasksLabels,
            tasks_allocations: TasksAllocations,
    ) -> (TasksAllocations, List[Anomaly], List[Metric]):
        ...


class NOPAllocator(Allocator):

    def allocate(self, platform, tasks_measurements, tasks_resources,
                 tasks_labels, tasks_allocations):
        return [], [], []


# ---------------------------- internal

class BoxedTasksAllocations:
    """Wrapper over simple TaskAllocations type"""

    # Mapping from simple inmutable allocations values like ints
    # to concrete implementations
    # RDTAllocation() -> RDTAllocationValue
    # float -> FloatAloocationValue
    registered_box_types: Dict[Type, Type[AllocationValue]] = {}

    @classmethod
    def register(cls, simple_type: Type, box_class: Type[AllocationValue]):
        cls.registered_box_types[simple_type] = box_class

    @classmethod
    def box_value(cls, value: Any, **kwargs) -> AllocationValue:
        """Wraps simple value with boxed type."""
        box_class = cls.registered_box_types[type(value)]
        return box_class(value, **kwargs)

    # @classmethod
    # def build(cls, tasks_allocations: TasksAllocations) -> 'BoxedTasksAllocations':
    #     return BoxedTasksAllocations(tasks_allocations)
    #
    # def __init__(self, tasks_allocations: TasksAllocations):
    #     raise NotImplementedError


# Defines relative tolerance for float comparison.
FLOAT_VALUES_CHANGE_DETECTION = 1e-02


class BoxedNumeric(AllocationValue):
    """
    Wrapper for floats and integers.
    If min_value is None then it becomes negative infinity.
    If max_value is Not then it becomes infinity.
    """

    def __init__(self, value: Union[float, int],
                 min_value: Optional[Union[int, float]] = 0,
                 max_value: Optional[Union[int, float]] = None,
                 float_value_change_sensitivity=FLOAT_VALUES_CHANGE_DETECTION):
        self._value = value
        self._float_value_change_sensitivity = float_value_change_sensitivity
        self._min_value = min_value if min_value is not None else -math.inf
        self._max_value = max_value if max_value is not None else math.inf

    def __eq__(self, other):
        try:
            return math.isclose(self._value, other._value,
                                rel_tol=self._float_value_change_sensitivity)
        except AttributeError:
            return False

    def generate_metrics(self) -> List[Metric]:
        pass

    def validate(self) -> List[str]:
        if not self._value >= self._min_value or not self._value <= self._max_value:
            return [f'{self._value} does not belong to range <{self._min_value};{self._max_value}>']
        return []

    def merge_with_current(self, new_value: Optional['BoxedNumeric']) \
            -> Tuple['BoxedNumeric', Optional['BoxedNumeric']]:

        # If new_value is not None then we are going to compare numbers
        if new_value is not None:
            value_changed = self != new_value
        # If new_value is None then it is different than an object
        else:
            value_changed = True

        # To avoid issues with multiple references to single object we are going to return brand new
        # objects.
        if value_changed:
            return BoxedNumeric(new_value._value, self._min_value, self._max_value,
                                self._float_value_change_sensitivity), \
                BoxedNumeric(new_value._value, self._min_value, self._max_value,
                             self._float_value_change_sensitivity)
        else:
            # If value is not changed, then is assumed current value is the same as
            # new so we can return any of them (lets return the new one) as target
            return copy.deepcopy(self), None


BoxedTasksAllocations.register(int, BoxedNumeric)
BoxedTasksAllocations.register(float, BoxedNumeric)

# -----------------------------------------------------------------------
# private logic to handle allocations
# -----------------------------------------------------------------------


def _convert_tasks_allocations_to_metrics(tasks_allocations: TasksAllocations) -> List[Metric]:
    """Takes allocations on input and convert them to something that can be
    stored persistently as metrics adding type fields and labels.

    Simple allocations become simple metric like this:
    - Metric(name='allocation', type='cpu_shares', value=0.2, labels=(task_id='some_task_id'))
    Encoding RDTAllocation object is delegated to RDTAllocation class.
    """
    metrics = []
    for task_id, task_allocations in tasks_allocations.items():
        task_allocations: TaskAllocations
        for allocation_type, allocation_value in task_allocations.items():

            if isinstance(allocation_value, AllocationValue):
                this_allocation_metrics = allocation_value.generate_metrics()
                for metric in this_allocation_metrics:
                    metric.labels.update(task_id=task_id)
                metrics.extend(this_allocation_metrics)

            elif isinstance(allocation_value, (float, int)):
                # Default metrics encoding method for float and integers values.
                # Simple encoding for
                metrics.append(
                    Metric(name='allocation', value=allocation_value, type=MetricType.GAUGE,
                           labels=dict(allocation_type=allocation_type, task_id=task_id)
                           )
                )
            else:
                raise NotImplementedError(
                    'encoding AllocationType=%r for value of type=%r is '
                    'not supported!' % (allocation_type, type(allocation_value))
                )

    return metrics


def _calculate_chageset(current: Dict, new: Dict):
    return {}, {}


def _generate_metrics(current: Dict):
    pass


def _validate(current: Dict):
    pass


@trace(log, verbose=False)
def _calculate_task_allocations_changeset(
        current_task_allocations: TaskAllocations,
        new_task_allocations: TaskAllocations) \
        -> Tuple[TaskAllocations, TaskAllocations]:
    """Return tuple of resource allocation (changeset) per task.
    """

    # Copy current to become new current as target.
    target_task_allocations: TaskAllocations = dict(current_task_allocations)
    task_allocations_changeset: TaskAllocations = {}

    for allocation_type, new_value in new_task_allocations.items():

        new_allocation_value = BoxedTasksAllocations.box_value(new_value)

        current_allocation = current_task_allocations.get(allocation_type)
        target_allocation, allocation_changeset = \
            new_allocation_value.merge_with_current(current_allocation)
        target_task_allocations[allocation_type] = target_allocation

        if allocation_changeset is not None:
            task_allocations_changeset[allocation_type] = allocation_changeset

    if task_allocations_changeset:
        log.log(TRACE, '_calculate_task_allocations_changeset():'
                       '\ncurrent_task_allocations=\n%s'
                       '\nnew_task_allocations=\n%s'
                       '\ntarget_task_allocations=\n%s'
                       '\ntask_allocations_changeset=\n%s',
                pformat(current_task_allocations),
                pformat(new_task_allocations),
                pformat(target_task_allocations),
                pformat(task_allocations_changeset)
                )

    return target_task_allocations, task_allocations_changeset


@trace(log, verbose=False)
def _calculate_tasks_allocations_changeset(
        current_tasks_allocations: TasksAllocations, new_tasks_allocations: TasksAllocations) \
        -> Tuple[TasksAllocations, TasksAllocations]:
    """Return tasks allocations that need to be applied.
    Takes as input:
    1) current_tasks_allocations: currently applied allocations in the system,
    2) new_tasks_allocations: new to be applied allocations

    and outputs:
    1) target_tasks_allocations: the list of all allocations which will
        be applied in the system in next step:
       so it is a sum of inputs (if the are conflicting allocations
       in both inputs the value is taken from new_tasks_allocations).
    2) tasks_allocations_changeset: only allocations from
       new_tasks_allocations which are not contained already
       in current_tasks_allocations (set difference
       of input new_tasks_allocations and input current_tasks_allocations)
    """
    target_tasks_allocations: TasksAllocations = {}
    tasks_allocations_changeset: TasksAllocations = {}

    # check and merge & overwrite with old allocations
    for task_id, current_task_allocations in current_tasks_allocations.items():
        if task_id in new_tasks_allocations:
            new_task_allocations = new_tasks_allocations[task_id]
            target_task_allocations, changeset_task_allocations = \
                _calculate_task_allocations_changeset(current_task_allocations,
                                                      new_task_allocations)
            target_tasks_allocations[task_id] = target_task_allocations
            if changeset_task_allocations:
                tasks_allocations_changeset[task_id] = changeset_task_allocations
        else:
            target_tasks_allocations[task_id] = current_task_allocations

    # if there are any new_allocations on task level that yet not exists in old_allocations
    # then just add them to both list
    only_new_tasks_ids = set(new_tasks_allocations) - set(current_tasks_allocations)
    for only_new_task_id in only_new_tasks_ids:
        task_allocations = new_tasks_allocations[only_new_task_id]
        target_tasks_allocations[only_new_task_id] = task_allocations
        tasks_allocations_changeset[only_new_task_id] = task_allocations

    return target_tasks_allocations, tasks_allocations_changeset


def _ignore_invalid_allocations(platform: platforms.Platform,
                                new_tasks_allocations: TasksAllocations) -> (
        int, TasksAllocations):
    """Validate and ignore allocations, that are invaild.
    Returns new valid TasksAllocation object and number of ignored allocations.
    """
    # Ignore and warn about invalid allocations.
    ignored_allocations = 0
    task_ids_to_remove = set()
    for task_id, task_allocations in new_tasks_allocations.items():

        if isinstance(task_allocations, AllocationValue):
            _ = task_allocations.validate()

    new_tasks_allocations = {t: a for t, a in new_tasks_allocations.items()
                             if t not in task_ids_to_remove}
    return ignored_allocations, new_tasks_allocations
