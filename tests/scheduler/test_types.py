# Copyright (c) 2020 Intel Corporation
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
import pytest

from wca.scheduler.types import ExtenderArgs, ExtenderFilterResult, HostPriority, UnsupportedCase
from wca.config import ValidationError

from tests.testing import create_json_fixture_mock


@pytest.mark.parametrize(
    'host, score', (
            (0, 1),
            (0, 1.1),
            (0, 'node1'),
            ('node1', 1.1),
            ('node1', '1'),
            ('node1', '1.1'),
    )
)
def test_improper_host_priority(host, score):
    with pytest.raises(ValidationError):
        HostPriority(host, score)


POD = create_json_fixture_mock('kubeapi_single_pod').json()
NODE_NAMES = ['node1', 'node2']


@pytest.mark.parametrize(
    'nodes, pod, node_names', (
            ([{}, {}], POD, NODE_NAMES),
            ([{}], POD, NODE_NAMES),
    )
)
def test_extender_args_unsupported_case_with_nodes(nodes, pod, node_names):
    with pytest.raises(UnsupportedCase):
        ExtenderArgs(nodes, pod, node_names)


@pytest.mark.parametrize(
    'nodes, pod, node_names', (
            (None, POD, NODE_NAMES),
    )
)
def test_extender_args_correct_data(nodes, pod, node_names):
    ExtenderArgs(nodes, pod, node_names)


@pytest.mark.parametrize(
    'nodes, pod, node_names', (
            (None, 'pod', NODE_NAMES),
            (None, POD, 1234),
            (None, None, None),
    )
)
def test_extender_args_improper_data(nodes, pod, node_names):
    with pytest.raises(ValidationError):
        ExtenderArgs(nodes, pod, node_names)


FAILED_NODES = {'node3': 'Unsufficient memory bandwidth!',
                'node4': 'Power off!'}
ERROR = 'TEST ERROR'


@pytest.mark.parametrize(
    'nodes, node_names, failed_nodes, error', (
            ([{}, {}], NODE_NAMES, FAILED_NODES, ERROR),
            ([{}], NODE_NAMES, FAILED_NODES, ERROR),
    )
)
def test_extender_filter_result_unsupported_case_with_nodes(nodes, node_names, failed_nodes, error):
    with pytest.raises(UnsupportedCase):
        ExtenderFilterResult(nodes, node_names, failed_nodes, error)


@pytest.mark.parametrize(
    'nodes, node_names, failed_nodes, error', (
            (None, NODE_NAMES, FAILED_NODES, ERROR),
    )
)
def test_extender_filter_result_correct_data(nodes, node_names, failed_nodes, error):
    ExtenderFilterResult(nodes, node_names, failed_nodes, error)


@pytest.mark.parametrize(
    'nodes, node_names, failed_nodes, error', (
            (None, NODE_NAMES, FAILED_NODES, 123),
            (None, 123, FAILED_NODES, ERROR),
            (None, NODE_NAMES, 123, ERROR),
    )
)
def test_extender_filter_result_improper_data(nodes, node_names, failed_nodes, error):
    with pytest.raises(ValidationError):
        ExtenderFilterResult(nodes, node_names, failed_nodes, error)
