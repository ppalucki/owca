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
from typing import Pattern, Optional, List, Tuple
from wca.metrics import MetricName, Measurements, merge_measurements

DEFAULT_SCHED_KEY_REGEXP = r'.*'


def _parse_proc_sched(sched_filename: str,
                      pattern: Optional[Pattern]) -> Tuple[Measurements, Measurements]:
    """Parses /proc/PID/sched only with ':' within line"""
    key_measurements = {}
    numa_faults_measurements = {}
    with open(sched_filename) as f:
        for line in f.readlines():

            if '#threads' in line:
                continue

            if line.startswith('numa_faults '):
                # Only supported format is for kernel > 4.x
                # numa_faults node=0 task_private=0 task_shared=0 group_private=0 group_shared=0
                fields = line.split()
                if len(fields) != 6:
                    continue
                numa_node_raw = fields[1]
                numa_node_key, numa_node = numa_node_raw.split('=')
                assert numa_node_key == 'node'
                numa_node = str(int(numa_node))  # mare sure it is int

                # Ignore two first parts (name and node field).
                fields = fields[2:]
                for field in fields:
                    field_type, field_value_raw = field.split('=')
                    field_value = int(field_value_raw)
                    if numa_node not in numa_faults_measurements:
                        numa_faults_measurements[numa_node] = {}
                    numa_faults_measurements[str(numa_node)][field_type] = field_value

                continue

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

            key_measurements[key] = float(value)

    return key_measurements, numa_faults_measurements


def _get_pid_sched_measurements(pid: int, pattern: Optional[Pattern]) -> Measurements:
    key_measurements, numa_faults_measurements = _parse_proc_sched(
        '/proc/%i/sched' % pid, pattern)

    return {MetricName.TASK_SCHED_STAT: key_measurements,
            MetricName.TASK_SCHED_STAT_NUMA_FAULTS: numa_faults_measurements}


def get_pids_sched_measurements(pids: List[int], pattern: Optional[Pattern]):
    pids_measurements = []
    for pid in pids:
        pid_measurements = _get_pid_sched_measurements(pid, pattern)
        pids_measurements.append(pid_measurements)

    merged_measurements = merge_measurements(pids_measurements)
    return merged_measurements
