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

from unittest.mock import patch, Mock

import pytest

from owca.allocators import AllocationType
from owca.containers import ContainerManager, _calculate_desired_state
from owca.resctrl import RDTAllocation
from owca.runner import DetectionRunner
from owca.testing import task, container


@pytest.mark.parametrize(
    'discovered_tasks,containers,expected_new_tasks,expected_containers_to_delete', (
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
def test_calculate_desired_state(
        discovered_tasks,
        containers,
        expected_new_tasks,
        expected_containers_to_delete):
    new_tasks, containers_to_delete = _calculate_desired_state(
        discovered_tasks, containers
    )

    assert new_tasks == expected_new_tasks
    assert containers_to_delete == expected_containers_to_delete


@patch('owca.containers.ResGroup')
@patch('owca.containers.PerfCounters')
@patch('owca.containers.Container.sync')
@patch('owca.containers.Container.cleanup')
@patch('owca.platforms.collect_topology_information', return_value=(1, 1, 1))
@pytest.mark.parametrize('tasks,existing_containers,expected_running_containers', (
    ([], {},
     {}),
    ([task('/t1')], {},
     {task('/t1'): container('/t1')}),
    ([task('/t1')], {task('/t2'): container('/t2')},
     {task('/t1'): container('/t1')}),
    ([task('/t1')], {task('/t1'): container('/t1'), task('/t2'): container('/t2')},
     {task('/t1'): container('/t1')}),
    ([], {task('/t1'): container('/t1'), task('/t2'): container('/t2')},
     {}),
))
def test_sync_containers_state(platform_mock, cleanup_mock, sync_mock,
                               PerfCoutners_mock, ResGroup_mock,
                               tasks, existing_containers,
                               expected_running_containers):
    # Mocker runner, because we're only interested in one sync_containers_state function.
    runner = DetectionRunner(
        node=Mock(),
        metrics_storage=Mock(),
        anomalies_storage=Mock(),
        detector=Mock(),
        rdt_enabled=False,
    )
    # Prepare internal state used by sync_containers_state function - mock.
    # Use list for copying to have original list.
    runner.containers_manager.containers = dict(existing_containers)

    # Call it.
    got_containers = runner.containers_manager.sync_containers_state(tasks)

    # Check internal state ...
    assert expected_running_containers == got_containers

    # Check other side effects like calling sync() on external objects.
    assert sync_mock.call_count == len(expected_running_containers)
    number_of_removed_containers = len(set(existing_containers) - set(expected_running_containers))
    assert cleanup_mock.call_count == number_of_removed_containers


@patch('owca.mesos.MesosTask')
@pytest.mark.parametrize(
    'tasks_allocations,expected_resgroup_reallocation_count',
    (
        # No RDT allocations.
        (
            {
                'task_id_1': {AllocationType.QUOTA: 0.6},
            },
            0
        ),
        # The both task in the same resctrl group.
        (
            {
                'task_id_1': {'rdt': RDTAllocation(name='be', l3='ff')},
                'task_id_2': {'rdt': RDTAllocation(name='be', l3='ff')}
            },
            1
        ),
        # The tasks in seperate resctrl group.
        (
            {
                'task_id_1': {'rdt': RDTAllocation(name='be', l3='ff')},
                'task_id_2': {'rdt': RDTAllocation(name='le', l3='ff')}
            },
            2
        ),
    )
)
def test_cm_perform_allocations(MesosTaskMock, tasks_allocations,
                                expected_resgroup_reallocation_count):
    """Checks if allocation of resctrl group is performed only once if more than one
       task_allocations has RDTAllocation with the same name. In other words,
       check if unnecessary reallocation of resctrl group does not take place.

       The goal is achieved by checking how many times
       Container.perform_allocations is called with allocate_rdt=True."""
    # Minimal MesosTask mock needed for the test.
    tasks = []
    tasks_ = {}
    for task_id in tasks_allocations.keys():
        task = Mock(task_id=task_id)
        tasks.append(task)
        tasks_[task_id] = task

    container_manager = ContainerManager(True, True, 1, None)
    container_manager.containers = {task: Mock() for task in tasks}

    # Call the main function to test.
    container_manager._perfom_allocations(tasks_allocations)

    count_ = 0
    for task_id, _ in tasks_allocations.items():
        perform_allocations_mock = container_manager.containers[tasks_[task_id]].perform_allocations
        assert len(perform_allocations_mock.mock_calls) == 1
        args, kwargs = perform_allocations_mock.call_args_list[0]
        _, allocate_rdt_called = args
        count_ = count_ + 1 if allocate_rdt_called else count_
    assert expected_resgroup_reallocation_count == count_
