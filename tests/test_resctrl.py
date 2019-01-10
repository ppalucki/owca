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


import errno
from unittest.mock import call, MagicMock, patch

import pytest

from owca.resctrl import ResGroup, check_resctrl, RESCTRL_ROOT_NAME
from owca.testing import create_open_mock


@patch('builtins.open', new=create_open_mock({
    "/sys/fs/resctrl": "0",
    "/sys/fs/resctrl/tasks": "0",
    "/sys/fs/resctrl/mon_data/mon_L3_00/mbm_total_bytes": "0",
}))
def test_check_resctrl(*mock):
    assert check_resctrl()


@patch('owca.resctrl.log.warning')
@patch('os.path.exists', return_value=True)
@patch('os.makedirs')
@patch('owca.resctrl.SetEffectiveRootUid')
def test_add_tasks(*args):
    root_tasks_mock = MagicMock()
    tasks_mock = MagicMock()
    mongroup_tasks_mock = MagicMock()
    open_mock = create_open_mock({
        "/sys/fs/resctrl": "0",
        "/sys/fs/resctrl/tasks": root_tasks_mock,
        # for best_efforts resctrl group
        "/sys/fs/resctrl/best_efforts/tasks": tasks_mock,
        "/sys/fs/resctrl/best_efforts/mon_groups/task_id/tasks": mongroup_tasks_mock,
    })
    with patch('builtins.open', open_mock):
        resgroup = ResGroup("best_efforts")
        resgroup.add_tasks(['123', '124'], 'task_id')
        tasks_mock.assert_called_once_with(
            '/sys/fs/resctrl/best_efforts/tasks', 'w')
        mongroup_tasks_mock.assert_called_once_with(
            '/sys/fs/resctrl/best_efforts/mon_groups/task_id/tasks', 'w')
        tasks_mock.assert_has_calls([call().__enter__().write('123')])
        tasks_mock.assert_has_calls([call().__enter__().write('124')])
        mongroup_tasks_mock.assert_has_calls([call().__enter__().write('123')])
        mongroup_tasks_mock.assert_has_calls([call().__enter__().write('124')])


@patch('owca.resctrl.log.warning')
@patch('os.path.exists', return_value=True)
@patch('os.makedirs', side_effect=OSError(errno.ENOSPC, "mock"))
@patch('builtins.open', new=create_open_mock({
    "/sys/fs/cgroup/cpu/ddd/tasks": "123",
}))
def test_sync_no_space_left_on_device(makedirs_mock, exists_mock, log_warning_mock):
    with pytest.raises(Exception, match='Limit of workloads reached'):
        ResGroup("best_efforts")


@patch('builtins.open', new=create_open_mock({
    "/sys/fs/resctrl/mon_groups/best_efforts/mon_data/1/mbm_total_bytes": "1",
    "/sys/fs/resctrl/mon_groups/best_efforts/mon_data/2/mbm_total_bytes": "1",
    "/sys/fs/resctrl/mon_groups/best_efforts/mon_data/1/llc_occupancy": "1",
    "/sys/fs/resctrl/mon_groups/best_efforts/mon_data/2/llc_occupancy": "1",
    "/sys/fs/cgroup/cpu/best_efforts/cpuacct.usage": "4",
}))
@patch('os.listdir', return_value=['1', '2'])
def test_get_measurements(*mock):
    resgroup = ResGroup(name=RESCTRL_ROOT_NAME)
    assert {'memory_bandwidth': 2, 'llc_occupancy': 2} == resgroup.get_measurements('best_efforts')


@patch('builtins.open', new=create_open_mock({
    "/sys/fs/resctrl/mesos-1/tasks": "1\n2\n",
    # resctrl group to recycle - expected to be removed.
    "/sys/fs/resctrl/mesos-2/tasks": "",
    "/sys/fs/resctrl/mesos-3/tasks": "2",
    "/sys/fs/resctrl/mon_groups/mesos-1/tasks": "1\n2\n",
    # resctrl group to recycle - should be removed.
    "/sys/fs/resctrl/mon_groups/mesos-2/tasks": "",
    "/sys/fs/resctrl/mon_groups/mesos-3/tasks": "2",
}))
@patch('os.listdir', return_value=['mesos-1', 'mesos-2', 'mesos-3'])
@patch('os.rmdir')
@patch('os.path.isdir', return_value=True)
@patch('os.path.exists', return_value=True)
def test_clean_resctrl(exists_mock, isdir_mock, rmdir_mock, listdir_mock):
    from owca.resctrl import cleanup_resctrl
    cleanup_resctrl()
    assert listdir_mock.call_count == 2
    assert isdir_mock.call_count == 6
    assert exists_mock.call_count == 6
    assert rmdir_mock.call_count == 2
    rmdir_mock.assert_has_calls([
        call('/sys/fs/resctrl/mesos-2'),
        call('/sys/fs/resctrl/mon_groups/mesos-2'),
    ])
