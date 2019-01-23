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
import math
from abc import ABC, abstractmethod
from enum import Enum
from pprint import pformat
from typing import List, Dict, Union, Tuple, Optional, Any, Type

from dataclasses import dataclass

from owca import platforms
from owca.allocators import AllocationValue, TasksAllocations, TaskAllocations
from owca.detectors import TasksMeasurements, TasksResources, TasksLabels, Anomaly
from owca.logger import trace, TRACE
from owca.nodes import TaskId
from owca.metrics import Metric, MetricType
from owca.platforms import Platform

log = logging.getLogger(__name__)




# class BoxedTasksAllocations:
#     """Wrapper over simple TaskAllocations type"""
#
#     # Mapping from simple inmutable allocations values like ints
#     # to concrete implementations
#     # RDTAllocation() -> RDTAllocationValue
#     # float -> FloatAloocationValue
#     registered_box_types: Dict[Type, Type[AllocationValue]] = {}
#
#     @classmethod
#     def register(cls, simple_type: Type, box_class: Type[AllocationValue]):
#         cls.registered_box_types[simple_type] = box_class
#
#     @classmethod
#     def box_value(cls, value: Any, **kwargs) -> AllocationValue:
#         """Wraps simple value with boxed type."""
#         box_class = cls.registered_box_types[type(value)]
#         return box_class(value, **kwargs)
#
#     # @classmethod
#     # def build(cls, tasks_allocations: TasksAllocations) -> 'BoxedTasksAllocations':
#     #     return BoxedTasksAllocations(tasks_allocations)
#     #
#     # def __init__(self, tasks_allocations: TasksAllocations):
#     #     raise NotImplementedError


class CommonLablesAllocationValue(AllocationValue):
    """ Update any allocation values wiht common labels, when peforming generate_metrics."""

    def __init__(self, allocation_value, **common_labels):
        self.allocation_value = allocation_value		
        self.common_labels = common_labels

    def generate_metrics(self):
        metrics = self.allocation_value.generate_metrics() 
        for metric in metrics:
            metric.labels.update(**self.common_labels)
        return metrics

    def perform_allocations(self):
        self.allocation_value.perform_allocations()

    def validate(self):
        return self.allocation_value.perform_allocations()
    
    def merge_with_current(self, current):
        return self.allocation_value.merge_with_curent(current)




class AllocationsDict(AllocationValue, dict):
    """ keys: str
        values: AllocationValue
    """

    def merge_with_current(self, current: 'AllocationsDict'):
        """ 
        TODO: translate !!!!
        Mergowanie dictow wyglada tak:
        jest w nowym jest klucz a w starym nie ma, to target zawiera nowy
        jesli klucz jest w starym a nie ma w nowym to nowy jest wynikiem
        jesli klucz jest w obu rekreucjny  merge i zaplikuje wynik
        """ 
        assert isinstance(current, AllocationsDict)

        target = AllocationsDict()
        changeset = AllocationsDict()

        for key, new_value in self.items():

            # Autoboxing for simple types.
            if not isinstance(new_value, AllocationValue):
                new_value = box_value(new_value)

            current_value = current.get(key)

            if current_value is None:
                # There is no current value, new is used 
                target[key] = new_value
                changeset[key] = new_value

            else:
                if not isinstance(current_value, AllocationValue):
                    current_value = box_value(current_value)
                # Both exists - recurse
                target_value, value_changeset = new_value.merge_with_current(current_value)
                target[key] = target_value
                if value_changeset is not None:
                    changeset[key] = value_changeset

        # Empty dict with no changes is like a None.
        if not changeset:
            changeset = None

        return target, changeset

    def generate_metrics(self):
        metrics = [] 
        for value in self.values():
            metrics.extend(value.generate_metrics())
        return metrics

    def perform_allocations(self):
        for value in self.values():
            value.perform_allocations()

    def validate(self) -> List[str]:
        errors = []
        for value in self.values():
            errors.extend(value.validate())
        return errors


# Defines default how senstive in terms of float precision are changes from RDTAllocation detected.
FLOAT_VALUES_CHANGE_DETECTION = 1e-02

class BoxedNumeric(AllocationValue):
    """ Wraps floats and ints.
    """

    def __init__(self, value: float, min_value=0, max_value=None,
                 float_value_change_sensitivity=FLOAT_VALUES_CHANGE_DETECTION,
                 ):
        self.value = value
        self.float_value_change_sensitivity = float_value_change_sensitivity
        self.min_value = min_value
        self.max_value = max_value

    def generate_metrics(self) -> List[Metric]:
        """ Default metrics encoding method for float and integers values."""

        assert isinstance(self.value, (float, int))
        return [Metric(
                    name='allocation', 
                    value=self.valu, 
                    type=MetricType.GAUGE,
               )]

    def validate(self) -> List[str]:
        errors = []
        if self.value < self.min_value:
            errors.append('value (%r) is lower that allowed minimum value (%r))' % (
                self.value, self.min_value))
        if self.value > self.max_value:
            errors.append('value (%r) is higher that allowed maxmimum value (%r))' % (
                self.value, self.min_value))
        return errors

    def merge_with_current(self, current_value: Optional['BoxedNumeric']) \
            -> Tuple['BoxedNumeric', Optional['BoxedNumeric']]:
        """Assuming self is "new value" return target and changeset. """

        new_float = self.value

        # Float and integered based change detection.
        if current_value is not None:
            current_float = current_value.value
            # If we have old value
            value_changed = not math.isclose(current_float, new_float,
                                             rel_tol=self.float_value_change_sensitivity)
        else:
            # There is no old value, so there is a change
            value_changed = True

        if value_changed:
            # For floats merge is simple, is value is change, the
            # new_value just become target and changeset
            # target and changeset
            return self, self
        else:
            # If value is not changed, then is assumed current value is the same as
            # new so we can return any of them (lets return the new one) as target
            return self, None

    def perform_allocations(self):
        raise NotImplementedError()

_boxed_values_register = dict()
def register_autobox(t: Type, avt: Type[AllocationValue]):
    _boxed_values_register[type] = avt
register_autobox[int] = BoxedNumeric
register_autobox[float] = BoxedNumeric
register_autobox[dict] = AllocationsDict
def box_value(value: Any) -> AllocationValue:
    if not type(value) in _boxed_values_register:
        raise Exception('cannot automatically box value, unregistered type: %s' % type(value))
    box_class = _boxed_values_register[type(value)]
    boxed_value = box_class(value)
    return boxed_value

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
