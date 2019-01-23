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
from typing import List, Dict, Union, Tuple, Optional, Any, Type, Callable

from owca.allocators import AllocationValue
from owca.metrics import Metric, MetricType

log = logging.getLogger(__name__)


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


class AllocationsDict(dict, AllocationValue):
    """ keys: str
        values: AllocationValue
    """
    _default_mapping = dict()

    @classmethod
    def register_automapping_type(cls, t: Type, avt: Type[AllocationValue]):
        cls._default_mapping[t] = avt

    def __repr__(self):
        return 'AllocationsDict(%s)' % dict.__repr__(self)

    @classmethod
    def convert_values(cls,
                       d: Dict[str, Any],
                       ctx: List[str] = None,
                       mapping: Dict[
                           Union[Type, Tuple[str, Type]],  # recurisve types hell
                           Callable[[Any, List[str], Dict], AllocationValue]
                       ] = None) -> Dict[str, AllocationValue]:

        mapping = mapping or {}
        mapping.update(cls._default_mapping)

        nd = {}
        base_ctx = list(ctx or [])
        for k, v in d.items():
            if isinstance(v, AllocationValue):
                nv = v
            else:
                if (k, type(v)) in mapping:
                    box_class = mapping[(k, type(v))]
                    nv = box_class(v, base_ctx + [k], mapping)

                elif type(v) in mapping:
                    box_class = mapping[type(v)]
                    nv = box_class(v, base_ctx + [k], mapping)
                else:
                    raise Exception('cannot convert %r (type=%r under %r key) '
                                    'to AllocationValue using provied mapping=%r' %
                                    (v, type(v), k, mapping))
            nd[k] = nv

        return nd

    def __init__(self,
                 d: Dict[str, Any],
                 ctx: List[str] = None,  # accumulator like, for passing recursilvely
                 mapping: Dict[Union[Type, Tuple[str, Type]], Type[AllocationValue]] = None,
                 ):

        nd = self.convert_values(d, ctx, mapping)

        # Itnialize self as a dict with already converted values.
        dict.__init__(self, nd)

    def merge_with_current(self, current: 'AllocationsDict'):
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


AllocationsDict.register_automapping_type(dict, AllocationsDict)


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

    def validate(self) -> List[str]:
        # errors = []
        # if self.value < self.min_value:
        #     errors.append('value (%r) is lower that allowed minimum value (%r))' % (
        #         self.value, self.min_value))
        # if self.value > self.max_value:
        #     errors.append('value (%r) is higher that allowed maxmimum value (%r))' % (
        #         self.value, self.min_value))
        if not self.value >= self.min_value or not self.value <= self.max_value:
            return [f'{self.value} does not belong to range <{self.min_value};{self.max_value}>']
        return []

    def merge_with_current(self, current_value: Optional['BoxedNumeric']) \
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


AllocationsDict.register_automapping_type(int, lambda value, ctx, mapping: BoxedNumeric(value))
AllocationsDict.register_automapping_type(float, lambda value, ctx, mapping: BoxedNumeric(value))
