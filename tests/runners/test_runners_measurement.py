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

from unittest.mock import Mock

from owca import storage
from owca.mesos import MesosNode
from owca.runners.measurement import MeasurementRunner
from owca.testing import assert_metric, redis_task_with_default_labels, measurements_runner_patches


@measurements_runner_patches
def test_measurements_runner():
    # Node mock
    t1 = redis_task_with_default_labels('t1')
    t2 = redis_task_with_default_labels('t2')

    runner = MeasurementRunner(
        node=Mock(spec=MesosNode,
                  get_tasks=Mock(return_value=[t1, t2])),
        metrics_storage=Mock(spec=storage.Storage, store=Mock()),
        rdt_enabled=False,
        extra_labels=dict(extra_label='extra_value')  # extra label with some extra value
    )

    # Mock to finish after one iteration.
    runner._wait_or_finish = Mock(return_value=False)
    runner.run()

    # Check output metrics.
    got_metrics = runner._metrics_storage.store.call_args[0][0]

    # Internal owca metrics are generated (owca is running, number of task under control,
    # memory usage and profiling information)
    assert_metric(got_metrics, 'owca_up', dict(extra_label='extra_value'))
    assert_metric(got_metrics, 'owca_tasks', expected_metric_value=2)
    # owca & its children memory usage (in bytes)
    assert_metric(got_metrics, 'owca_memory_usage_bytes', expected_metric_value=100*2*1024)
    assert_metric(got_metrics, 'owca_duration_seconds', dict(function='profiled_function'),
                  expected_metric_value=1)

    # Measurements metrics about tasks, based on get_measurements mocks.
    assert_metric(got_metrics, 'cpu_usage', dict(task_id=t1.task_id), expected_metric_value=23)
    assert_metric(got_metrics, 'cpu_usage', dict(task_id=t2.task_id), expected_metric_value=23)
