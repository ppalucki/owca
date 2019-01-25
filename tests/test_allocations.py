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

from unittest.mock import Mock

import pytest

from owca.allocations import AllocationsDict, BoxedNumeric, AllocationValue, \
    create_default_registry, _convert_values, CommonLablesAllocationValue, \
    ContextualErrorAllocationValue, InvalidAllocationValue
from owca.testing import allocation_metric


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
    'value, min_value, max_value, float_value_change_sensitivity, expected_errors', (
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
                                  expected_errors):
    boxed_value = BoxedNumeric(value, min_value, max_value, float_value_change_sensitivity)
    expected_new_value = None if expected_errors else boxed_value
    got_errors, got_new_value = boxed_value.validate()
    assert got_errors == expected_errors
    assert got_new_value == expected_new_value


@pytest.mark.parametrize(
    'current, new, expected_target, expected_changeset', (
            (10, 10.1, 10, None),
            (10, 10.99, 10.99, 10.99),
    )
)
def test_boxed_numeric_calculated_changeset(current, new, expected_target, expected_changeset):
    expected_changeset = BoxedNumeric(expected_changeset) \
        if expected_changeset is not None else None
    got_target, got_changeset = BoxedNumeric(new).calculate_changeset(BoxedNumeric(current))
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
    'current, new, expected_target, expected_changeset', [
        ({}, {},
         {}, None),
        ({'x': 2}, {},
         {'x': 2}, None),
        ({'a': 0.2}, {},
         {'a': 0.2}, None),
        ({'a': 0.2}, {'a': 0.2},
         {'a': 0.2}, None),
        ({'b': 2}, {'b': 3},
         {'b': 3}, {'b': 3}),
        ({'a': 0.2, 'b': 0.4}, {'a': 0.2, 'b': 0.5},
         {'a': 0.2, 'b': 0.5}, {'b': 0.5}),
        ({}, {'a': 0.2, 'b': 0.5},
         {'a': 0.2, 'b': 0.5}, {'a': 0.2, 'b': 0.5}),
        # Recursively one more level (we use dict to show it)
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
    ]
)
def test_allocations_dict_merging(current, new,
                                  expected_target, expected_changeset):
    # Conversion
    current_dict = AllocationsDict(current)
    new_dict = AllocationsDict(new)

    # Merge
    got_target_dict, got_changeset_dict = new_dict.calculate_changeset(current_dict)

    assert got_target_dict.unwrap() == expected_target
    got_changeset = got_changeset_dict.unwrap() if got_changeset_dict is not None else None
    assert got_changeset == expected_changeset


def test_allocation_value_validate():
    failing_allocation_value = Mock(spec=AllocationValue, validate=Mock(
        return_value=(['some error generic'], None)))
    d = AllocationsDict({'bad_generic': failing_allocation_value,
                         'good': 2.5,
                         'bad_float': -5,
                         'subdict_good': {
                             'good': 2.5,
                             'bad': -6,
                         },
                         'subdict_bad': ContextualErrorAllocationValue(
                             AllocationsDict({
                                 'bad1': -2.5,
                                 'bad2': -7,
                             }),
                             'from_subdict_bad '
                         )
                         })
    errors, nd = d.validate()
    assert 'some error generic' in errors
    assert 'some error generic' in errors
    assert '-5 does not belong to range <0;inf>' in errors
    assert 'bad' not in nd
    assert 'bad float' not in nd
    assert 'good' in nd
    assert 'subdict_good' in nd
    assert 'subdict_bad' not in nd
    assert 'from_subdict_bad -2.5 does not belong to range <0;inf>' in errors
    failing_allocation_value.validate.assert_called_once()


@pytest.mark.parametrize('allocation_value, expected_metrics', [
    (AllocationsDict({}),
     []),
    (BoxedNumeric(2),
     [allocation_metric(None, 2)]),
    (CommonLablesAllocationValue(BoxedNumeric(2), labels=dict(foo='bar')),
     [allocation_metric(None, 2, labels=dict(foo='bar'))]),
    (AllocationsDict({'x': 2, 'y': 3}),
     [allocation_metric(None, 2), allocation_metric(None, 3)]),
    (AllocationsDict({'x': 2, 'y': 3}),
     [allocation_metric(None, 2), allocation_metric(None, 3)]),
    (AllocationsDict({'x': 2,
                      'y': CommonLablesAllocationValue(BoxedNumeric(3.5), labels=dict(foo='bar'))}),
     [allocation_metric(None, 2), allocation_metric(None, 3.5, labels=dict(foo='bar'))]),
])
def test_allocation_values_metrics(allocation_value: AllocationValue, expected_metrics):
    got_metrics = allocation_value.generate_metrics()
    assert got_metrics == expected_metrics


def test_invalid_allocation_values_helper():
    value = InvalidAllocationValue(BoxedNumeric(2), 'foo_prefix')
    errors, new_value = value.validate()
    assert new_value is None
    assert errors == ['foo_prefix']
