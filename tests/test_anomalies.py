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
from typing import List, Dict

import pytest

from owca.detectors import convert_anomalies_to_metrics, _create_uuid_from_tasks_ids, \
    ContendedResource
from owca.metrics import Metric, MetricType
from owca.nodes import TaskId
from owca.testing import anomaly


def anomaly_metrics(contended_task_id: TaskId, contending_task_ids: List[TaskId],
                    contending_workload_instances: Dict[TaskId, str] = None,
                    labels: Dict[TaskId, Dict[str, str]] = None):
    """Helper method to create metric based on anomaly.
    uuid is used if provided.
    """
    contending_workload_instances = contending_workload_instances or dict()
    labels = labels or dict()
    metrics = []
    for task_id in contending_task_ids:
        uuid = _create_uuid_from_tasks_ids(contending_task_ids + [contended_task_id])
        metric = Metric(
            name='anomaly', value=1,
            labels=dict(
                contended_task_id=contended_task_id, contending_task_id=task_id,
                resource=ContendedResource.MEMORY_BW, uuid=uuid,
                type='contention',
                contending_workload_instance=contending_workload_instances[task_id],
                workload_instance=contending_workload_instances[contended_task_id]),
            type=MetricType.COUNTER
        )
        if contended_task_id in labels:
            metric.labels.update(labels[contended_task_id])
        metrics.append(metric)
    return metrics


@pytest.mark.parametrize('anomalies,tasks_labels,expected_metrics', (
        ([], {}, []),
        (
                [anomaly('t1', ['t2'])],
                {'t1': {'workload_instance': 't1_workload_instance'},
                 't2': {'workload_instance': 't2_workload_instance'}},
                anomaly_metrics('t1', ['t2'],
                                {'t1': 't1_workload_instance', 't2': 't2_workload_instance'})),
        (
                [anomaly('t2', ['t1', 't3'])],
                {'t1': {'workload_instance': 't1_workload_instance'},
                 't2': {'workload_instance': 't2_workload_instance'},
                 't3': {'workload_instance': 't3_workload_instance'}},
                anomaly_metrics('t2', ['t1', 't3'],
                                {'t1': 't1_workload_instance', 't2': 't2_workload_instance',
                                 't3': 't3_workload_instance'})
        ),
))
def test_convert_anomalies_to_metrics(anomalies, tasks_labels, expected_metrics):
    metrics_got = convert_anomalies_to_metrics(anomalies, tasks_labels)
    assert metrics_got == expected_metrics
