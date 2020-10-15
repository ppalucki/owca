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
from typing import Dict, Pattern, Optional, List
from wca.metrics import MetricName, Measurements, merge_measurements

DEFAULT_SCHED_KEY_REGEXP = r'.*'


def _parse_proc_sched(sched_filename: str, pattern: Optional[Pattern]) -> Dict[str, int]:
    """Parses /proc/PID/sched only with ':' within line"""
    measurements = {}
    with open(sched_filename) as f:
        for line in f.readlines():
            if ':' not in line:
                continue

            key, value_str = line.split(':')
            key = key.strip()

            if pattern is not None and not pattern.match(key):
                # Skip unmatching keys.
                continue

            # Parse value
            value_str = value_str.strip()
            if '.' in value_str:
                value = float(value_str)
            else:
                value = int(value_str)

            measurements[key] = float(value)

    return measurements


def _get_pid_sched_measurements(pid: int, pattern: Optional[Pattern]) -> Measurements:
    return {MetricName.TASK_SCHED_STAT: _parse_proc_sched('/proc/%i/sched' % pid, pattern)}


def get_pids_sched_measurements(pids: List[int], pattern: Optional[Pattern]):
    pids_measurements = []
    for pid in pids:
        pid_measurements = _get_pid_sched_measurements(pid, pattern)
        pids_measurements.append(pid_measurements)

    merged_measurements = merge_measurements(pids_measurements)
    return merged_measurements
