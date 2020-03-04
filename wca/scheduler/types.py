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
from enum import Enum
from typing import Dict, List, Optional

from wca.config import assure_type

# Kubernetes
NodeName = str
TaskName = str
AppName = str
FailureMessage = str


class UnsupportedCase(Exception):
    """Raised when kube-scheduler passes information about nodes rather
    than list of node names which wca-scheduler supports."""
    pass

#  https://github.com/kubernetes/kubernetes/blob/release-1.15/pkg/scheduler/api/types.go#L299
@dataclass
class ExtenderFilterResult:
    Nodes: Optional[List[Dict]] = None
    NodeNames: List[NodeName] = field(default_factory=lambda: [])
    FailedNodes: Dict[NodeName, FailureMessage] = field(default_factory=lambda: {})
    Error: str = ''

    def __post_init__(self):
        if self.Nodes:
            raise UnsupportedCase()

        assure_type(self.NodeNames, List[NodeName])
        assure_type(self.FailedNodes, Dict[NodeName, FailureMessage])
        assure_type(self.Error, str)


#  https://github.com/kubernetes/kubernetes/blob/release-1.15/pkg/scheduler/api/types.go#L331
@dataclass
class HostPriority:
    Host: str
    Score: int

    def __post_init__(self):
        assure_type(self.Host, str)
        assure_type(self.Score, int)


#  https://github.com/kubernetes/kubernetes/blob/release-1.15/pkg/scheduler/api/types.go#L284
@dataclass
class ExtenderArgs:
    Nodes: Optional[List[Dict]]
    Pod: Dict
    NodeNames: List[NodeName]

    def __post_init__(self):

        if self.Nodes:
            raise UnsupportedCase()

        assure_type(self.Pod, dict)
        assure_type(self.NodeNames, List[str])


# Internal
class ResourceType(str, Enum):
    MEM = 'mem'
    CPU = 'cpu'
    MEMBW_WRITE = 'membw_write'
    MEMBW_READ = 'membw_read'
    WSS = 'wss'

    # Only for internal use
    MEMBW = 'membw'
    MEMBW_FLAT = 'membw_flat'

    def __repr__(self):
        return self.value


AppsCount = Dict[AppName, int]
Resources = Dict[ResourceType, float]
