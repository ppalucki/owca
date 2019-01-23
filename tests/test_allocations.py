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


@pytest.mark.parametrize(
    'current_allocations, new_allocations, '
    'expected_target_allocations, expected_allocations_changeset', [
        ({}, {}, {}, None),
        (dict(x=2), {}, dict(x=2), None),
    ]
)
def test_allocations_dict_merging(current_allocations, new_allocations, 
                                  expected_target_allocations, expected_allocations_changeset
    ):
    got_target_allocations, got_allocations_changeset = \
        AllocationsDict(new_allocations).merge_with_current(AllocationsDict(current_allocations))

    expected_allocations_changeset_dict = AllocationsDict(expected_allocations_changeset) if \
        expected_allocations_changeset is not None else None
     
    assert got_target_allocations == AllocationsDict(expected_target_allocations)
    assert got_allocations_changeset == expected_allocations_changeset_dict

# single task

# @pytest.mark.parametrize(
#     'current_task_allocations,new_task_allocations,'
#     'expected_target_task_allocations,expected_task_allocations_changeset', (
#         ({}, {},
#          {}, {}),
#         ({'a': 0.2}, {},
#          {'a': 0.2}, {}),
#         ({'a': 0.2}, {'a': 0.2},
#          {'a': 0.2}, {}),
#         ({'b': 2}, {'b': 3},
#          {'b': 3}, {'b': 3}),
#         ({'a': 0.2, 'b': 0.4}, {'a': 0.2, 'b': 0.5},
#          {'a': 0.2, 'b': 0.5}, {'b': 0.5}),
#         ({}, {'a': 0.2, 'b': 0.5},
#          {'a': 0.2, 'b': 0.5}, {'a': 0.2, 'b': 0.5}),
#         # RDTAllocations
#         ({}, {"rdt": RDTAllocation(name='', l3='ff')},
#          {"rdt": RDTAllocation(name='', l3='ff')}, {"rdt": RDTAllocation(name='', l3='ff')}),
#         ({"rdt": RDTAllocation(name='', l3='ff')}, {},
#          {"rdt": RDTAllocation(name='', l3='ff')}, {}),
#         ({"rdt": RDTAllocation(name='', l3='ff')}, {"rdt": RDTAllocation(name='x', l3='ff')},
#          {"rdt": RDTAllocation(name='x', l3='ff')}, {"rdt": RDTAllocation(name='x', l3='ff')}),
#         ({"rdt": RDTAllocation(name='x', l3='ff')}, {"rdt": RDTAllocation(name='x', l3='dd')},
#          {"rdt": RDTAllocation(name='x', l3='dd')}, {"rdt": RDTAllocation(name='x', l3='dd')}),
#         ({"rdt": RDTAllocation(name='x', l3='dd', mb='ff')}, {"rdt": RDTAllocation(name='x', mb='ff')},
#          {"rdt": RDTAllocation(name='x', l3='dd', mb='ff')}, {}),
#     ))
# def test_calculate_task_allocations(
#         current_task_allocations, new_task_allocations,
#         expected_target_task_allocations, expected_task_allocations_changeset):
#     target_task_allocations, task_allocations_changeset = _calculate_task_allocations_changeset(
#         current_task_allocations, new_task_allocations
#     )
#     assert target_task_allocations == expected_target_task_allocations
#     assert task_allocations_changeset == expected_task_allocations_changeset



# # tasks
#
# @pytest.mark.parametrize(
#     'current_tasks_allocations,new_tasks_allocations,'
#     'expected_target_tasks_allocations,expected_tasks_allocations_changeset', (
#         ({}, {},
#          {}, {}),
#         (dict(t1={'a': 2}), {},
#          dict(t1={'a': 2}), {}),
#         (dict(t1={'a': 2}), dict(t1={'a': 2.01}),  # small enough to ignore
#          dict(t1={'a': 2}), {}),
#         (dict(t1={'a': 2}), dict(t1={'a': 2.1}),  # big enough to notice
#          dict(t1={'a': 2.1}), dict(t1={'a': 2.1})),
#         (dict(t1={'a': 2}), dict(t1={'a': 2}),
#          dict(t1={'a': 2}), {}),
#         (dict(t1={'a': 1}), dict(t1={'b': 2}, t2={'b': 3}),
#          dict(t1={'a': 1, 'b': 2}, t2={'b': 3}), dict(t1={'b': 2}, t2={'b': 3})),
#     ))
# def test_calculate_tasks_allocations_changeset(
#         current_tasks_allocations, new_tasks_allocations,
#         expected_target_tasks_allocations, expected_tasks_allocations_changeset
# ):
#     target_tasks_allocations, tasks_allocations_changeset = _calculate_tasks_allocations_changeset(
#         current_tasks_allocations, new_tasks_allocations
#     )
#     assert target_tasks_allocations == expected_target_tasks_allocations
#     assert tasks_allocations_changeset == expected_tasks_allocations_changeset
#
#




# @pytest.mark.parametrize(
#     'value, min_value, max_value, float_value_change_sensitivity, is_valid', (
#             (1, 2, 3, 0.00001, ['1 does not belong to range <2;3>']),
#             (1.1, 2, 3, 0.00001, ['1.1 does not belong to range <2;3>']),
#             (2.5, 2, 3, 0.00001, []),
#             (3, 2.5, 3.0, 0.00001, []),
#             (2.0, 2, 3.0, 0.00001, []),
#             (2.0, None, 3.0, 0.00001, []),
#             (2.0, 1, None, 0.00001, []),
#     )
# )
# def test_boxed_numeric_validation(value, min_value, max_value, float_value_change_sensitivity,
#                                   is_valid):
#     boxed_value = BoxedNumeric(value, min_value, max_value, float_value_change_sensitivity)
#     assert boxed_value.validate() == is_valid
#
#
# @pytest.mark.parametrize(
#     'current_value, new_value, expected_value', (
#             (BoxedNumeric(10), BoxedNumeric(10.1), (BoxedNumeric(10), None)),
#             (BoxedNumeric(10), BoxedNumeric(10.99), (BoxedNumeric(10.99), BoxedNumeric(10.99))),
#     )
# )
# def test_boxed_numeric_merging(current_value, new_value, expected_value):
#     value, changeset = current_value.merge_with_current(new_value)
#     assert value == expected_value[0]
#     assert changeset == expected_value[1]
#
#
# @pytest.mark.parametrize(
#     'left, right, is_equal', (
#             (BoxedNumeric(10), BoxedNumeric(10), True),
#             (BoxedNumeric(10), BoxedNumeric(11), False),
#             (BoxedNumeric(10), BoxedNumeric(10.1), True),
#             (BoxedNumeric(10), BoxedNumeric(10.11), False),
#             (BoxedNumeric(10.99), BoxedNumeric(10.99), True),
#     )
# )
# def test_boxed_numeric_equal(left, right, is_equal):
#     assert (left == right) == is_equal
#
#
# def test_box_allocations_factory_known_type():
#     boxed_int = BoxedAllocationFactory.create(1, min_value=2, max_value=3)
#     assert boxed_int._value == 1
#     assert boxed_int._min_value == 2
#     assert boxed_int._max_value == 3
#
#
# def test_box_allocations_factory_unknown_type():
#     with pytest.raises(KeyError):
#         this_is_really_complex = complex('1+2j')
#         BoxedAllocationFactory.create(this_is_really_complex, min_value=2, max_value=3)
