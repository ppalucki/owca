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

import pytest

from owca.allocations import AllocationsDict, BoxedNumeric, AllocationValue, \
    create_default_registry, _convert_values
from unittest.mock import Mock


@pytest.mark.parametrize(
    'simple_dict, expected_converted_dict', [
        (dict(), dict()),
        (dict(x=2), dict(x=BoxedNumeric(2))),
        (dict(x=dict()), dict(x=AllocationsDict({}))),
        (dict(x=dict(y=2)), dict(x=AllocationsDict(dict(y=BoxedNumeric(2))))),
    ]
)
def test_allocations_dict_convert_values_for_default_types(simple_dict, expected_converted_dict):
    registry = create_default_registry()
    got_converted_dict = _convert_values(simple_dict, None, registry)
    assert got_converted_dict == expected_converted_dict


def test_allocations_dict_custom_mapping():
    """Check that custom mappings are used to build mappings."""

    class Foo:
        pass

    foo_allocation_value_class1 = Mock(spec=AllocationValue)
    foo_allocation_value_class2 = Mock(spec=AllocationValue)

    mapping = {
        Foo: foo_allocation_value_class1,
        ('y', Foo): foo_allocation_value_class2
    }
    foo = Foo()
    registry = create_default_registry()
    for k, v in mapping.items():
        registry.register_automapping_type(k, v)

    _convert_values({'x': foo, 'y': foo}, None, registry)

    foo_allocation_value_class1.assert_called_once_with(foo, ['x'], registry)
    foo_allocation_value_class2.assert_called_once_with(foo, ['y'], registry)


############################################################################
# BoxedNumericTests
############################################################################

@pytest.mark.parametrize(
    'value, min_value, max_value, float_value_change_sensitivity, is_valid', (
            (1, 2, 3, 0.00001, ['1 does not belong to range <2;3>']),
            (1.1, 2, 3, 0.00001, ['1.1 does not belong to range <2;3>']),
            (2.5, 2, 3, 0.00001, []),
            (3, 2.5, 3.0, 0.00001, []),
            (2.0, 2, 3.0, 0.00001, []),
            (2.0, None, 3.0, 0.00001, []),
            (2.0, 1, None, 0.00001, []),
    )
)
def test_boxed_numeric_validation(value, min_value, max_value, float_value_change_sensitivity,
                                  is_valid):
    boxed_value = BoxedNumeric(value, min_value, max_value, float_value_change_sensitivity)
    assert boxed_value.validate() == is_valid


@pytest.mark.parametrize(
    'current, new, expected_target, expected_changeset', (
        (10, 10.1, 10, None),
        (10, 10.99, 10.99, 10.99),
    )
)
def test_boxed_numeric_calculated_changeset(current, new, expected_target, expected_changeset):
    expected_changeset = BoxedNumeric(expected_changeset) \
        if expected_changeset is not None else None
    got_target, got_changeset = BoxedNumeric(new).merge_with_current(BoxedNumeric(current))
    assert got_target == BoxedNumeric(expected_target)
    assert got_changeset == expected_changeset


@pytest.mark.parametrize(
    'left, right, is_equal', (
            (BoxedNumeric(10), BoxedNumeric(10), True),
            (BoxedNumeric(10), BoxedNumeric(11), False),
            (BoxedNumeric(10), BoxedNumeric(10.1), True),
            (BoxedNumeric(10), BoxedNumeric(10.11), False),
            (BoxedNumeric(10.99), BoxedNumeric(10.99), True),
    )
)
def test_boxed_numeric_equal(left, right, is_equal):
    assert (left == right) == is_equal


@pytest.mark.parametrize(
    'current_tasks_allocations,new_tasks_allocations,'
    'expected_target_tasks_allocations,expected_tasks_allocations_changeset', (
            ({}, {},
             {}, None),
            (dict(t1={'a': 2}), {},
             dict(t1={'a': 2}), None),
            (dict(t1={'a': 2}), dict(t1={'a': 2.01}),  # small enough to ignore
             dict(t1={'a': 2}), None),
            (dict(t1={'a': 2}), dict(t1={'a': 2.1}),  # big enough to notice
             dict(t1={'a': 2.1}), dict(t1={'a': 2.1})),
            (dict(t1={'a': 2}), dict(t1={'a': 2}),
             dict(t1={'a': 2}), None),
            (dict(t1={'a': 1}), dict(t1={'b': 2}, t2={'b': 3}),
             dict(t1={'a': 1, 'b': 2}, t2={'b': 3}), dict(t1={'b': 2}, t2={'b': 3})),
    ))
def test_calculate_tasks_allocations_changeset(
        current_tasks_allocations, new_tasks_allocations,
        expected_target_tasks_allocations, expected_tasks_allocations_changeset
):
    registry = create_default_registry()
    # conversion
    current_dict = AllocationsDict(current_tasks_allocations, None, registry)
    new_dict = AllocationsDict(new_tasks_allocations, None, registry)
    if expected_tasks_allocations_changeset is not None:
        assert isinstance(expected_tasks_allocations_changeset, dict)
        expected_allocations_changeset_dict = AllocationsDict(expected_tasks_allocations_changeset, None, registry)
    else:
        expected_allocations_changeset_dict = None
    expected_target_allocations_dict = AllocationsDict(expected_target_tasks_allocations, None, registry)

    # merge
    got_target_dict, got_changeset_dict = \
        new_dict.merge_with_current(current_dict)

    assert got_target_dict == expected_target_allocations_dict
    assert got_changeset_dict == expected_allocations_changeset_dict
