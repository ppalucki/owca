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
import os

from typing import Dict, Pattern, Optional
from wca.metrics import MetricName, Measurements

DEFAULT_VMSTAT_KEY_REGEXP = r'.*'


def _parse_vmstat(vmstat_filename: str, regexp: Optional[Pattern]) -> Dict[str, int]:
    measurements = {}
    with open(vmstat_filename) as f:
        for line in f.readlines():
            key, value = line.split()
            if regexp is not None and not regexp.match(key):
                # Skip unmatching keys.
                continue
            measurements[key] = int(value)
    return measurements


BASE_SYSFS_NODES_PATH = '/sys/devices/system/node'


def parse_node_vmstat_keys(regexp: Optional[Pattern]) -> Measurements:
    """Parses /sys/devices/system/node/node*/vmstat
    """
    measurements = {}
    for nodedir in os.listdir(BASE_SYSFS_NODES_PATH):
        if nodedir.startswith('node'):
            node_id = int(nodedir[4:])
            vmstat_filename = os.path.join(BASE_SYSFS_NODES_PATH, nodedir, 'vmstat')
            measurements[node_id] = _parse_vmstat(vmstat_filename, regexp)
    return {MetricName.PLATFORM_NODE_VMSTAT: measurements}


def parse_proc_vmstat_keys(regexp: Pattern) -> Measurements:
    """Parses /proc/vmstat """
    return {MetricName.PLATFORM_VMSTAT: _parse_vmstat('/proc/vmstat', regexp)}
