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

"""
The module contains high level tests of the project.
The classes derived from BaseRunnerMixin class are tested.
"""


from unittest.mock import patch, Mock

import pytest

from owca.runner import DetectionRunner, AllocationRunner, convert_to_allocations_values
from owca.mesos import MesosNode, sanitize_mesos_label
from owca import storage
from owca import platforms
from owca.metrics import Metric, MetricType
from owca.detectors import AnomalyDetector
from owca.allocators import Allocator, AllocationType, AllocationConfiguration
from owca.resctrl import RDTAllocation
from owca.testing import anomaly_metrics, anomaly, task, container, metric, allocation_metric


# We are mocking objects used by containers.
@patch('owca.testing._create_uuid_from_tasks_ids', return_value='fake-uuid')
@patch('owca.detectors._create_uuid_from_tasks_ids', return_value='fake-uuid')
@patch('owca.runner.are_privileges_sufficient', return_value=True)
@patch('owca.containers.ResGroup')
@patch('owca.containers.PerfCounters')
@patch('owca.platforms.collect_topology_information', return_value=(1, 1, 1))
@patch('owca.containers.Cgroup.get_measurements', return_value=dict(cpu_usage=23))
@patch('time.time', return_value=1234567890.123)
def test_detection_runner_containers_state(*mocks):
    """Tests proper interaction between runner instance and functions for
    creating anomalies and calculating the desired state.

    Also tests labelling of metrics during iteration loop.
    """

    # Task labels
    task_labels = {
        'org.apache.aurora.metadata.application': 'redis',
        'org.apache.aurora.metadata.load_generator': 'rpc-perf',
        'org.apache.aurora.metadata.name': 'redis--6792',
    }
    task_labels_sanitized = {
        sanitize_mesos_label(label_key): label_value
        for label_key, label_value
        in task_labels.items()
    }
    task_labels_sanitized_with_task_id = {'task_id': 'task-id-/t1'}
    task_labels_sanitized_with_task_id.update(task_labels_sanitized)

    # Node mock
    node_mock = Mock(spec=MesosNode, get_tasks=Mock(return_value=[
        task('/t1', resources=dict(cpus=8.), labels=task_labels)]))

    # Storage mocks
    metrics_storage = Mock(spec=storage.Storage, store=Mock())
    anomalies_storage = Mock(spec=storage.Storage, store=Mock())

    # Detector mock - simulate returning one anomaly and additional metric
    detector_mock = Mock(
        spec=AnomalyDetector,
        detect=Mock(
            return_value=(
                [anomaly(
                    'task1', ['task2'], metrics=[
                        metric('contention_related_metric')
                    ]
                )],  # one anomaly + related metric
                [metric('bar')]  # one extra metric
            )
        )
    )

    extra_labels = dict(el='ev')  # extra label with some extra value

    runner = DetectionRunner(
        node=node_mock,
        metrics_storage=metrics_storage,
        anomalies_storage=anomalies_storage,
        detector=detector_mock,
        rdt_enabled=False,
        extra_labels=extra_labels,
    )

    # Mock to finish after one iteration.
    runner.wait_or_finish = Mock(return_value=False)

    platform_mock = Mock(spec=platforms.Platform)
    with patch('owca.platforms.collect_platform_information', return_value=(
            platform_mock, [metric('platform-cpu-usage')], {})):
        runner.run()

    # store() method was called twice:
    # 1. Before calling detect() to store state of the environment.
    metrics_storage.store.assert_called_once_with([
        Metric('owca_up', type=MetricType.COUNTER, value=1234567890.123, labels=extra_labels),
        Metric('owca_tasks', type=MetricType.GAUGE, value=1, labels=extra_labels),
        metric('platform-cpu-usage', labels=extra_labels),  # Store metrics from platform ...
        Metric(name='cpu_usage', value=23,
               labels=dict(extra_labels, **task_labels_sanitized_with_task_id)),
    ])  # and task

    # 2. After calling detect to store information about detected anomalies.
    expected_anomaly_metrics = anomaly_metrics('task1', ['task2'])
    for m in expected_anomaly_metrics:
        m.labels.update(extra_labels)

    expected_anomaly_metrics.extend([
        metric('contention_related_metric',
               labels=dict({'uuid': 'fake-uuid', 'type': 'anomaly'}, **extra_labels)),
        metric('bar', extra_labels),
        Metric('anomaly_count', type=MetricType.COUNTER, value=1, labels=extra_labels),
        Metric('anomaly_last_occurence', type=MetricType.COUNTER, value=1234567890.123,
               labels=extra_labels),
        Metric(name='detect_duration', value=0.0, labels={'el': 'ev'}, type=MetricType.GAUGE),
    ])
    anomalies_storage.store.assert_called_once_with(expected_anomaly_metrics)

    # Check that detector was called with proper arguments.
    detector_mock.detect.assert_called_once_with(
        platform_mock,
        {'task-id-/t1': {'cpu_usage': 23}},
        {'task-id-/t1': {'cpus': 8}},
        {'task-id-/t1': task_labels_sanitized_with_task_id}
    )

    # assert expected state (new container based on first task /t1)
    assert (runner.containers_manager.containers ==
            {task('/t1', resources=dict(cpus=8.), labels=task_labels): container('/t1')})

    runner.wait_or_finish.assert_called_once()


@pytest.mark.skip('TODO')
@patch('time.time', return_value=1234567890.123)
@patch('owca.platforms.collect_topology_information', return_value=(1, 1, 1))
@patch('owca.runner.are_privileges_sufficient', return_value=True)
@patch('owca.runner.AllocationRunner.configure_rdt', return_value=True)
@patch('owca.containers.Container.get_pids', return_value=['123'])
@patch('owca.containers.Container.get_allocations', return_value={})
@patch('owca.containers.PerfCounters')
@patch('owca.containers.Cgroup.get_measurements', return_value=dict(cpu_usage=23))
@patch('owca.containers.Cgroup.write_schemata')
@patch('owca.resctrl.ResGroup.add_tasks')
@patch('owca.resctrl.ResGroup.move_tasks_to_root')
@patch('owca.resctrl.ResGroup._create_controlgroup_directory')
@patch('owca.resctrl.ResGroup.get_measurements')
@patch('owca.resctrl.ResGroup.write_schemata')
@patch('owca.resctrl.ResGroup.cleanup')
@patch('owca.detectors._create_uuid_from_tasks_ids', return_value='fake-uuid')
@patch('owca.testing._create_uuid_from_tasks_ids', return_value='fake-uuid')
def test_allocation_runner_containers_state(*mocks):
    """ Low level system calls are not mocked - but higher level objects and functions:
        Cgroup, Resgroup, Platform, etc. Thus the test do not cover the full usage scenario
        (such tests would be much harder to write).
    """
    # Mock platform.
    platform_mock = Mock(spec=platforms.Platform, sockets=2,
                         rdt_cbm_mask='fffff', rdt_min_cbm_bits=1)

    task_labels_sanitized_with_task_id = {'task_id': 'task-id-/t1'}

    # Node mock.
    mesos_node_mock = Mock(spec=MesosNode, get_tasks=Mock(return_value=[
        task('/t1', resources=dict(cpus=8.), labels={})]))

    # Storage mocks.
    metrics_storage = Mock(spec=storage.Storage, store=Mock())
    anomalies_storage = Mock(spec=storage.Storage, store=Mock())
    allocations_storage = Mock(spec=storage.Storage, store=Mock())

    # Detector mock - simulate returning one anomaly and additional metric.
    allocations = {'task-id-/t1': {AllocationType.QUOTA: 1000,
                                   AllocationType.RDT: RDTAllocation(name='only_group',
                                                                     l3='L3:0=00fff;1=0ffff')}}

    # Patch some of the functions of AllocationRunner.
    runner = AllocationRunner(
        node=mesos_node_mock,
        metrics_storage=metrics_storage,
        anomalies_storage=anomalies_storage,
        allocations_storage=allocations_storage,
        rdt_enabled=True,
        ignore_privileges_check=True,
        allocator=Mock(spec=Allocator),
        extra_labels={},
    )

    def _ignore_invalid_allocations(platform, new_tasks_allocations):
        return (0, new_tasks_allocations)
    runner._ignore_invalid_allocations = Mock(side_effect=_ignore_invalid_allocations)
    runner.wait_or_finish = Mock(return_value=False)
    runner.allocator.allocate.return_value = allocations, [], []

    ############
    # First run.
    with patch('owca.platforms.collect_platform_information', return_value=(
            platform_mock, [metric('platform-cpu-usage')], {})):
        runner.run()

    # Checking state after run.
    assert (len(runner.containers_manager.resgroups_containers_relation[''][1]) == 0)
    assert (len(runner.containers_manager.resgroups_containers_relation['only_group'][1]) == 1)

    # Check whether allocate run with proper arguments.
    runner.allocator.allocate.assert_called_once_with(
        platform_mock,
        {'task-id-/t1': {'cpu_usage': 23}},
        {'task-id-/t1': {'cpus': 8}},
        {'task-id-/t1': task_labels_sanitized_with_task_id},
        {'task-id-/t1': {}}
    )

    ############
    # Second run.
    runner.node = Mock(spec=MesosNode, get_tasks=Mock(return_value=[
        task('/t1', resources=dict(cpus=8.), labels={}),
        task('/t2', resources=dict(cpus=9.), labels={})]))
    with patch('owca.platforms.collect_platform_information', return_value=(
            platform_mock, [metric('platform-cpu-usage')], {})):
        runner.run()

    # Checking state after run.
    assert (len(runner.containers_manager.resgroups_containers_relation['only_group'][1]) == 1)
    assert (len(runner.containers_manager.resgroups_containers_relation[''][1]) == 1)

    ############
    # Third run.
    runner.allocator.allocate.return_value = \
        {
            'task-id-/t1': {
                AllocationType.QUOTA: 1000,
                AllocationType.RDT: RDTAllocation(name='only_group', l3='L3:0=00fff;1=0ffff')
            },
            'task-id-/t2': {
                AllocationType.QUOTA: 1000,
                AllocationType.RDT: RDTAllocation(name='only_group', l3='L3:0=00fff;1=0ffff')
            }
        }, [], []
    with patch('owca.platforms.collect_platform_information', return_value=(
            platform_mock, [metric('platform-cpu-usage')], {})):
        runner.run()

    # Checking state after run.
    assert (len(runner.containers_manager.resgroups_containers_relation['only_group'][1]) == 2)
    assert (len(runner.containers_manager.resgroups_containers_relation[''][1]) == 0)
    assert (len(runner.containers_manager.containers) == 2)


@pytest.mark.skip('TODO')
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
def test_unique_rdt_allocations(tasks_allocations, expected_resgroup_reallocation_count):
    """Checks if allocation of resctrl group is performed only once if more than one
       task_allocations has RDTAllocation with the same name. In other words,
       check if unnecessary reallocation of resctrl group does not take place.

       The goal is achieved by checking how many times
       Container.write_schemata is called with allocate_rdt=True."""
    raise NotImplementedError


@pytest.mark.skip('TODO')
@pytest.mark.parametrize('tasks_allocations,expected_metrics', (
    ({}, []),
    ({'some_task': {AllocationType.SHARES: 0.5}}, [
        Metric(name='allocation', value=0.5,
               type=MetricType.GAUGE,
               labels={'allocation_type': 'cpu_shares', 'task_id': 'some_task'})
    ]),
    ({'some_task': {AllocationType.RDT: RDTAllocation(mb='mb:0=20')}}, [
        allocation_metric('rdt_mb', 20, group_name='', domain_id='0', task_id='some_task')
    ]),
    ({'some_task': {AllocationType.SHARES: 0.5,
                    AllocationType.RDT: RDTAllocation(mb='mb:0=20')}}, [
        Metric(
            name='allocation', value=0.5,
            type=MetricType.GAUGE,
            labels={'allocation_type': AllocationType.SHARES, 'task_id': 'some_task'}
        ),
        allocation_metric('rdt_mb', 20, group_name='', domain_id='0', task_id='some_task')
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
         allocation_metric('rdt_mb', 30, group_name='', domain_id='0', task_id='some_task_a'),
         Metric(
             name='allocation', value=0.6,
             type=MetricType.GAUGE,
             labels={'allocation_type': AllocationType.QUOTA, 'task_id': 'some_task_b'}
         ),
         allocation_metric('rdt_l3_cache_ways', 4, group_name='b',
                           domain_id='0', task_id='some_task_b'),
         allocation_metric('rdt_l3_mask', 15, group_name='b',
                           domain_id='0', task_id='some_task_b'),
         allocation_metric('rdt_l3_cache_ways', 5, group_name='b',
                           domain_id='1', task_id='some_task_b'),
         allocation_metric('rdt_l3_mask', 241, group_name='b',
                           domain_id='1', task_id='some_task_b'),
     ]),
))
def test_convert_task_allocations_to_metrics(tasks_allocations, expected_metrics):
    platform = platforms.collect_platform_information(False)
    allocation_configuration = AllocationConfiguration()
    containers = {}
    allocations = convert_to_allocations_values(tasks_allocations, containers,
                                                platform, allocation_configuration)
    metrics_got = allocations.generate_metrics()
    assert metrics_got == expected_metrics
