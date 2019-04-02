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
from unittest.mock import Mock, patch

import pytest

from owca.allocators import RDTAllocation
from owca.extra.static_allocator import StaticAllocator, _build_allocations_from_rules


@patch('os.path.exists', Mock(return_value=True))
@patch('owca.extra.static_allocator.load_config', return_value=[])
@patch('owca.extra.static_allocator._build_allocations_from_rules', return_value={})
def test_static_allocator(allocate_according_rules_mock, load_config_mock):
    static_allocator = StaticAllocator(config='somefile')
    platform_mock = Mock()
    measurements = {'task1': {}}
    resources = {'task1': {}}
    labels = {'task1': {'foo': 'bar'}}
    allocations = {'task1': {'cpu_quota': 1.0}}

    assert static_allocator.allocate(platform_mock, measurements,
                                     resources, labels, allocations) == ({}, [], [])

    allocate_according_rules_mock.assert_called_once()
    load_config_mock.assert_called_once()


@pytest.mark.parametrize('rules, expected_tasks_allocations', [
    ([], {}),
    # default rule match all tasks
    ([{'allocations': {'cpu_quota': 2}}],
     {'task1': {'cpu_quota': 2}, 'task2': {'cpu_quota': 2}}),
    # additional rule to match by task_id (for task2)
    ([{'allocations': {'cpu_quota': 2}},
      {'task_id': 'task2', 'allocations': {'cpu_quota': 3}}],
     {'task1': {'cpu_quota': 2}, 'task2': {'cpu_quota': 3}}),
    # additional rule to match by labels (for task1)
    ([{'allocations': {'cpu_quota': 2}},
      {'task_id': 'task2', 'allocations': {'cpu_quota': 3}},
      {'labels': {'foo': 'bar'}, 'allocations': {'cpu_quota': 1}}
      ],
     {'task1': {'cpu_quota': 1}, 'task2': {'cpu_quota': 3}}),
    # RDT are properly created for just first task
    ([{'task_id': 'task1', 'allocations': {'rdt': {'l3': 'somevalue'}}}],
     {'task1': {'rdt': RDTAllocation(l3='somevalue')}}),
    # RDT are properly created for just first task with explicit name
    ([{'task_id': 'task1', 'allocations': {'rdt': {'name': 'foo', 'l3': 'somevalue'}}}],
     {'task1': {'rdt': RDTAllocation(name='foo', l3='somevalue')}}),
])
def test_build_allocations_from_rules(rules, expected_tasks_allocations):
    all_tasks_ids = {'task1', 'task2'}
    labels = {'task1': {'foo': 'bar'}}
    assert _build_allocations_from_rules(all_tasks_ids, labels, rules) == expected_tasks_allocations
