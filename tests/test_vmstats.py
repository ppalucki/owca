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
from unittest.mock import patch

from tests.testing import create_open_mock, relative_module_path
from wca import vmstats


@patch('builtins.open', new=create_open_mock({
    '/sys/devices/system/node/node0/vmstat': open(
        relative_module_path(__file__, 'fixtures/proc-vmstat-simple.txt')).read(),
    '/sys/devices/system/node/node1/vmstat': open(
        relative_module_path(__file__, 'fixtures/proc-vmstat-simple.txt')).read()
}))
@patch('os.listdir', return_value=['node0', 'node1'])
def test_parse_node_meminfo(*mocks):
    measurements = vmstats.parse_node_vmstat_keys(None)
    assert measurements == {
        'platform_node_vmstat':
            {0: {'nr_bar': 30, 'nr_foo': 20},
             1: {'nr_bar': 30, 'nr_foo': 20}}
    }


@patch('builtins.open', new=create_open_mock({
    "/proc/vmstat": open(relative_module_path(__file__, 'fixtures/proc-vmstat-simple.txt')).read(),
}))
def test_parse_proc_vmstat_keys(*mocks):
    measurements = vmstats.parse_proc_vmstat_keys(None)
    assert measurements == {'platform_vmstat': {'nr_bar': 30, 'nr_foo': 20}}
