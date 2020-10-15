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
import re
from unittest.mock import patch

from tests.testing import create_open_mock, relative_module_path
from wca import sched_stats
from wca.metrics import MetricName


@patch('builtins.open', new=create_open_mock({
    "/proc/1/sched": open(relative_module_path(__file__, 'fixtures/proc-1-sched.txt')).read(),
    "/proc/2/sched": open(relative_module_path(__file__, 'fixtures/proc-2-sched.txt')).read(),
}))
def test_parse_proc_vmstat_keys(*mocks):
    pattern = re.compile('.*numa')
    measurements = sched_stats.get_pids_sched_measurements([1, 2], pattern)
    assert measurements == {
        MetricName.TASK_SCHED_STAT: {
                'mm->numa_scan_seq': 27,
                'numa_pages_migrated': 10.5,
                'numa_preferred_nid': -3.0,
                'total_numa_faults': 0,
                },
        MetricName.TASK_SCHED_STAT_NUMA_FAULTS: {
            '0': {'group_private': 330,
                  'group_shared': 440,
                  'task_private': 110,
                  'task_shared': 220},
            '1': {'group_private': 670,
                  'group_shared': 780,
                  'task_private': 450,
                  'task_shared': 560}
        }
    }
