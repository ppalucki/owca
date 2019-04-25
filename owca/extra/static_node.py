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

import logging
import os
from typing import List

from dataclasses import dataclass

from owca.config import Str
from owca.nodes import Node, Task

log = logging.getLogger(__name__)


@dataclass
class StaticNode(Node):
    """Simple implementation of Node that returns tasks based on
    provided list on tasks names.

    Tasks are returned only if corresponding cgroups exists:
    - /sys/fs/cgroup/cpu/(task_name)
    - /sys/fs/cgroup/cpuacct/(task_name)
    - /sys/fs/cgroup/perf_event/(task_name)

    Otherwise, the item is ignored.
    """

    # List of task names.
    tasks: List[Str]
    require_pids: bool = False

    _BASE_CGROUP_PATH = '/sys/fs/cgroup'
    _REQUIRED_CONTROLLERS = ('cpu', 'cpuacct', 'perf_event')

    def get_tasks(self) -> List[Task]:
        tasks = []
        for task_name in self.tasks:
            for required_controller in self._REQUIRED_CONTROLLERS:
                full_cgroup_path = os.path.join(
                    self._BASE_CGROUP_PATH, required_controller, task_name, 'tasks')
                if not os.path.exists(full_cgroup_path):
                    log.warning('StaticNode: There is no required cgroup %r for %r - skipping!',
                                full_cgroup_path, task_name)
                    break
                if self.require_pids and len(open(full_cgroup_path).readlines()) == 0:
                    log.warning('StaticNode: There is no pids in cgroup %r for %r - skipping!',
                                full_cgroup_path, task_name)
                    break
            else:
                tasks.append(
                    Task(
                        name=task_name,
                        task_id=task_name,
                        cgroup_path='/%s' % task_name,
                        labels={},
                        resources={},
                        subcgroups_paths=[]
                    )
                )
        return tasks
