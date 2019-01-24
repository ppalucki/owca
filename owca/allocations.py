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
from typing import List, Dict, Union, Tuple, Optional, Any, Type

from owca.metrics import Metric, MetricType

log = logging.getLogger(__name__)


class AllocationValue(ABC):

    @abstractmethod
    def calculate_changeset(self, current: 'AllocationValue') -> Tuple[
            'AllocationValue', Optional['AllocationValue']]:
        # TODO: docstiring for calculate_changeset
        ...

    @abstractmethod
    def generate_metrics(self) -> List[Metric]:
        ...

    @abstractmethod
    def validate(self) -> Tuple[List[str], Optional['AllocationValue']]:
        """Returns list of errors, empty list indicates that value is ok.
        Returns modifed object that can still perform some of allocations,
        or None if nothing can be processed.
        Examples:
            RDTAllocation can ignore setting MB, but still set L3
            TasksAllocatios can still apply some settings for some tasks.
        """
        ...

    @abstractmethod
    def perform_allocations(self):
        """Perform allocatoins."""
        ...

    @abstractmethod
    def unwrap(self) -> Any:
        """Perform allocatoins."""
        ...


class AllocationValueDelegator(AllocationValue):

    def __init__(self, allocation_value):
        self.allocation_value: AllocationValue = allocation_value

    def validate(self) -> Tuple[List[str], AllocationValue]:
        return self.allocation_value.validate()

    def perform_allocations(self):
        self.allocation_value.perform_allocations()

    def calculate_changeset(self, current):
        return self.allocation_value.calculate_changeset(current)

    def generate_metrics(self):
        return self.allocation_value.generate_metrics()

    def unwrap(self):
        return self.allocation_value.unwrap()


class ContextualErrorAllocationValue(AllocationValueDelegator):
    """Prefixes errors messages with given string."""

    def __init__(self, allocation_value: AllocationValue, prefix_message: str):
        super().__init__(allocation_value)
        self.prefix_message = prefix_message

    def validate(self) -> Tuple[List[str], AllocationValue]:
        errors, new_value = self.allocation_value.validate()
        prefixed_errors = ['%s%s' % (self.prefix_message, error) for error in errors]
        return prefixed_errors, new_value


class InvalidAllocationValue(AllocationValueDelegator):
    """ Update any allocation values wiht common labels, when peforming generate_metrics."""

    def __init__(self, allocation_value, error_message):
        super().__init__(allocation_value)
        self.error_message = error_message

    def validate(self):
        return [self.error_message], None


class CommonLablesAllocationValue(AllocationValueDelegator):
    """ Update any allocation values wiht common labels, when peforming generate_metrics."""

    def __init__(self, allocation_value, **common_labels):
        super().__init__(allocation_value)
        self.common_labels = common_labels

    def generate_metrics(self):
        metrics = self.allocation_value.generate_metrics()
        for metric in metrics:
            metric.labels.update(**self.common_labels)
        return metrics


class Registry:
    # TODO: docs Registry class

    def __init__(self):
        self._mapping = dict()

    def register_automapping_type(self, t: Type, avt: Type[AllocationValue]):
        # TODO: better local names
        self._mapping[t] = avt

    def convert_value(self, base_ctx, k, v):
        # TODO: docstring and better variables names
        if (k, type(v)) in self._mapping:
            box_class = self._mapping[(k, type(v))]
            nv = box_class(v, base_ctx + [k], self)
        elif type(v) in self._mapping:
            box_class = self._mapping[type(v)]
            nv = box_class(v, base_ctx + [k], self)
        else:
            raise Exception('cannot convert %r (type=%r under %r key) '
                            'to AllocationValue using provied mapping=%r' %
                            (v, type(v), k, self._mapping))
        return nv


def _convert_values(d: Dict[str, Any], ctx: List[str], registry) -> Dict[str, AllocationValue]:
    # TODO: docs for convert_values
    # TODO: better variables naming

    nd = {}
    base_ctx = list(ctx or [])
    for k, v in d.items():
        if isinstance(v, AllocationValue):
            nv = v
        else:
            nv = registry.convert_value(base_ctx, k, v)
        nd[k] = nv

    return nd


class AllocationsDict(dict, AllocationValue):
    """ keys: str
        values: AllocationValue
    """

    def __repr__(self):
        return 'AllocationsDict(%s)' % dict.__repr__(self)

    def __init__(self,
                 d: Dict[str, Any],
                 ctx: List[str] = None,  # accumulator like, for passing recursilvely
                 registry=None,
                 ):

        registry = registry or create_default_registry()
        nd = _convert_values(d, ctx, registry)

        # Itnialize self as a dict with already converted values.
        dict.__init__(self, nd)

    def calculate_changeset(self, current: 'AllocationsDict') -> Tuple['AllocationsDict',
                                                                       Optional['AllocationsDict']]:
        assert isinstance(current, AllocationsDict)

        target = AllocationsDict(current)
        changeset = AllocationsDict({})

        for key, new_value in self.items():

            # Autoboxing for simple types.
            assert isinstance(new_value, AllocationValue)

            current_value = current.get(key)

            if current_value is None:
                # There is no current value, new is used
                target[key] = new_value
                changeset[key] = new_value

            else:
                assert isinstance(current_value, AllocationValue)
                # Both exists - recurse
                target_value, value_changeset = new_value.calculate_changeset(current_value)
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

    def validate(self) -> Tuple[List[str], 'AllocationsDict']:
        errors = []
        nd = AllocationsDict({})
        for key, value in self.items():
            value_errors, new_value = value.validate()
            if new_value is not None:
                nd[key] = new_value
            errors.extend(value_errors)
        # Empty dict becomes None
        nd = nd or None
        return errors, nd

    def unwrap(self) -> dict:
        d = {}
        for k, v in self.items():
            if v is not None:
                d[k] = v.unwrap()
        return d


class BoxedNumeric(AllocationValue):
    """ Wraps floats and ints.

    Wrapper for floats and integers.
    If min_value is None then it becomes negative infinity.
    If max_value is Not then it becomes infinity.
    """
    # Defines default how senstive in terms of
    # float precision are changes from RDTAllocation detected.
    FLOAT_VALUES_CHANGE_DETECTION = 1e-02

    def __init__(self, value: Union[float, int],
                 min_value: Optional[Union[int, float]] = 0,
                 max_value: Optional[Union[int, float]] = None,
                 float_value_change_sensitivity=FLOAT_VALUES_CHANGE_DETECTION,
                 ):
        assert isinstance(value, (float, int))
        self.value = value
        self.float_value_change_sensitivity = float_value_change_sensitivity
        self.min_value = min_value if min_value is not None else -math.inf
        self.max_value = max_value if max_value is not None else math.inf

    def __repr__(self):
        return 'BoxedNumeric(%r)' % self.value

    def __eq__(self, other: 'BoxedNumeric'):
        return math.isclose(self.value, other.value,
                            rel_tol=self.float_value_change_sensitivity)

    def generate_metrics(self) -> List[Metric]:
        """ Default metrics encoding method for float and integers values."""

        assert isinstance(self.value, (float, int))
        return [Metric(
                    name='allocation',
                    value=self.value,
                    type=MetricType.GAUGE,
               )]

    def validate(self) -> Tuple[List[str], Optional['BoxedNumeric']]:
        if not self.value >= self.min_value or not self.value <= self.max_value:
            errors = ['%s does not belong to range <%s;%s>' % (
                           self.value, self.min_value, self.max_value)]
            return errors, None
        return [], self

    def calculate_changeset(self, current_value: Optional['BoxedNumeric']) \
            -> Tuple['BoxedNumeric', Optional['BoxedNumeric']]:
        """Assuming self is "new value" return target and changeset. """

        # Float and integered based change detection.
        if current_value is None:
            # There is no old value, so there is a change
            value_changed = True
        else:
            # If we have old value compare them.
            value_changed = (self != current_value)

        if value_changed:
            # For floats merge is simple, is value is change, the
            # new_value just become target and changeset
            # target and changeset (overwrite policy)
            return self, self
        else:
            # If value is not changed, then is assumed current value is the same as
            # new so we can return any of them (lets return the new one) as target
            return self, None

    def perform_allocations(self):
        raise NotImplementedError()

    def unwrap(self):
        return self.value


def create_default_registry():
    registry = Registry()
    registry.register_automapping_type(dict, AllocationsDict)
    registry.register_automapping_type(int, lambda value, ctx, mapping: BoxedNumeric(value))
    registry.register_automapping_type(float, lambda value, ctx, mapping: BoxedNumeric(value))
    return registry
