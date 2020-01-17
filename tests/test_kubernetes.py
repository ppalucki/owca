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
import requests

from tests.testing import create_json_fixture_mock
from wca.config import ValidationError
from wca.kubernetes import KubernetesNode, KubernetesTask, \
    _build_cgroup_path, are_all_tasks_of_single_qos, QOS_LABELNAME, \
    MissingCgroupException
from wca.nodes import TaskSynchronizationException


def ktask(name, qos):
    """Creates kubernetes task."""
    return KubernetesTask(
        name=name,
        task_id='task_id-' + name,
        qos=qos,
        labels={'exampleKey': 'value', QOS_LABELNAME: qos},
        resources={'requests_cpu': 0.25,
                   'requests_memory': float(64 * 1024 ** 2),
                   'cpus': 0.25,
                   'mem': float(64 * 1024 ** 2)},
        cgroup_path='/kubepods/{}/pod{}'.format(qos, name),
        subcgroups_paths=['/kubepods/{}/pod{}/t1'.format(qos, name),
                          '/kubepods/{}/pod{}/t2'.format(qos, name)])


@patch('requests.get', return_value=create_json_fixture_mock('kubernetes_get_state', __file__))
@patch('os.path.exists', return_value=True)
def test_get_tasks(mock_path_exists, get_mock):
    expected_tasks = [KubernetesTask(
        name='default/test',
        task_id='4d6a81df-3448-11e9-8e1d-246e96663c22',
        qos='burstable',
        labels={'exampleKey': 'value',
                QOS_LABELNAME: 'burstable'},
        resources={'requests_cpu': 0.25,
                   'requests_memory': float(64 * 1024 ** 2),
                   'cpus': 0.25,
                   'mem': float(64 * 1024 ** 2)},
        cgroup_path='/kubepods/burstable/pod4d6a81df'
                    '-3448-11e9-8e1d-246e96663c22',
        subcgroups_paths=['/kubepods/burstable/pod4d'
                          '6a81df-3448-11e9-8e1d-246'
                          'e96663c22/eb9c378219b6a4e'
                          'fc034ea8898b19faa0e27c7b2'
                          '0b8eb254fda361cceacf8e90']),
        KubernetesTask(
            name='default/test2',
            task_id='567975a0-3448-11e9-8e1d-246e96663c22',
            qos='besteffort',
            labels={QOS_LABELNAME: 'besteffort'},
            resources={},
            cgroup_path='/kubepods/besteffort/pod567975a0-3448-'
                        '11e9-8e1d-246e96663c22',
            subcgroups_paths=['/kubepods/besteffort/pod5'
                              '67975a0-3448-11e9-8e1d-24'
                              '6e96663c22/e90bbbb3b060ba'
                              'a1d354cd9b26f353d66fbb08d'
                              '785abd32f4f6ec52ac843a2e7'])]

    node = KubernetesNode(kubelet_enabled=True)
    tasks = node.get_tasks()

    assert len(tasks) == 2
    for i, task in enumerate(tasks):
        assert task == expected_tasks[i]


@patch('requests.get', return_value=create_json_fixture_mock('kubeapi_res', __file__))
@patch('pathlib.Path.open')
@patch('os.path.exists', return_value=True)
def test_get_tasks_kubeapi(mock_path_exists, get_mock, pathlib_open_mock):
    node = KubernetesNode(node_ip="100.64.176.37")
    tasks = node.get_tasks()
    assert len(tasks) == 11


@patch('requests.get', return_value=create_json_fixture_mock(
    'kubeapi_invalid_res_missing_host_ip', __file__))
@patch('pathlib.Path.open')
@patch('os.path.exists', return_value=True)
def test_get_tasks_kubeapi_invalid_res_missing_host_ip(
        mock_path_exists, get_mock, pathlib_open_mock):
    node = KubernetesNode(node_ip="100.64.176.37")
    tasks = node.get_tasks()
    assert len(tasks) == 0


@patch(
    'requests.get',
    return_value=create_json_fixture_mock('kubernetes_get_state_not_ready', __file__))
def test_get_tasks_not_all_ready(get_mock):
    node = KubernetesNode(kubelet_enabled=True)
    tasks = node.get_tasks()
    assert len(tasks) == 0


@patch(
    'requests.get',
    return_value=create_json_fixture_mock('kubelet_invalid_pods_response', __file__))
@patch('wca.kubernetes._build_cgroup_path', return_value="/mock_path")
def test_invalid_kubelet_response(mock_path_exists, get_mock):
    node = KubernetesNode(kubelet_enabled=True)
    with pytest.raises(ValidationError):
        node.get_tasks()


_POD_ID = '12345-67890'
_STATIC_POD_ID = '09876-54321'
_CUTTED_STATIC_POD_ID = '0987654321'
_CONTAINER_ID = '123456'


def pod_cgroup_exists(pod_path):
    if _POD_ID in pod_path or _CUTTED_STATIC_POD_ID in pod_path:
        return True
    return False


@pytest.mark.parametrize('qos, expected_cgroup_path', (
        ('burstable', '/kubepods.slice/kubepods-burstable.slice/'
                      'kubepods-burstable-pod12345_67890.slice'),
        ('guaranteed', '/kubepods.slice/kubepods-guaranteed.slice/'
                       'kubepods-guaranteed-pod12345_67890.slice'),
        ('besteffort', '/kubepods.slice/kubepods-besteffort.slice/'
                       'kubepods-besteffort-pod12345_67890.slice'),
)
                         )
def test_find_cgroup_path_for_pod_systemd(qos, expected_cgroup_path):
    assert expected_cgroup_path == _build_cgroup_path(cgroup_driver='systemd',
                                                      qos=qos, pod_id=_POD_ID)


@pytest.mark.parametrize('qos, expected_cgroup_path', (
        ('burstable', '/kubepods.slice/kubepods-burstable.slice/'
                      'kubepods-burstable-pod12345_67890.slice/'
                      'docker-123456.scope'),
        ('guaranteed', '/kubepods.slice/kubepods-guaranteed.slice/'
                       'kubepods-guaranteed-pod12345_67890.slice/'
                       'docker-123456.scope'),
        ('besteffort', '/kubepods.slice/kubepods-besteffort.slice/'
                       'kubepods-besteffort-pod12345_67890.slice/'
                       'docker-123456.scope'),
)
                         )
def test_find_cgroup_path_for_pod_systemd_with_container_id(qos, expected_cgroup_path):
    assert expected_cgroup_path == _build_cgroup_path(cgroup_driver='systemd',
                                                      qos=qos, pod_id=_POD_ID,
                                                      container_id=_CONTAINER_ID)


@pytest.mark.parametrize('qos, expected_cgroup_path', (
        ('burstable', '/kubepods/burstable/pod12345-67890'),
        # Here we have exception, guaranteed pods are kept directly in kubepods cgroup.
        ('guaranteed', '/kubepods/pod12345-67890'),
        ('besteffort', '/kubepods/besteffort/pod12345-67890'),
)
                         )
@patch('os.path.exists', side_effect=pod_cgroup_exists)
def test_build_cgroup_path_pod_cgroupfs(mock_path_exists, qos, expected_cgroup_path):
    assert expected_cgroup_path == _build_cgroup_path(cgroup_driver='cgroupfs',
                                                      qos=qos, pod_id=_POD_ID)


@pytest.mark.parametrize('qos, expected_cgroup_path', (
        ('burstable', '/kubepods/burstable/pod0987654321'),
        # Here we have exception, guaranteed pods are kept directly in kubepods cgroup.
        ('guaranteed', '/kubepods/pod0987654321'),
        ('besteffort', '/kubepods/besteffort/pod0987654321'),
)
                         )
@patch('os.path.exists', side_effect=pod_cgroup_exists)
def test_build_cgroup_path_static_pod_cgroupfs(mock_path_exists, qos, expected_cgroup_path):
    assert expected_cgroup_path == _build_cgroup_path(cgroup_driver='cgroupfs',
                                                      qos=qos, pod_id=_STATIC_POD_ID)


@patch('os.path.exists', return_value=False)
def test_raise_missing_cgroup_exception_build_cgroup_path_pod_cgroupfs(mock_path_exists):
    with pytest.raises(MissingCgroupException):
        _build_cgroup_path(cgroup_driver='cgroupfs',
                           qos='burstable', pod_id=_STATIC_POD_ID)


@pytest.mark.parametrize('tasks, expected_result', (
        ([ktask(name="a", qos="guaranteed"), ktask(name="b", qos="besteffort")], False),
        ([ktask(name="a", qos="besteffort"), ktask(name="b", qos="besteffort")], True),
))
def test_are_all_tasks_of_single_qos(tasks, expected_result):
    assert are_all_tasks_of_single_qos(tasks) == expected_result


@patch('requests.get', side_effect=requests.exceptions.ConnectionError())
def test_get_tasks_synchronization_error(request):
    node = KubernetesNode(kubelet_enabled=True)
    with pytest.raises(TaskSynchronizationException):
        node.get_tasks()
