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

from wca.allocators import RDTAllocation
from wca.extra.static_allocator import StaticAllocator, _build_allocations_from_rules
from tests.testing import task_data


@patch('os.path.exists', Mock(return_value=True))
@patch('wca.extra.static_allocator.load_config', return_value=[])
@patch('wca.extra.static_allocator._build_allocations_from_rules', return_value={})
def test_static_allocator(allocate_according_rules_mock, load_config_mock):
    static_allocator = StaticAllocator(
        config='somefile', rules=[{'allocations': {'cpu_quota': 0.5}}])
    platform_mock = Mock()

    tasks_data = {
            't1_task_id': task_data('/t1', labels={'foo': 'bar'}, resources={'cpu_quota': 1.0})}

    assert static_allocator.allocate(platform_mock, tasks_data) == ({}, [], [])

    allocate_according_rules_mock.assert_called_once()
    load_config_mock.assert_called_once()


@pytest.mark.parametrize('rules, expected_tasks_allocations', [
    ([], {}),
    # default rule match all tasks
    ([{'allocations': {'cpu_quota': 2}}],
     {'t1_task_id': {'cpu_quota': 2}, 't2_task_id': {'cpu_quota': 2}}),
    # additional rule to match by task_id (for t2)
    ([{'allocations': {'cpu_quota': 2}},
      {'task_id': 't2_task_id', 'allocations': {'cpu_quota': 3}}],
     {'t1_task_id': {'cpu_quota': 2}, 't2_task_id': {'cpu_quota': 3}}),
    # additional rule to match by labels (for t1)
    ([{'allocations': {'cpu_quota': 2}},
      {'task_id': 't2_task_id', 'allocations': {'cpu_quota': 3}},
      {'labels': {'foo': 'bar'}, 'allocations': {'cpu_quota': 1}}
      ],
     {'t1_task_id': {'cpu_quota': 1}, 't2_task_id': {'cpu_quota': 3}}),
    # RDT are properly created for just first task
    ([{'task_id': 't1_task_id', 'allocations': {'rdt': {'l3': 'somevalue'}}}],
     {'t1_task_id': {'rdt': RDTAllocation(l3='somevalue')}}),
    # RDT are properly created for just first task with explicit name
    ([{'task_id': 't1_task_id', 'allocations': {'rdt': {'name': 'foo', 'l3': 'somevalue'}}}],
     {'t1_task_id': {'rdt': RDTAllocation(name='foo', l3='somevalue')}}),
])
def test_build_allocations_from_rules(rules, expected_tasks_allocations):
    tasks_data = {
            't1_task_id': task_data('/t1', labels={'foo': 'bar'}),
            't2_task_id': task_data('/t1')}

    assert _build_allocations_from_rules(tasks_data, rules) == expected_tasks_allocations
