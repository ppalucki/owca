# Copyright (c) 2019 Intel Corporation
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

from owca.extra.static_node import StaticNode
from owca.nodes import Task


@patch('os.path.exists', Mock(return_value=True))
def test_static_node():
    static_node = StaticNode(tasks=['task1'])
    assert static_node.get_tasks() == [Task(
        name='task1', task_id='task1', cgroup_path='/task1',
        labels={}, resources={}, subcgroups_paths=[]
    )]


@patch('os.path.exists', Mock(return_value=False))
def test_static_node_without_cgroups():
    static_node = StaticNode(tasks=['task1'])
    assert static_node.get_tasks() == []
