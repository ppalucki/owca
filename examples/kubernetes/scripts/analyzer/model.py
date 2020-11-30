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

from dataclasses import dataclass, field
from typing import Dict, List


@dataclass
class Task:
    name: str
    workload_name: str
    node: str
    performance_metrics: Dict[str, float] = field(default_factory=lambda: {})


@dataclass
class Workload:
    name: str
    tasks: List[Task]
    performance_metrics: Dict[str, float] = field(default_factory=lambda: {})


@dataclass
class Node:
    name: str
    # per socket performance_metrics [socket][metric_name]
    performance_metrics: Dict[int, Dict[str, float]] = field(default_factory=lambda: {})
