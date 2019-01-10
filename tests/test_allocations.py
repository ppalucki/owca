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

from owca.allocators import _calculate_task_allocations, _calculate_tasks_allocations, \
    RDTAllocation, AllocationType, convert_tasks_allocations_to_metrics, \
    _parse_schemata_file_domains, _count_enabled_bits, _merge_rdt_allocation
from owca.metrics import Metric, MetricType

r = AllocationType.RDT


@pytest.mark.parametrize(
    'old_task_allocations,new_task_allocations,'
    'expected_all_task_allocations,expected_resulting_task_allocations', (
        ({}, {},
         {}, {}),
        ({'a': 0.2}, {},
         {'a': 0.2}, {}),
        ({'a': 0.2}, {'a': 0.2},
         {'a': 0.2}, {}),
        ({'b': 2}, {'b': 3},
         {'b': 3}, {'b': 3}),
        ({'a': 0.2, 'b': 0.4}, {'a': 0.2, 'b': 0.5},
         {'a': 0.2, 'b': 0.5}, {'b': 0.5}),
        ({}, {'a': 0.2, 'b': 0.5},
         {'a': 0.2, 'b': 0.5}, {'a': 0.2, 'b': 0.5}),
        # RDTAllocations
        ({}, {r: RDTAllocation(name='', l3='ff')},
         {r: RDTAllocation(name='', l3='ff')}, {r: RDTAllocation(name='', l3='ff')}),
        ({r: RDTAllocation(name='', l3='ff')}, {},
         {r: RDTAllocation(name='', l3='ff')}, {}),
        ({r: RDTAllocation(name='', l3='ff')}, {r: RDTAllocation(name='x', l3='ff')},
         {r: RDTAllocation(name='x', l3='ff')}, {r: RDTAllocation(name='x', l3='ff')}),
        ({r: RDTAllocation(name='x', l3='ff')}, {r: RDTAllocation(name='x', l3='dd')},
         {r: RDTAllocation(name='x', l3='dd')}, {r: RDTAllocation(name='x', l3='dd')}),
        ({r: RDTAllocation(name='x', l3='dd', mb='ff')}, {r: RDTAllocation(name='x', mb='ff')},
         {r: RDTAllocation(name='x', l3='dd', mb='ff')}, {r: RDTAllocation(name='x', mb='ff')}),
    ))
def test_calculate_task_allocations(
        old_task_allocations, new_task_allocations,
        expected_all_task_allocations, expected_resulting_task_allocations):
    all_task_allocations, resulting_task_allocations = _calculate_task_allocations(
        old_task_allocations, new_task_allocations
    )
    assert all_task_allocations == expected_all_task_allocations
    assert resulting_task_allocations == expected_resulting_task_allocations


@pytest.mark.parametrize(
    'old_tasks_allocations,new_tasks_allocations,'
    'expected_all_tasks_allocations,expected_resulting_tasks_allocations', (
        ({}, {},
         {}, {}),
        (dict(t1={'a': 2}), {},
         dict(t1={'a': 2}), {}),
        (dict(t1={'a': 1}), dict(t1={'b': 2}, t2={'b': 3}),
         dict(t1={'a': 1, 'b': 2}, t2={'b': 3}), dict(t1={'b': 2}, t2={'b': 3})),
    ))
def test_calculate_tasks_allocations(
        old_tasks_allocations, new_tasks_allocations,
        expected_all_tasks_allocations, expected_resulting_tasks_allocations
):
    all_tasks_allocations, resulting_tasks_allocations = _calculate_tasks_allocations(
        old_tasks_allocations, new_tasks_allocations
    )
    assert all_tasks_allocations == expected_all_tasks_allocations
    assert resulting_tasks_allocations == expected_resulting_tasks_allocations


@pytest.mark.parametrize('hexstr,expected_bits_count', (
        ('', 0),
        ('1', 1),
        ('2', 1),
        ('3', 2),
        ('f', 4),
        ('f0', 4),
        ('0f0', 4),
        ('ff0', 8),
        ('f1f', 9),
        ('fffff', 20),
))
def test_count_enabled_bits(hexstr, expected_bits_count):
    got_bits_count = _count_enabled_bits(hexstr)
    assert got_bits_count == expected_bits_count


@pytest.mark.parametrize('line,expected_domains', (
        ('', {}),
        ('x=2', {'x': '2'}),
        ('x=2;y=3', {'x': '2', 'y': '3'}),
        ('foo=bar', {'foo': 'bar'}),
        ('mb:1=20;2=50',  {'1': '20', '2': '50'}),
        ('mb:xxx=20mbs;2=50b', {'xxx': '20mbs', '2': '50b'}),
        ('l3:0=20;1=30', {'1': '30', '0': '20'}),
))
def test_parse_schemata_file_domains(line, expected_domains):
    got_domains = _parse_schemata_file_domains(line)
    assert got_domains == expected_domains


@pytest.mark.parametrize('invalid_line', (
        'x=',
        'x=2;x=3',
        '=2',
        '2',
        ';',
        'xxx',
))
def test_parse_invalid_schemata_file_domains(invalid_line):
    with pytest.raises(ValueError):
        _parse_schemata_file_domains(invalid_line)


def rdt_metric_func(type, value, **labels):
    """Helper to create RDT like metric"""
    return Metric(
      name='allocation',
      type=MetricType.GAUGE,
      value=value,
      labels=dict(allocation_type=type, **(labels or dict()))
    )


@pytest.mark.parametrize('rdt_allocation, expected_metrics', (
    (RDTAllocation(), []),
    (RDTAllocation(mb='mb:0=20'), [
          rdt_metric_func('rdt_mb', 20, group_name='', domain_id='0')
    ]),
    (RDTAllocation(mb='mb:0=20;1=30'), [
        rdt_metric_func('rdt_mb', 20, group_name='', domain_id='0'),
        rdt_metric_func('rdt_mb', 30, group_name='', domain_id='1'),
    ]),
    (RDTAllocation(l3='l3:0=ff'), [
        rdt_metric_func('rdt_l3', 8, group_name='', domain_id='0'),
    ]),
    (RDTAllocation(name='be', l3='l3:0=ff', mb='mb:0=20;1=30'), [
        rdt_metric_func('rdt_l3', 8, group_name='be', domain_id='0'),
        rdt_metric_func('rdt_mb', 20, group_name='be', domain_id='0'),
        rdt_metric_func('rdt_mb', 30, group_name='be', domain_id='1'),
    ]),
))
def test_rdt_allocation_generate_metrics(rdt_allocation: RDTAllocation, expected_metrics):
    got_metrics = rdt_allocation.generate_metrics()
    assert got_metrics == expected_metrics


@pytest.mark.parametrize('tasks_allocations,expected_metrics', (
    ({}, []),
    ({'some_task': {AllocationType.SHARES: 0.5}}, [
        Metric(name='allocation', value=0.5,
               type=MetricType.GAUGE,
               labels={'allocation_type': 'cpu_shares', 'task_id': 'some_task'})
    ]),
    ({'some_task': {AllocationType.SHARES: 0.5, AllocationType.RDT: RDTAllocation(mb='mb:0=20')}}, [
        Metric(
            name='allocation', value=0.5,
            type=MetricType.GAUGE,
            labels={'allocation_type': AllocationType.SHARES, 'task_id': 'some_task'}
        ),
        rdt_metric_func('rdt_mb', 20, group_name='', domain_id='0', task_id='some_task')
    ]),
    ({'some_task_a': {
            AllocationType.SHARES: 0.5, AllocationType.RDT: RDTAllocation(mb='mb:0=30')
        },
      'some_task_b': {
            AllocationType.QUOTA: 0.6,
            AllocationType.RDT: RDTAllocation(name='b', l3='l3:0=f;1=f1'),
        }}, [
        Metric(
            name='allocation', value=0.5,
            type=MetricType.GAUGE,
            labels={'allocation_type': AllocationType.SHARES, 'task_id': 'some_task_a'}
        ),
        rdt_metric_func('rdt_mb', 30, group_name='', domain_id='0', task_id='some_task_a'),
        Metric(
            name='allocation', value=0.6,
            type=MetricType.GAUGE,
            labels={'allocation_type': AllocationType.QUOTA, 'task_id': 'some_task_b'}
        ),
        rdt_metric_func('rdt_l3', 4, group_name='b', domain_id='0', task_id='some_task_b'),
        rdt_metric_func('rdt_l3', 5, group_name='b', domain_id='1', task_id='some_task_b'),
    ]),
))
def test_convert_task_allocations_to_metrics(tasks_allocations, expected_metrics):
    metrics_got = convert_tasks_allocations_to_metrics(tasks_allocations)
    assert metrics_got == expected_metrics


@pytest.mark.parametrize(
    'old_rdt_alloaction, new_rdt_allocation,'
    'expected_all_rdt_allocation,expected_resulting_rdt_allocation', (
        (None, RDTAllocation(),
         RDTAllocation(), RDTAllocation()),
        (RDTAllocation(name=''), RDTAllocation(),  # empty group overrides existing
         RDTAllocation(), RDTAllocation()),
        (RDTAllocation(), RDTAllocation(l3='x'),
         RDTAllocation(l3='x'), RDTAllocation(l3='x')),
        (RDTAllocation(l3='x'), RDTAllocation(mb='y'),
         RDTAllocation(l3='x', mb='y'), RDTAllocation(mb='y')),
        (RDTAllocation(l3='x'), RDTAllocation(l3='x', mb='y'),
         RDTAllocation(l3='x', mb='y'), RDTAllocation(mb='y')),
        (RDTAllocation(l3='x', mb='y'), RDTAllocation(name='new', l3='x', mb='y'),
         RDTAllocation(name='new', l3='x', mb='y'), RDTAllocation(name='new', l3='x', mb='y'))
    )
)
def test_merge_rdt_allocations1(
        old_rdt_alloaction, new_rdt_allocation,
        expected_all_rdt_allocation, expected_resulting_rdt_allocation):
    got_all_rdt_allocation, got_resulting_rdt_alloction = _merge_rdt_allocation(old_rdt_alloaction,
                                                                                new_rdt_allocation)

    assert got_all_rdt_allocation == expected_all_rdt_allocation
    assert got_resulting_rdt_alloction == expected_resulting_rdt_allocation
