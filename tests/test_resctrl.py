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


import errno
from unittest.mock import call, MagicMock, patch, mock_open, Mock
from typing import List, Dict

import pytest

from owca.allocations import AllocationsDict
from owca.allocators import AllocationValue, AllocationConfiguration
from owca.cgroups import Cgroup

from owca.resctrl import ResGroup, check_resctrl, RESCTRL_ROOT_NAME, get_max_rdt_values, \
    RDTAllocation, check_cbm_bits, _count_enabled_bits, _parse_schemata_file_row, RDTAllocationValue
from owca.testing import create_open_mock, rdt_metric_func


@patch('builtins.open', new=create_open_mock({
    "/sys/fs/resctrl": "0",
    "/sys/fs/resctrl/tasks": "0",
    "/sys/fs/resctrl/mon_data/mon_L3_00/mbm_total_bytes": "0",
}))
def test_check_resctrl(*mock):
    assert check_resctrl()


@patch('owca.resctrl.log.warning')
@patch('os.path.exists', return_value=True)
@patch('os.makedirs')
@patch('owca.resctrl.SetEffectiveRootUid')
def test_add_tasks(*args):
    root_tasks_mock = MagicMock()
    tasks_mock = MagicMock()
    mongroup_tasks_mock = MagicMock()
    open_mock = create_open_mock({
        "/sys/fs/resctrl": "0",
        "/sys/fs/resctrl/tasks": root_tasks_mock,
        # for best_efforts resctrl group
        "/sys/fs/resctrl/best_efforts/tasks": tasks_mock,
        "/sys/fs/resctrl/best_efforts/mon_groups/task_id/tasks": mongroup_tasks_mock,
    })
    with patch('builtins.open', open_mock):
        resgroup = ResGroup("best_efforts")
        resgroup.add_tasks(['123', '124'], 'task_id')

        tasks_mock.assert_called_once_with(
            '/sys/fs/resctrl/best_efforts/tasks', 'w')
        tasks_mock.assert_has_calls([call().__enter__().write('123')])
        tasks_mock.assert_has_calls([call().__enter__().write('124')])

        mongroup_tasks_mock.assert_called_once_with(
            '/sys/fs/resctrl/best_efforts/mon_groups/task_id/tasks', 'w')
        mongroup_tasks_mock.assert_has_calls([call().__enter__().write('123')])
        mongroup_tasks_mock.assert_has_calls([call().__enter__().write('124')])


@patch('os.path.isdir', return_value=True)
@patch('os.rmdir')
@patch('owca.resctrl.SetEffectiveRootUid')
def test_remove_tasks(isdir_mock, rmdir_mock, *args):
    root_tasks_mock = mock_open()
    open_mock = create_open_mock({
        "/sys/fs/resctrl": "0",
        "/sys/fs/resctrl/tasks": root_tasks_mock,
        "/sys/fs/resctrl/best_efforts/mon_groups/task_id/tasks": "123\n124\n",
    })
    with patch('owca.resctrl.open', open_mock):
        resgroup = ResGroup("best_efforts")
        resgroup.remove_tasks('task_id')
        rmdir_mock.assert_called_once_with('/sys/fs/resctrl/best_efforts/mon_groups/task_id')
        # Assure that only two pids were written to the root group.
        root_tasks_mock().assert_has_calls([
            call.write('123'),
            call.flush(),
            call.write('124'),
            call.flush()])


@patch('owca.resctrl.log.warning')
@patch('os.path.exists', return_value=True)
@patch('os.makedirs', side_effect=OSError(errno.ENOSPC, "mock"))
@patch('builtins.open', new=create_open_mock({
    "/sys/fs/cgroup/cpu/ddd/tasks": "123",
}))
def test_sync_no_space_left_on_device(makedirs_mock, exists_mock, log_warning_mock):
    with pytest.raises(Exception, match='Limit of workloads reached'):
        ResGroup("best_efforts")


@patch('builtins.open', new=create_open_mock({
    "/sys/fs/resctrl/mon_groups/best_efforts/mon_data/1/mbm_total_bytes": "1",
    "/sys/fs/resctrl/mon_groups/best_efforts/mon_data/2/mbm_total_bytes": "1",
    "/sys/fs/resctrl/mon_groups/best_efforts/mon_data/1/llc_occupancy": "1",
    "/sys/fs/resctrl/mon_groups/best_efforts/mon_data/2/llc_occupancy": "1",
    "/sys/fs/cgroup/cpu/best_efforts/cpuacct.usage": "4",
}))
@patch('os.listdir', return_value=['1', '2'])
def test_get_measurements(*mock):
    resgroup = ResGroup(name=RESCTRL_ROOT_NAME)
    assert {'memory_bandwidth': 2, 'llc_occupancy': 2} == resgroup.get_measurements('best_efforts')


@patch('os.listdir', return_value=['mesos-1', 'mesos-2', 'mesos-3'])
@patch('os.rmdir')
@patch('os.path.isdir', return_value=True)
@patch('os.path.exists', return_value=True)
def test_clean_resctrl(exists_mock, isdir_mock, rmdir_mock, listdir_mock):
    from owca.resctrl import cleanup_resctrl

    schemata_mock = mock_open()

    with patch('builtins.open', new=create_open_mock({
            "/sys/fs/resctrl/mesos-1/tasks": "1\n2\n",
            # resctrl group to recycle - expected to be removed.
            "/sys/fs/resctrl/mesos-2/tasks": "",
            "/sys/fs/resctrl/mesos-3/tasks": "2",
            "/sys/fs/resctrl/mon_groups/mesos-1/tasks": "1\n2\n",
            # resctrl group to recycle - should be removed.
            "/sys/fs/resctrl/mon_groups/mesos-2/tasks": "",
            "/sys/fs/resctrl/mon_groups/mesos-3/tasks": "2",
            # default values expected to be written
            "/sys/fs/resctrl/schemata": schemata_mock})):
        cleanup_resctrl(root_rdt_l3='L3:0=ff', root_rdt_mb='MB:0=100')

    listdir_mock.assert_has_calls([
        call('/sys/fs/resctrl/mon_groups'),
        call('/sys/fs/resctrl/')
    ])
    isdir_mock.assert_has_calls([
        call('/sys/fs/resctrl/mon_groups/mesos-1'),
        call('/sys/fs/resctrl/mon_groups/mesos-2'),
        call('/sys/fs/resctrl/mon_groups/mesos-3'),
        call('/sys/fs/resctrl/mesos-1'),
        call('/sys/fs/resctrl/mesos-2'),
        call('/sys/fs/resctrl/mesos-3'),
    ])
    exists_mock.assert_has_calls([
        call('/sys/fs/resctrl/mon_groups/mesos-1/tasks'),
        call('/sys/fs/resctrl/mon_groups/mesos-2/tasks'),
        call('/sys/fs/resctrl/mon_groups/mesos-3/tasks'),
        call('/sys/fs/resctrl/mesos-1/tasks'),
        call('/sys/fs/resctrl/mesos-2/tasks'),
        call('/sys/fs/resctrl/mesos-3/tasks')
    ])

    rmdir_mock.assert_has_calls([
        call('/sys/fs/resctrl/mon_groups/mesos-1'),
        call('/sys/fs/resctrl/mon_groups/mesos-2'),
        call('/sys/fs/resctrl/mon_groups/mesos-3'),
        call('/sys/fs/resctrl/mesos-1'),
        call('/sys/fs/resctrl/mesos-2'),
        call('/sys/fs/resctrl/mesos-3')
    ])

    schemata_mock.assert_has_calls([
        call().write(b'L3:0=ff\n'),
        call().write(b'MB:0=100\n'),
    ], any_order=True)


@pytest.mark.parametrize(
    'cbm_mask, platform_sockets, expected_max_rdt_l3, expected_max_rdt_mb', (
        ('ff', 0, 'L3:', 'MB:'),
        ('ff', 1, 'L3:0=ff', 'MB:0=100'),
        ('ffff', 2, 'L3:0=ffff;1=ffff', 'MB:0=100;1=100'),
    )
)
def test_get_max_rdt_values(cbm_mask, platform_sockets, expected_max_rdt_l3, expected_max_rdt_mb):
    got_max_rdt_l3, got_max_rdt_mb = get_max_rdt_values(cbm_mask, platform_sockets)
    assert got_max_rdt_l3 == expected_max_rdt_l3
    assert got_max_rdt_mb == expected_max_rdt_mb


@pytest.mark.parametrize(
    'resgroup_args, task_allocations, expected_writes', [
        (dict(name=''), {'rdt': RDTAllocation(name='', l3='ble')},
         {'/sys/fs/resctrl/schemata': [b'ble\n']}),
        (dict(name='be'), {'rdt': RDTAllocation(name='be', l3='ble')},
         {'/sys/fs/resctrl/be/schemata': [b'ble\n']}),
        (dict(name='be', rdt_mb_control_enabled=False), {'rdt': RDTAllocation(
            name='be', l3='l3write', mb='mbwrite')},
         {'/sys/fs/resctrl/be/schemata': [b'l3write\n']}),
        (dict(name='be', rdt_mb_control_enabled=True), {'rdt': RDTAllocation(
            name='be', l3='l3write', mb='mbwrite')},
         {'/sys/fs/resctrl/be/schemata': [b'l3write\n', b'mbwrite\n']}),
    ]
)
def test_resgroup_perform_allocations(resgroup_args, task_allocations,
                                      expected_writes: Dict[str, List[str]]):

    write_mocks = {filename: mock_open() for filename in expected_writes}
    with patch('os.makedirs'):
        resgroup = ResGroup(**resgroup_args)

    with patch('builtins.open', new=create_open_mock(write_mocks)):
        resgroup.perform_allocations(task_allocations)

    for filename, write_mock in write_mocks.items():
        expected_filename_writes = expected_writes[filename]
        expected_write_calls = [call().write(write_body) for write_body in expected_filename_writes]
        assert expected_filename_writes
        write_mock.assert_has_calls(expected_write_calls, any_order=True)

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

def test_check_cbm_bits_valid():
    check_cbm_bits('ff00', 'ffff', '1')


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
def test_merge_rdt_allocations(
        current_rdt_alloaction, new_rdt_allocation,
        expected_target_rdt_allocation, expected_rdt_allocation_changeset):


    cgroup = Cgroup(cgroup_path='/test', platform_cpus=2,
                    allocation_configuration=AllocationConfiguration())
    resgroup = ResGroup(name='')

    def convert(rdt_allocation):
        if rdt_allocation is not None:
            return RDTAllocationValue(rdt_allocation, resgroup, cgroup)
        else:
            return None

    current_rdt_allocation_value = convert(current_rdt_alloaction)
    new_rdt_allocation_value = convert(new_rdt_allocation)

    expected_target_rdt_allocation_value = convert(expected_target_rdt_allocation)
    expected_rdt_allocation_changeset_value = convert(expected_rdt_allocation_changeset)

    got_target_rdt_allocation_value, got_rdt_alloction_changeset_value = \
        new_rdt_allocation_value.merge_with_current(current_rdt_allocation_value)

    assert got_target_rdt_allocation_value == expected_target_rdt_allocation_value
    assert got_rdt_alloction_changeset_value == expected_rdt_allocation_changeset_value

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
    with patch('owca.resctrl.ResGroup._create_controlgroup_directory'):
        rdt_allocation_value = RDTAllocationValue(rdt_allocation, cgroup=Cgroup('/', platform_cpus=1),
                                                  resgroup=ResGroup(name=rdt_allocation.name or ''))
        got_metrics = rdt_allocation_value.generate_metrics()
    assert got_metrics == expected_metrics


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
        # RDTAllocations
        ({}, {"rdt": RDTAllocation(name='', l3='ff')},
         {"rdt": RDTAllocation(name='', l3='ff')}, {"rdt": RDTAllocation(name='', l3='ff')}),
        ({"rdt": RDTAllocation(name='', l3='ff')}, {},
         {"rdt": RDTAllocation(name='', l3='ff')}, None),
        ({"rdt": RDTAllocation(name='', l3='ff')}, {"rdt": RDTAllocation(name='x', l3='ff')},
         {"rdt": RDTAllocation(name='x', l3='ff')}, {"rdt": RDTAllocation(name='x', l3='ff')}),
        ({"rdt": RDTAllocation(name='x', l3='ff')}, {"rdt": RDTAllocation(name='x', l3='dd')},
         {"rdt": RDTAllocation(name='x', l3='dd')}, {"rdt": RDTAllocation(name='x', l3='dd')}),
        ({"rdt": RDTAllocation(name='x', l3='dd', mb='ff')}, {"rdt": RDTAllocation(name='x', mb='ff')},
         {"rdt": RDTAllocation(name='x', l3='dd', mb='ff')}, None),
    ]
)
def test_allocations_dict_merging(current, new,
                                  expected_target, expected_changeset):

    # Extra mapping
    from owca.resctrl import RDTAllocationValue

    CgroupMock = Mock(spec=Cgroup)
    ResGroupMock = Mock(spec=ResGroup)

    def rdt_allocation_value_constructor(value, ctx, mapping):
        return RDTAllocationValue(value, CgroupMock(), ResGroupMock())

    mapping = {('rdt', RDTAllocation): rdt_allocation_value_constructor}


    def convert_dict(d):
        return AllocationsDict(d, None, mapping)

    # conversion
    current_dict = convert_dict(current)
    new_dict = convert_dict(new)
    if expected_changeset is not None:
        assert isinstance(expected_changeset, dict)
        expected_allocations_changeset_dict = convert_dict(expected_changeset)
    else:
        expected_allocations_changeset_dict = None
    expected_target_allocations_dict = convert_dict(expected_target)

    # merge
    got_target_dict, got_changeset_dict = \
        new_dict.merge_with_current(current_dict)

    assert got_target_dict == expected_target_allocations_dict
    assert got_changeset_dict == expected_allocations_changeset_dict