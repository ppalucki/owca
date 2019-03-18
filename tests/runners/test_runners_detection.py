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
from unittest.mock import Mock, MagicMock
from unittest.mock import patch

import pytest

from owca import storage
from owca.detectors import AnomalyDetector
from owca.mesos import sanitize_mesos_label, MesosNode
from owca.metrics import Metric, MetricType
from owca.runners.detection import DetectionRunner
from owca.testing import metric, task, anomaly, anomaly_metrics, container, platform_mock, \
    assert_metric, assert_subdict

from pprint import pprint

def _prepare_task_and_labels(task_id):
    """Returns task instance and its labels."""
    task_labels = {
        'org.apache.aurora.metadata.application': 'redis',
        'org.apache.aurora.metadata.load_generator': 'rpc-perf-%s' % task_id,
        'org.apache.aurora.metadata.name': 'redis--6792-%s' % task_id,
    }
    task_labels_sanitized = {
        sanitize_mesos_label(label_key): label_value
        for label_key, label_value
        in task_labels.items()
    }
    task_labels_sanitized_with_task_id = {'task_id': '%s_task_id'  % task_id}
    task_labels_sanitized_with_task_id.update(task_labels_sanitized)
    return task('/%s' % task_id, resources=dict(cpus=8.), labels=task_labels), task_labels


@patch('resource.getrusage', return_value=Mock(ru_maxrss=1234))
@patch('owca.platforms.collect_platform_information', return_value=(
        platform_mock, [metric('platform-cpu-usage')], {}))
@patch('owca.testing._create_uuid_from_tasks_ids', return_value='fake-uuid')
@patch('owca.detectors._create_uuid_from_tasks_ids', return_value='fake-uuid')
@patch('owca.runners.measurement.are_privileges_sufficient', return_value=True)
@patch('owca.containers.ResGroup')
@patch('owca.containers.PerfCounters')
@patch('owca.platforms.collect_topology_information', return_value=(1, 1, 1))
@patch('owca.containers.Cgroup.get_measurements', return_value=dict(cpu_usage=23))
@patch('time.time', return_value=1234567890.123)
@patch('owca.profiling._durations', new=MagicMock(items=Mock(return_value=[('foo', 0.)])))
def test_detection_runner_containers_state(*mocks):
    """Tests proper interaction between runner instance and functions for
    creating anomalies and calculating the desired state.

    Also tests labelling of metrics during iteration loop.
    """

    # Node mock
    t1, t1_labels = _prepare_task_and_labels('t1')
    t2, t2_labels = _prepare_task_and_labels('t2')

    node_mock = Mock(spec=MesosNode, get_tasks=Mock(return_value=[t1, t2]))

    # Storage mocks
    metrics_storage = Mock(spec=storage.Storage, store=Mock())
    anomalies_storage = Mock(spec=storage.Storage, store=Mock())

    # Detector mock - simulate returning one anomaly and additional metric
    detector_mock = Mock(
        spec=AnomalyDetector,
        detect=Mock(
            return_value=(
                [anomaly(
                    't1_task_id', ['t2_task_id'], metrics=[
                        metric('contention_related_metric')
                    ]
                )],  # one anomaly + related metric
                [metric('bar')]  # one extra metric
            )
        )
    )

    extra_labels = dict(extra_label='extra_value')  # extra label with some extra value

    runner = DetectionRunner(
        node=node_mock,
        metrics_storage=metrics_storage,
        anomalies_storage=anomalies_storage,
        detector=detector_mock,
        rdt_enabled=False,
        extra_labels=extra_labels,
    )

    # Mock to finish after one iteration.
    runner._wait_or_finish = Mock(return_value=False)
    runner.run()


    got_metrics = metrics_storage.store.call_args[0][0]
    print()
    print('------- metrics: ')
    pprint(got_metrics)
    assert_metric(got_metrics, 'owca_up', dict(extra_label='extra_value'))
    assert_metric(got_metrics, 'owca_tasks', expected_metric_value=2)
    assert_metric(got_metrics, 'cpu_usage', dict(application='redis', task_id='t1_task_id'), expected_metric_value=23)
    assert_metric(got_metrics, 'cpu_usage', dict(application='redis', task_id='t2_task_id'), expected_metric_value=23)

    got_anomalies_metrics = anomalies_storage.store.mock_calls[0][1][0]
    print('-------- anomalies:')
    pprint(got_anomalies_metrics)

    # Check that detector was called with proper arguments.
    platform, tasks_measurements, tasks_resources, tasks_labels = detector_mock.detect.mock_calls[0][1]
    print('--------- detect:')
    pprint(tasks_measurements)
    pprint(tasks_labels)
    assert_subdict(tasks_measurements, dict(t1_task_id=dict(cpu_usage=23)))

