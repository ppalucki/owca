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

from unittest.mock import patch

import pytest

from owca.containers import _find_new_and_dead_tasks, ContainerManager
from owca.testing import task, container
from owca.allocators import AllocationConfiguration


@pytest.mark.parametrize(
    'discovered_tasks, containers, expected_new_tasks, expected_containers_to_delete', (
        # scenario when two task are created and them first one is removed,
        ([task('/t1')], [],  # one new task, just arrived
         [task('/t1')], []),  # should created one container
        ([task('/t1')], [container('/t1')],  # after one iteration, our state is converged
         [], []),  # no actions
        ([task('/t1'), task('/t2')], [container('/t1'), ],  # another task arrived,
         [task('/t2')], []),  # let's create another container,
        ([task('/t1'), task('/t2')], [container('/t1'), container('/t2')],  # 2on2 converged
         [], []),  # nothing to do,
        ([task('/t2')], [container('/t1'), container('/t2')],  # first task just disappeared
         [], [container('/t1')]),  # remove the first container
        # some other cases
        ([task('/t1'), task('/t2')], [],  # the new task, just appeared
         [task('/t1'), task('/t2')], []),
        ([task('/t1'), task('/t3')], [container('/t1'),
                                      container('/t2')],  # t2 replaced with t3
         [task('/t3')], [container('/t2')]),  # nothing to do,
    ))
def test_find_new_and_dead_tasks(
        discovered_tasks,
        containers,
        expected_new_tasks,
        expected_containers_to_delete):
    new_tasks, containers_to_delete = _find_new_and_dead_tasks(
        discovered_tasks, containers
    )

    assert new_tasks == expected_new_tasks
    assert containers_to_delete == expected_containers_to_delete


@patch('owca.resctrl.ResGroup.add_pids')
@patch('owca.resctrl.clean_taskless_groups')
@patch('owca.perf.PerfCounters')
@patch('owca.containers.Container.sync')
@patch('owca.platforms.collect_topology_information', return_value=(1, 1, 1))
@pytest.mark.parametrize(
  'tasks, existing_containers, mon_groups_relation, expected_running_containers', (
    # No new containers and no existing containers, nothing in resctrl,
    ([], {}, {},
     {}),
    # One new task, should result in one new container, nothing in resctrl,
    ([task('/t1')], {}, {},
     {task('/t1'): container('/t1')}),
    # One another new task t2, should result in one another container, both in 'be' resgroup.
    ([task('/t1')], {task('/t2'): container('/t2')}, {'be': ['t2', 't1']},
     {task('/t1'): container('/t1')}),
    # Task t2 disapears, only t1 task/container should stay (t2 has it's own resgroup)
    ([task('/t1')], {task('/t1'): container('/t1'), task('/t2'): container('/t2')}, {'t2': ['t2']},
     {task('/t1'): container('/t1')}),
    # All tasks disapears, should result in no containers.
    ([], {task('/t1'): container('/t1'), task('/t2'): container('/t2')}, {},
     {})))
def test_sync_containers_state(platform_mock, sync_mock,
                               PerfCoutners_mock, clean_mock, ResGroup_mock,
                               tasks, existing_containers, mon_groups_relation,
                               expected_running_containers):

    containers_manager = ContainerManager(
        rdt_enabled=True,
        rdt_mb_control_enabled=False,
        platform_cpus=1,
        allocation_configuration=AllocationConfiguration(),
    )

    # Prepare internal state used by sync_containers_state function - mock.
    # Use list for copying to have original list.
    containers_manager._containers = dict(existing_containers)

    # Call it.
    with patch('owca.resctrl.read_mon_groups_relation', return_value=mon_groups_relation):
        got_containers = containers_manager.sync_containers_state(tasks)

    # Check internal state ...
    assert sorted(got_containers) == sorted(expected_running_containers)

    # Check other side effects like calling sync() on external objects.
    assert sync_mock.call_count == len(expected_running_containers)

    # Check container objects has proper resgroup assigned.
    got_container_resgroup_names = {c.container_name:
                                    c.resgroup.name for c in got_containers.values()}
    for expected_resgroup_name, container_names in mon_groups_relation.items():
        for container_name in container_names:
            if container_name in got_container_resgroup_names:
                got_resgroup_name = got_container_resgroup_names.get(container_name)
                assert got_resgroup_name == expected_resgroup_name
