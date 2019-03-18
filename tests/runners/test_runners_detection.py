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

from owca import storage
from owca.detectors import AnomalyDetector
from owca.mesos import MesosNode
from owca.runners.detection import DetectionRunner
from owca.testing import metric, anomaly, \
    assert_metric, assert_subdict, redis_task_with_default_labels, measurements_runner_patches

from pprint import pprint

@measurements_runner_patches
@patch('owca.detectors._create_uuid_from_tasks_ids', return_value='fake-uuid')
@patch('owca.testing._create_uuid_from_tasks_ids', return_value='fake-uuid')
def test_detection_runner(*mocks):

    # Node mock
    t1 = redis_task_with_default_labels('t1')
    t2 = redis_task_with_default_labels('t2')

    # Detector mock - simulate returning one anomaly and additional metric
    detector_mock = Mock(
        spec=AnomalyDetector,
        detect=Mock(
            return_value=(
                [anomaly(
                    t1.task_id, [t2.task_id], metrics=[
                        metric('contention_related_metric')
                    ]
                )],  # one anomaly + related metric
                [metric('bar')]  # one extra metric
            )
        )
    )

    runner = DetectionRunner(
        node=Mock(spec=MesosNode, get_tasks=Mock(return_value=[t1, t2])),
        metrics_storage=Mock(spec=storage.Storage, store=Mock()),
        anomalies_storage=Mock(spec=storage.Storage, store=Mock()),
        detector=detector_mock,
        rdt_enabled=False,
        extra_labels=dict(extra_label='extra_value')  # extra label with some extra value
    )

    # Mock to finish after one iteration.
    runner._wait_or_finish = Mock(return_value=False)
    runner.run()


    got_metrics = runner._metrics_storage.store.call_args[0][0]
    print()
    print('------- metrics: ')
    pprint(got_metrics)
    assert_metric(got_metrics, 'owca_up', dict(extra_label='extra_value'))
    assert_metric(got_metrics, 'owca_tasks', expected_metric_value=2)
    assert_metric(got_metrics, 'cpu_usage', dict(application='redis', task_id='t1_task_id'), expected_metric_value=23)
    assert_metric(got_metrics, 'cpu_usage', dict(application='redis', task_id='t2_task_id'), expected_metric_value=23)

    got_anomalies_metrics = runner._anomalies_storage.store.mock_calls[0][1][0]
    print('-------- anomalies:')
    pprint(got_anomalies_metrics)

    # Check that detector was called with proper arguments.
    platform, tasks_measurements, tasks_resources, tasks_labels = detector_mock.detect.mock_calls[0][1]
    print('--------- detect:')
    pprint(tasks_measurements)
    pprint(tasks_labels)
    assert_subdict(tasks_measurements, dict(t1_task_id=dict(cpu_usage=23)))

