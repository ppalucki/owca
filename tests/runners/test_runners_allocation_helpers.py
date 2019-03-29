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
from unittest.mock import Mock
from unittest.mock import patch

import pytest

from owca.allocations import InvalidAllocations
from owca.allocators import AllocationType, RDTAllocation, AllocationConfiguration
from owca.cgroups import Cgroup
from owca.containers import Container
from owca.platforms import RDTInformation
from owca.resctrl import ResGroup
from owca.resctrl_allocations import RDTGroups, RDTAllocationValue
from owca.runners.allocation import TasksAllocationsValues, TaskAllocationsValues, AllocationRunner
from owca.testing import allocation_metric, task, container
from owca.testing import platform_mock


@pytest.mark.parametrize('tasks_allocations, expected_metrics', (
        ({}, []),
        ({'t1_task_id': {AllocationType.SHARES: 0.5}}, [
            allocation_metric('cpu_shares', value=0.5,
                              container_name='t1', task='t1_task_id')
        ]),
        ({'t1_task_id': {AllocationType.RDT: RDTAllocation(mb='MB:0=20')}}, [
            allocation_metric('rdt_mb', 20, group_name='t1', domain_id='0', container_name='t1',
                              task='t1_task_id')
        ]),
        ({'t1_task_id': {AllocationType.SHARES: 0.5,
                         AllocationType.RDT: RDTAllocation(mb='MB:0=20')}}, [
             allocation_metric('cpu_shares', value=0.5, container_name='t1', task='t1_task_id'),
             allocation_metric('rdt_mb', 20, group_name='t1', domain_id='0', container_name='t1',
                               task='t1_task_id')
         ]),
        ({'t1_task_id': {
            AllocationType.SHARES: 0.5, AllocationType.RDT: RDTAllocation(mb='MB:0=30')
        },
             't2_task_id': {
                 AllocationType.QUOTA: 0.6,
                 AllocationType.RDT: RDTAllocation(name='b', l3='L3:0=f'),
             }
         }, [
             allocation_metric('cpu_shares', value=0.5, container_name='t1', task='t1_task_id'),
             allocation_metric('rdt_mb', 30, group_name='t1', domain_id='0', container_name='t1',
                               task='t1_task_id'),
             allocation_metric('cpu_quota', value=0.6, container_name='t2', task='t2_task_id'),
             allocation_metric('rdt_l3_cache_ways', 4, group_name='b',
                               domain_id='0', container_name='t2', task='t2_task_id'),
             allocation_metric('rdt_l3_mask', 15, group_name='b',
                               domain_id='0', container_name='t2', task='t2_task_id'),
         ]),
))
def test_allocations_generate_metrics(tasks_allocations, expected_metrics):
    """Check that proper allocations metrics are generated. """
    containers = {task('/t1'): container('/t1'),
                  task('/t2'): container('/t2'),
                  }
    allocations_values = TasksAllocationsValues.create(
        tasks_allocations, containers, platform_mock)
    allocations_values.validate()
    metrics_got = allocations_values.generate_metrics()
    assert metrics_got == expected_metrics


@pytest.mark.parametrize(
    'current, new, expected_target, expected_changeset', [
        ({}, {"rdt": RDTAllocation(name='', l3='ff')},
         {"rdt": RDTAllocation(name='', l3='ff')}, {"rdt": RDTAllocation(name='', l3='ff')}),
        ({"rdt": RDTAllocation(name='', l3='ff')}, {},
         {"rdt": RDTAllocation(name='', l3='ff')}, None),
        ({"rdt": RDTAllocation(name='', l3='ff')}, {"rdt": RDTAllocation(name='x', l3='ff')},
         {"rdt": RDTAllocation(name='x', l3='ff')}, {"rdt": RDTAllocation(name='x', l3='ff')}),
        ({"rdt": RDTAllocation(name='x', l3='ff')}, {"rdt": RDTAllocation(name='x', l3='dd')},
         {"rdt": RDTAllocation(name='x', l3='dd')}, {"rdt": RDTAllocation(name='x', l3='dd')}),
        ({"rdt": RDTAllocation(name='x', l3='dd', mb='ff')},
         {"rdt": RDTAllocation(name='x', mb='ff')},
         {"rdt": RDTAllocation(name='x', l3='dd', mb='ff')}, None),
    ]
)
def test_rdt_allocations_dict_changeset(current, new, expected_target, expected_changeset):
    """Check that changeset is properly calculated."""

    # We need have to convert simple objects to wrapped using mocks, so
    # prepare class mocks (constructors).
    CgroupMock = Mock(spec=Cgroup)
    ResGroupMock = Mock(spec=ResGroup)
    ContainerMock = Mock(spec=Container)

    # Limiter for rdtgroups - 20 is enough to be not limited by number of rdtgroups.
    rdt_groups = RDTGroups(20)

    def rdt_allocation_value_constructor(allocation_value, container, common_labels):
        return RDTAllocationValue('c1', allocation_value, CgroupMock(), ResGroupMock(),
                                  platform_sockets=1, rdt_mb_control_enabled=False,
                                  rdt_cbm_mask='fff', rdt_min_cbm_bits='1',
                                  rdt_groups=rdt_groups,
                                  common_labels=common_labels,
                                  )

    def convert_dict(simple_dict):
        if simple_dict is not None:
            return TaskAllocationsValues.create(
                simple_dict,
                container=ContainerMock(),
                registry={AllocationType.RDT: rdt_allocation_value_constructor},
                common_labels={})
        else:
            return None

    # Convert both current and new value.
    current_values = convert_dict(current)
    new_values = convert_dict(new)
    expected_changeset_values = convert_dict(expected_changeset)
    expected_target_values = convert_dict(expected_target)

    # Calculate the difference to get changeset.
    got_target_values, got_changeset_values = new_values.calculate_changeset(current_values)

    assert got_changeset_values == expected_changeset_values
    assert got_target_values == expected_target_values


@pytest.mark.parametrize('tasks_allocations,expected_error', [
    ({'tx': {'cpu_shares': 3}}, 'invalid task id'),
    ({'t1_task_id': {'wrong_type': 5}}, 'unknown allocation type'),
    ({'t1_task_id': {'rdt': RDTAllocation()},
      't2_task_id': {'rdt': RDTAllocation()},
      't3_task_id': {'rdt': RDTAllocation()}},
     'too many resource groups for available CLOSids'),
])
def test_convert_invalid_task_allocations(tasks_allocations, expected_error):
    """After allocations are converted, check that for improper input values
    proper validation exception with appropriate message is raised."""
    containers = {task('/t1'): container('/t1'),
                  task('/t2'): container('/t2'),
                  task('/t3'): container('/t3'),
                  }
    with pytest.raises(InvalidAllocations, match=expected_error):
        got_allocations_values = TasksAllocationsValues.create(
            tasks_allocations, containers, platform_mock)
        got_allocations_values.validate()


@pytest.mark.parametrize(
    'tasks_allocations,expected_resgroup_reallocation_count',
    (
            # No RDT allocations.
            (
                    {
                        't1_task_id': {AllocationType.QUOTA: 0.6},
                    },
                    0
            ),
            # The both task in the same resctrl group.
            (
                    {
                        't1_task_id': {'rdt': RDTAllocation(name='be', l3='L3:0=ff')},
                        't2_task_id': {'rdt': RDTAllocation(name='be', l3='L3:0=ff')}
                    },
                    1
            ),
            # The tasks in seperate resctrl group.
            (
                    {
                        't1_task_id': {'rdt': RDTAllocation(name='be', l3='L3:0=ff')},
                        't2_task_id': {'rdt': RDTAllocation(name='le', l3='L3:0=ff')}
                    },
                    2
            ),
            # The tasks in root group (even with diffrent l3 values)
            (
                    {
                        't1_task_id': {'rdt': RDTAllocation(name='', l3='L3:0=ff')},
                        't2_task_id': {'rdt': RDTAllocation(name='', l3='L3:0=ff')}
                    },
                    1
            ),
            # The tasks are in autonamed groups (force execution always)
            (
                    {
                        't1_task_id': {'rdt': RDTAllocation(l3='L3:0=ff')},
                        't2_task_id': {'rdt': RDTAllocation(l3='L3:0=ff')}
                    },
                    2
            ),
    )
)
def test_unique_rdt_allocations(tasks_allocations, expected_resgroup_reallocation_count):
    """Checks if allocation of resctrl group is performed only once if more than one
       task_allocations has RDTAllocation with the same name. In other words,
       check if unnecessary reallocation of resctrl group does not take place.

       The goal is achieved by checking how many times
       Container.write_schemata is called with allocate_rdt=True."""
    containers = {task('/t1'): container('/t1', resgroup_name='', with_config=True),
                  task('/t2'): container('/t2', resgroup_name='', with_config=True)}
    allocations_values = TasksAllocationsValues.create(
        tasks_allocations, containers, platform_mock)
    allocations_values.validate()
    with patch('owca.resctrl.ResGroup.write_schemata') as mock, \
            patch('owca.cgroups.Cgroup._write'), patch('owca.cgroups.Cgroup._read'):
        allocations_values.perform_allocations()
        assert mock.call_count == expected_resgroup_reallocation_count


@pytest.mark.parametrize(
    'default_rdt_l3, default_rdt_mb,'
    'config_rdt_mb_control_enabled, platform_rdt_mb_control_enabled,'
    'expected_exception, expected_final_rdt_mb_control_enabled_with_value,'
    'expected_cleanup_arguments', [
        # rdt mb is not enabled and not detected on platform, there should be no call nor exception
        (None, None, False, False, None, False, ('L3:0=fff', None)),
        # rdt mb is not enabled but detected on platform - configure l3 to max, but not mb
        (None, None, False, True, None, False, ('L3:0=fff', None)),  # mask based on cbm_mask below
        # rdt mb is enabled and not detected on platform, there should be exception
        (None, None, True, False, 'RDT MB control is not supported', False, None),
        # rdt mb is enabled and available on platform, there should be no exception
        (None, None, True, True, None, True, ('L3:0=fff', 'MB:0=100')),
        # rdt mb is enabled and available on platform, there should be no exception, but use MB=50
        (None, 'MB:0=50', True, True, None, True, ('L3:0=fff', 'MB:0=50')),
        # rdt mb is enabled and available on platform, there should be no exception, but use L3=f
        ('L3:0=00f', None, True, True, None, True, ('L3:0=00f', 'MB:0=100')),
        # rdt mb is enabled and available on platform, there should be no exception, but use both
        ('L3:0=00f', 'MB:0=50', True, True, None, True, ('L3:0=00f', 'MB:0=50')),
        # rdt mb is not enabled and not available on platform, no exception, and just set L3
        ('L3:0=00f', 'MB:0=50', False, False, None, False, ('L3:0=00f', None)),
        # wrong values
        ('wrongl3', 'MB:0=50', True, True, 'l3 resources setting should start with', True, None),
        ('L3:0=00f', 'wrong mb', True, True, 'mb resources setting should start with', True, None),
    ]
)
@patch('owca.resctrl.cleanup_resctrl')
@patch('owca.platforms.collect_platform_information', return_value=(platform_mock, [], {}))
def test_rdt_initialize(rdt_max_values_mock, cleanup_resctrl_mock,
                        default_rdt_l3, default_rdt_mb,
                        config_rdt_mb_control_enabled,
                        platform_rdt_mb_control_enabled,
                        expected_exception,
                        expected_final_rdt_mb_control_enabled_with_value,
                        expected_cleanup_arguments,
                        ):
    allocation_configuration = AllocationConfiguration(
        default_rdt_mb=default_rdt_mb,
        default_rdt_l3=default_rdt_l3
    )
    runner = AllocationRunner(
        node=Mock(),
        allocator=Mock(),
        metrics_storage=Mock(),
        anomalies_storage=Mock(),
        allocations_storage=Mock(),
        action_delay=1,
        rdt_enabled=True,
        rdt_mb_control_enabled=config_rdt_mb_control_enabled,
        allocation_configuration=allocation_configuration,
    )

    with patch('owca.testing.platform_mock.rdt_information', Mock(
            spec=RDTInformation,
            cbm_mask='fff', min_cbm_bits='2',
            rdt_mb_control_enabled=platform_rdt_mb_control_enabled)):
        if expected_exception:
            with pytest.raises(Exception, match=expected_exception):
                runner._initialize_rdt()
        else:
            runner._initialize_rdt()

    if expected_final_rdt_mb_control_enabled_with_value:
        assert runner._rdt_mb_control_enabled == expected_final_rdt_mb_control_enabled_with_value

    if expected_cleanup_arguments:
        cleanup_resctrl_mock.assert_called_with(*expected_cleanup_arguments)
    else:
        assert cleanup_resctrl_mock.call_count == 0
