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

from owca.config import load_config
from owca.nodes import Node, Task

log = logging.getLogger(__name__)

@dataclass
class StaticNode(Node):
    """Dummy implementation of tasks for testing."""

    config: str

    def get_tasks(self) -> List[Task]:
        if not os.path.exists(self.config):
            return []
        else:
            tasks_data = load_config(self.config)
            tasks = []
            for task_raw in tasks_data:
                tasks.append(Task(
                    name=task_raw['name'],
                    task_id=task_raw['task_id'],
                    cgroup_path=task_raw['cgroup_path'],
                    labels=dict(),
                    resources=dict(),
                ))
        return tasks
