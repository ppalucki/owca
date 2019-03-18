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


"""Module for independent simple helper functions."""

import os
from typing import List, Dict, Union, Optional
from unittest.mock import mock_open, Mock

from owca.detectors import ContendedResource, ContentionAnomaly, _create_uuid_from_tasks_ids
from owca.nodes import TaskId, Task
from owca.metrics import Metric, MetricType


def relative_module_path(module_file, relative_path):
    """Returns path relative to current python module."""
    dir_path = os.path.dirname(os.path.realpath(module_file))
    return os.path.join(dir_path, relative_path)


def create_open_mock(paths: Dict[str, Mock]):
    """Creates open_mocks registry based on multiple path.

    You can access created open_mocks by using __getitem__ functions like this:
    OpenMock({'path':'body')['path']. Useful for write mocks assertions.

    For typical example of usage, check tests/test_testing:test_create_open_mock()

    """

    class OpenMock:
        def __init__(self, paths: Dict[str, Union[str, Mock]]):
            self.paths = paths
            self._mocks = {}

        def __call__(self, path, mode='rb'):
            """Used instead of open function."""
            if path not in self.paths:
                raise Exception('opening %r is not mocked with OpenMock!' % path)
            mock_or_str = self.paths[path]
            if isinstance(mock_or_str, str) or isinstance(mock_or_str, bytes):
                mock = mock_open(read_data=mock_or_str)
                self._mocks[path] = mock
            else:
                mock = self.paths[path]
            return mock(path, mode)

        def __getitem__(self, path):
            if path not in self._mocks:
                raise Exception('mock %r was not open!' % path)

            return self._mocks[path]

    return OpenMock(paths)


def anomaly_metrics(contended_task_id: TaskId, contending_task_ids: List[TaskId],
                    contending_workload_instances: Dict[TaskId, str] = {},
                    labels: Dict[TaskId, Dict[str, str]] = {}):
    """Helper method to create metric based on anomaly.
    uuid is used if provided.
    """
    metrics = []
    for task_id in contending_task_ids:
        uuid = _create_uuid_from_tasks_ids(contending_task_ids + [contended_task_id])
        metric = Metric(name='anomaly', value=1,
                        labels=dict(contended_task_id=contended_task_id, contending_task_id=task_id,
                                    resource=ContendedResource.MEMORY_BW, uuid=uuid,
                                    type='contention',
                                    contending_workload_instance=contending_workload_instances[
                                        task_id], workload_instance=contending_workload_instances[
                                            contended_task_id]), type=MetricType.COUNTER)
        if contended_task_id in labels:
            metric.labels.update(labels[contended_task_id])
        metrics.append(metric)
    return metrics


def anomaly(contended_task_id: TaskId, contending_task_ids: List[TaskId],
            metrics: List[Metric] = None):
    """Helper method to create simple anomaly for single task.
    It is always about memory contention."""
    return ContentionAnomaly(
        contended_task_id=contended_task_id,
        contending_task_ids=contending_task_ids,
        resource=ContendedResource.MEMORY_BW,
        metrics=metrics or [],
    )


def task(cgroup_path, labels=None, resources=None):
    """Helper method to create task with default values."""
    return Task(
        cgroup_path=cgroup_path,
        name='name-' + cgroup_path,
        task_id='task-id-' + cgroup_path,
        labels=labels or dict(),
        resources=resources or dict()
    )


def assert_subdict(got_dict: dict, expected_subdict: dict):
    """Assert that one dict is a subset of another dict in recursive manner.
    Check if expected key exists and if value matches expected value.
    """
    for expected_key, expected_value in expected_subdict.items():
        if expected_key not in got_dict:
            raise AssertionError('key %r not found in %r' % (expected_key, got_dict))
        got_value = got_dict[expected_key]
        if isinstance(expected_value, dict):
            # When comparing with dict use 'containment' operation instead of equal.
            # If expected value is a dict, call assert_subdict recursively.
            if not isinstance(got_value, dict):
                raise AssertionError('expected dict type at %r key, got %r' % (
                    expected_key, type(got_value)))
            assert_subdict(got_value, expected_value)
        else:
            # For any other type check using ordinary equality operator.
            assert got_value == expected_value, \
                'value differs got=%r expected=%r at key=%r' % (
                    got_value, expected_value, expected_key)


def _is_dict_match(got_dict: dict, expected_subdict: dict):
    """Match values and keys from dict (non recursive)."""
    for expected_key, expected_value in expected_subdict.items():
        if expected_key not in got_dict:
            return False
        if got_dict[expected_key] != expected_value:
            return False
    return True


def assert_metric(got_metrics: List[Metric],
                  expected_metric_name: str,
                  expected_metric_some_labels: Optional[Dict] = None,
                  expected_metric_value: Optional[Union[float, int]] = None,
                  ):
    """Assert that given metrics exists in given set of metrics."""
    found_metric = None
    for got_metric in got_metrics:
        if got_metric.name == expected_metric_name:
            # found by name, should we check labels ?
            if expected_metric_some_labels is not None:
                # yes check by labels
                if _is_dict_match(got_metric.labels, expected_metric_some_labels):
                    found_metric = got_metric
                    break
            else:
                found_metric = got_metric
                break
    if not found_metric:
        raise AssertionError('metric %r not found' % expected_metric_name)
    # Check values as well
    if expected_metric_value is not None:
        assert found_metric.value == expected_metric_value, \
            'metric name=%r value differs got=%r expected=%r' % (
                found_metric.name, found_metric.value, expected_metric_value)
