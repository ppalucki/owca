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
import copy
import logging
import math
from abc import ABC, abstractmethod
from enum import Enum
from pprint import pformat
from typing import List, Dict, Union, Tuple, Optional, Any, Type

from dataclasses import dataclass

from owca import platforms
from owca.detectors import TasksMeasurements, TasksResources, TasksLabels, Anomaly
from owca.logger import trace, TRACE
from owca.mesos import TaskId
from owca.metrics import Metric, MetricType
from owca.platforms import Platform

log = logging.getLogger(__name__)


class AllocationType(str, Enum):
    QUOTA = 'cpu_quota'
    SHARES = 'cpu_shares'
    RDT = 'rdt'

class AllocationValue(ABC):

    @abstractmethod
    def merge_with_current(self, current: 'AllocationValue') -> Tuple[
            'AllocationValue', Optional['AllocationValue']]:
        ...

    @abstractmethod
    def generate_metrics(self) -> List[Metric]:
        ...

    @abstractmethod
    def validate(self) -> List[str]:
        """Returns list of errors, empty list indicates that value is ok."""
        ...

    @abstractmethod
    def perform_allocations(self):
        """Perform allocatoins."""
        ...


TaskAllocations = Dict[AllocationType, Union[int, float, AllocationValue]]
TasksAllocations = Dict[TaskId, TaskAllocations]

TaskAllocationsValues = List[AllocationValue]
TasksAllocationsValues = Dict[TaskId, TaskAllocationsValues]


@dataclass
class AllocationConfiguration:
    # Default value for cpu.cpu_period [ms] (used as denominator).
    cpu_quota_period: int = 1000

    # Number of minimum shares, when ``cpu_shares`` allocation is set to 0.0.
    cpu_shares_min: int = 2
    # Number of shares to set, when ``cpu_shares`` allocation is set to 1.0.
    cpu_shares_max: int = 10000

    # Default Allocation for default root group during initilization.
    # It will be used as default for all tasks (None will set to maximum available value).
    default_rdt_l3: str = None
    default_rdt_mb: str = None


class Allocator(ABC):

    @abstractmethod
    def allocate(
            self,
            platform: Platform,
            tasks_measurements: TasksMeasurements,
            tasks_resources: TasksResources,
            tasks_labels: TasksLabels,
            tasks_allocations: TasksAllocations,
    ) -> (TasksAllocations, List[Anomaly], List[Metric]):
        ...


class NOPAllocator(Allocator):

    def allocate(self, platform, tasks_measurements, tasks_resources,
                 tasks_labels, tasks_allocations):
        return [], [], []
