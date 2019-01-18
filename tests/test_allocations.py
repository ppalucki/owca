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

from owca.allocators import _calculate_task_allocations_changeset, \
    _calculate_tasks_allocations_changeset, AllocationType, \
    _convert_tasks_allocations_to_metrics
from owca.metrics import Metric, MetricType
from owca.resctrl import RDTAllocation, _parse_schemata_file_row, _count_enabled_bits, \
    check_cbm_bits


@pytest.mark.parametrize(
    'current_task_allocations,new_task_allocations,'
    'expected_target_task_allocations,expected_task_allocations_changeset', (
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
        ({}, {"rdt": RDTAllocation(name='', l3='ff')},
         {"rdt": RDTAllocation(name='', l3='ff')}, {"rdt": RDTAllocation(name='', l3='ff')}),
        ({"rdt": RDTAllocation(name='', l3='ff')}, {},
         {"rdt": RDTAllocation(name='', l3='ff')}, {}),
        ({"rdt": RDTAllocation(name='', l3='ff')}, {"rdt": RDTAllocation(name='x', l3='ff')},
         {"rdt": RDTAllocation(name='x', l3='ff')}, {"rdt": RDTAllocation(name='x', l3='ff')}),
        ({"rdt": RDTAllocation(name='x', l3='ff')}, {"rdt": RDTAllocation(name='x', l3='dd')},
         {"rdt": RDTAllocation(name='x', l3='dd')}, {"rdt": RDTAllocation(name='x', l3='dd')}),
        ({"rdt": RDTAllocation(name='x', l3='dd', mb='ff')},
         {"rdt": RDTAllocation(name='x', mb='ff')},
         {"rdt": RDTAllocation(name='x', l3='dd', mb='ff')}, {}),
    ))
def test_calculate_task_allocations(
        current_task_allocations, new_task_allocations,
        expected_target_task_allocations, expected_task_allocations_changeset):
    target_task_allocations, task_allocations_changeset = _calculate_task_allocations_changeset(
        current_task_allocations, new_task_allocations
    )
    assert target_task_allocations == expected_target_task_allocations
    assert task_allocations_changeset == expected_task_allocations_changeset


@pytest.mark.parametrize(
    'current_tasks_allocations,new_tasks_allocations,'
    'expected_target_tasks_allocations,expected_tasks_allocations_changeset', (
            ({}, {},
             {}, {}),
            (dict(t1={'a': 2}), {},
             dict(t1={'a': 2}), {}),
            (dict(t1={'a': 2}), dict(t1={'a': 2.01}),  # small enough to ignore
             dict(t1={'a': 2}), {}),
            (dict(t1={'a': 2}), dict(t1={'a': 2.1}),  # big enough to notice
             dict(t1={'a': 2.1}), dict(t1={'a': 2.1})),
            (dict(t1={'a': 2}), dict(t1={'a': 2}),
             dict(t1={'a': 2}), {}),
            (dict(t1={'a': 1}), dict(t1={'b': 2}, t2={'b': 3}),
             dict(t1={'a': 1, 'b': 2}, t2={'b': 3}), dict(t1={'b': 2}, t2={'b': 3})),
    ))
def test_calculate_tasks_allocations_changeset(
        current_tasks_allocations, new_tasks_allocations,
        expected_target_tasks_allocations, expected_tasks_allocations_changeset
):
    target_tasks_allocations, tasks_allocations_changeset = _calculate_tasks_allocations_changeset(
        current_tasks_allocations, new_tasks_allocations
    )
    assert target_tasks_allocations == expected_target_tasks_allocations
    assert tasks_allocations_changeset == expected_tasks_allocations_changeset


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
        ('mb:1=20;2=50', {'1': '20', '2': '50'}),
        ('mb:xxx=20mbs;2=50b', {'xxx': '20mbs', '2': '50b'}),
        ('l3:0=20;1=30', {'1': '30', '0': '20'}),
))
def test_parse_schemata_file_row(line, expected_domains):
    got_domains = _parse_schemata_file_row(line)
    assert got_domains == expected_domains


@pytest.mark.parametrize('invalid_line,expected_message', (
        ('x=', 'value cannot be empty'),
        ('x=2;x=3', 'Conflicting domain id found!'),
        ('=2', 'domain_id cannot be empty!'),
        ('2', 'Value separator is missing "="!'),
        (';', 'domain cannot be empty'),
        ('xxx', 'Value separator is missing "="!'),
))
def test_parse_invalid_schemata_file_domains(invalid_line, expected_message):
    with pytest.raises(ValueError, match=expected_message):
        _parse_schemata_file_row(invalid_line)


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
            rdt_metric_func('rdt_l3_cache_ways', 8, group_name='', domain_id='0'),
            rdt_metric_func('rdt_l3_mask', 255, group_name='', domain_id='0'),
        ]),
        (RDTAllocation(name='be', l3='l3:0=ff', mb='mb:0=20;1=30'), [
            rdt_metric_func('rdt_l3_cache_ways', 8, group_name='be', domain_id='0'),
            rdt_metric_func('rdt_l3_mask', 255, group_name='be', domain_id='0'),
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
        ({'some_task': {AllocationType.RDT: RDTAllocation(mb='mb:0=20')}}, [
            rdt_metric_func('rdt_mb', 20, group_name='', domain_id='0', task_id='some_task')
        ]),
        ({'some_task': {AllocationType.SHARES: 0.5,
                        AllocationType.RDT: RDTAllocation(mb='mb:0=20')}}, [
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
             rdt_metric_func('rdt_l3_cache_ways', 4, group_name='b',
                             domain_id='0', task_id='some_task_b'),
             rdt_metric_func('rdt_l3_mask', 15, group_name='b',
                             domain_id='0', task_id='some_task_b'),
             rdt_metric_func('rdt_l3_cache_ways', 5, group_name='b',
                             domain_id='1', task_id='some_task_b'),
             rdt_metric_func('rdt_l3_mask', 241, group_name='b',
                             domain_id='1', task_id='some_task_b'),
         ]),
))
def test_convert_task_allocations_to_metrics(tasks_allocations, expected_metrics):
    metrics_got = _convert_tasks_allocations_to_metrics(tasks_allocations)
    assert metrics_got == expected_metrics


@pytest.mark.parametrize(
    'current_rdt_alloaction, new_rdt_allocation,'
    'expected_target_rdt_allocation,expected_rdt_allocation_changeset', (
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
             RDTAllocation(name='new', l3='x', mb='y'), RDTAllocation(name='new', l3='x', mb='y')),
            (RDTAllocation(l3='x'), RDTAllocation(name='', l3='x'),
             RDTAllocation(name='', l3='x'), RDTAllocation(name='', l3='x'))
    )
)
def test_merge_rdt_allocations1(
        current_rdt_alloaction, new_rdt_allocation,
        expected_target_rdt_allocation, expected_rdt_allocation_changeset):
    got_target_rdt_allocation, got_rdt_alloction_changeset = \
        new_rdt_allocation.merge_with_current(current_rdt_alloaction)

    assert got_target_rdt_allocation == expected_target_rdt_allocation
    assert got_rdt_alloction_changeset == expected_rdt_allocation_changeset


def test_check_cbm_bits_valid():
    check_cbm_bits('ff00', 'ffff', '1')


@pytest.mark.parametrize(
    'mask, cbm_mask, min_cbm_bits, expected_error_message', (
            ('f0f', 'ffff', '1', 'without a gap'),
            ('0', 'ffff', '1', 'minimum'),
            ('ffffff', 'ffff', 'bigger', ''),
    )
)
def test_check_cbm_bits_gap(mask: str, cbm_mask: str, min_cbm_bits: str,
                            expected_error_message: str):
    with pytest.raises(ValueError, match=expected_error_message):
        check_cbm_bits(mask, cbm_mask, min_cbm_bits)
