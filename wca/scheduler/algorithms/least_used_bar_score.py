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
from typing import Dict, List, Optional, Tuple, Any

from wca.scheduler.algorithms.base import DEFAULT_DIMENSIONS, QueryDataProviderInfo
from wca.scheduler.algorithms.least_used_bar import LeastUsedBAR
from wca.scheduler.algorithms.score import Score
from wca.scheduler.data_providers.score import ScoreDataProvider
from wca.scheduler.types import ResourceType, NodeName


class LeastUsedBARScore(LeastUsedBAR, Score):

    def __init__(self, data_provider: ScoreDataProvider,
                 dimensions: List[ResourceType] = DEFAULT_DIMENSIONS,
                 least_used_weights: Dict[ResourceType, float] = None,
                 bar_weights: Dict[ResourceType, float] = None,
                 least_used_weight=1,
                 alias=None,
                 max_node_score: float = 10.,
                 score_target: Optional[float] = None,
                 strict_mode_placement: bool = False,
                 threshold: float = 0.97
                 ):
        LeastUsedBAR.__init__(self, data_provider, dimensions, least_used_weights,
                              bar_weights, least_used_weight, alias, max_node_score)
        Score.__init__(self, data_provider, dimensions, max_node_score, alias, score_target,
                       strict_mode_placement, threshold)

    def priority_for_node(self, node_name: str, app_name: str,
                          data_provider_queried: Tuple[Any]) -> float:
        return LeastUsedBAR.priority_for_node(self, node_name, app_name, data_provider_queried)

    def app_fit_node(self, node_name: NodeName, app_name: str,
                     data_provider_queried: QueryDataProviderInfo) -> Tuple[bool, str]:
        return Score.app_fit_node(self, node_name, app_name, data_provider_queried)

    def app_fit_nodes(self, node_names: List[NodeName], app_name: str,
                      data_provider_queried: QueryDataProviderInfo) -> \
            Tuple[List[NodeName], Dict[NodeName, str]]:
        return Score.app_fit_nodes(self, node_names, app_name, data_provider_queried)
