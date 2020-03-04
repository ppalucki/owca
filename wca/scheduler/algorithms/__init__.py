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
from abc import ABC, abstractmethod
from typing import List, Tuple, Optional

from wca.metrics import Metric
from wca.scheduler.metrics import MetricRegistry
from wca.scheduler.types import ExtenderArgs, ExtenderFilterResult, HostPriority

log = logging.getLogger(__name__)


class DataMissingException(Exception):
    pass


class Algorithm(ABC):
    @abstractmethod
    def filter(self, extender_args: ExtenderArgs) -> Tuple[ExtenderFilterResult, List[Metric]]:
        pass

    @abstractmethod
    def prioritize(self, extender_args: ExtenderArgs) -> Tuple[List[HostPriority], List[Metric]]:
        pass

    @abstractmethod
    def get_metrics_registry(self) -> Optional[MetricRegistry]:
        return None

    @abstractmethod
    def get_metrics_names(self) -> List[str]:
        return []

    @abstractmethod
    def reinit_metrics(self):
        pass
