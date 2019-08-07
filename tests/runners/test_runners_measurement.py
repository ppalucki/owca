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

from unittest.mock import Mock, patch

import pytest

from wca import storage
from wca.containers import Container
from wca.metrics import MissingMeasurementException
from wca.mesos import MesosNode
from wca.platforms import RDTInformation
from wca.resctrl import ResGroup
from wca.runners.measurement import MeasurementRunner, _build_tasks_metrics, _prepare_tasks_data, \
    TaskLabelRegexGenerator
from tests.testing import assert_metric, redis_task_with_default_labels, prepare_runner_patches, \
    TASK_CPU_USAGE, WCA_MEMORY_USAGE, metric, DEFAULT_METRIC_VALUE, task


@prepare_runner_patches
@pytest.mark.parametrize('subcgroups', ([], ['/T/c1'], ['/T/c1', '/T/c2']))
def test_measurements_runner(subcgroups):
    # Node mock
    t1 = redis_task_with_default_labels('t1', subcgroups)
    t2 = redis_task_with_default_labels('t2', subcgroups)

    runner = MeasurementRunner(
        node=Mock(spec=MesosNode,
                  get_tasks=Mock(return_value=[t1, t2])),
        metrics_storage=Mock(spec=storage.Storage, store=Mock()),
        rdt_enabled=False,
        extra_labels=dict(extra_label='extra_value')  # extra label with some extra value
    )
    runner._wait = Mock()
    # Mock to finish after one iteration.
    runner._initialize()
    runner._iterate()

    # Check output metrics.
    got_metrics = runner._metrics_storage.store.call_args[0][0]

    # Internal wca metrics are generated (wca is running, number of task under control,
    # memory usage and profiling information)
    assert_metric(got_metrics, 'wca_up', dict(extra_label='extra_value'))
    assert_metric(got_metrics, 'wca_tasks', expected_metric_value=2)
    # wca & its children memory usage (in bytes)
    assert_metric(got_metrics, 'wca_memory_usage_bytes',
                  expected_metric_value=WCA_MEMORY_USAGE * 2 * 1024)

    # Measurements metrics about tasks, based on get_measurements mocks.
    cpu_usage = TASK_CPU_USAGE * (len(subcgroups) if subcgroups else 1)
    assert_metric(got_metrics, 'cpu_usage', dict(task_id=t1.task_id),
                  expected_metric_value=cpu_usage)
    assert_metric(got_metrics, 'cpu_usage', dict(task_id=t2.task_id),
                  expected_metric_value=cpu_usage)

    # Test for labels generator.
    cpu_metric = [metric for metric in got_metrics if metric.name == 'cpu_usage'][0]
    assert 'task_name' in t1.labels
    assert cpu_metric.labels['application'] == 'example/root/staging/redis-6792'
    assert cpu_metric.labels['application_version_name'] == ''


@prepare_runner_patches
@patch('wca.runners.measurement.time.sleep')
def test_measurements_wait(sleep_mock):
    with patch('time.time', return_value=1):
        runner = MeasurementRunner(
            node=Mock(spec=MesosNode,
                      get_tasks=Mock(return_value=[])),
            metrics_storage=Mock(spec=storage.Storage, store=Mock()),
            rdt_enabled=False,
            extra_labels={}
        )

        runner._initialize()
        runner._iterate()
        sleep_mock.assert_called_once_with(1.0)

    with patch('time.time', return_value=1.3):
        runner._iterate()
        sleep_mock.assert_called_with(0.7)
        assert runner._last_iteration == 1.3

    with patch('time.time', return_value=2.5):
        runner._iterate()
        sleep_mock.assert_called_with(0)


@pytest.mark.parametrize('tasks_labels, tasks_measurements, expected_metrics', [
    ({}, {}, []),
    ({'t1_task_id': {'app': 'redis'}}, {}, []),
    ({'t1_task_id': {'app': 'redis'}}, {'t1_task_id': {'cpu_usage': DEFAULT_METRIC_VALUE}},
     [metric('cpu_usage', {'app': 'redis'})]),
])
def test_build_tasks_metrics(tasks_labels, tasks_measurements, expected_metrics):
    assert expected_metrics == _build_tasks_metrics(tasks_labels, tasks_measurements)


@patch('wca.cgroups.Cgroup')
@patch('wca.perf.PerfCounters')
@patch('wca.containers.Container.get_measurements', Mock(return_value={'cpu_usage': 13}))
def test_prepare_tasks_data(*mocks):
    rdt_information = RDTInformation(True, True, True, True, '0', '0', 0, 0, 0)
    containers = {
        task('/t1', labels={'label_key': 'label_value'}, resources={'cpu': 3}):
            Container('/t1', 1, 1, rdt_information)
    }

    tasks_measurements, tasks_resources, tasks_labels = _prepare_tasks_data(containers)

    assert tasks_measurements == {'t1_task_id': {'cpu_usage': 13}}
    assert tasks_resources == {'t1_task_id': {'cpu': 3}}
    assert tasks_labels == {'t1_task_id': {'initial_task_cpu_assignment': 'unknown',
                                           'label_key': 'label_value',
                                           'task_id': 't1_task_id'}}


@patch('wca.cgroups.Cgroup')
@patch('wca.resctrl.ResGroup.get_measurements', side_effect=MissingMeasurementException())
@patch('wca.perf.PerfCounters')
def test_prepare_task_data_resgroup_not_found(*mocks):
    rdt_information = RDTInformation(True, True, True, True, '0', '0', 0, 0, 0)
    containers = {
        task('/t1', labels={'label_key': 'label_value'}, resources={'cpu': 3}):
            Container('/t1', 1, 1, rdt_information, resgroup=ResGroup('/t1'))
    }
    tasks_measurements, tasks_resources, tasks_labels = \
        _prepare_tasks_data(containers)
    assert tasks_measurements == {}


@patch('wca.cgroups.Cgroup.get_measurements', side_effect=MissingMeasurementException())
@patch('wca.perf.PerfCounters')
def test_prepare_task_data_cgroup_not_found(*mocks):
    rdt_information = RDTInformation(True, True, True, True, '0', '0', 0, 0, 0)
    containers = {
        task('/t1', labels={'label_key': 'label_value'}, resources={'cpu': 3}):
            Container('/t1', 1, 1, rdt_information)
    }
    tasks_measurements, tasks_resources, tasks_labels = \
        _prepare_tasks_data(containers)
    assert tasks_measurements == {}


@pytest.mark.parametrize('source_val, pattern, repl, expected_val', (
    ('__val__', '__(.*)__', r'\1', 'val'),
    ('example/devel/staging-13/redis.small', r'.*/.*/.*/(.*)\..*', r'\1', 'redis'),
))
def test_task_label_regex_generator(source_val, pattern, repl, expected_val):
    tasks = [task('/t1', labels={'source_key': source_val})]
    task_label_regex_generator = TaskLabelRegexGenerator(pattern, repl, 'source_key')
    task_label_regex_generator.generate(tasks, 'target_key')
    assert tasks[0].labels['target_key'] == expected_val


@patch('wca.runners.measurement.log')
def test_task_label_regex_generator_error(log_mock):
    tasks = [task('/t1', labels={'source_key': 'source_val'})]
    task_label_regex_generator = TaskLabelRegexGenerator('__(.*)__', '\\1', 'non_existing_key')
    task_label_regex_generator.generate(tasks, 'target_key')
    log_mock.warning.assert_called_once()


def test_task_label_regex_generator_overwriting_label():
    tasks = [task('/t1', labels={'source_key': '__val__'})]
    task_label_regex_generator = TaskLabelRegexGenerator('__(.*)__', '\\1', 'source_key')
    task_label_regex_generator.generate(tasks, 'source_key')
    assert tasks[0].labels['source_key'] == '__val__'
