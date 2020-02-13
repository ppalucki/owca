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

import logging
from typing import Tuple, Dict, Any, Iterable

from wca.logger import TRACE

from wca.scheduler.algorithms import used_resources_on_node, free_resources_on_node
from wca.scheduler.data_providers import DataProvider
from wca.scheduler.algorithms.fit import FitGeneric
from wca.scheduler.types import ResourceType as rt

log = logging.getLogger(__name__)


class BARGeneric(FitGeneric):
    def __init__(self, data_provider: DataProvider,
                 dimensions: Iterable[rt] = (rt.CPU, rt.MEM, rt.MEMBW_READ, rt.MEMBW_WRITE),
                 max_node_score: int = 10, least_used_weights: Dict[rt, float] = None):
        FitGeneric.__init__(self, data_provider, dimensions)
        if least_used_weights is None:
            self.least_used_weights = {dim: 1 for dim in self.dimensions}
            self.least_used_weights[rt.MEMBW_FLAT] = 1
        else:
            self.least_used_weights = least_used_weights
        self.max_node_score = max_node_score

    def priority_for_node(self, node_name: str, app_name: str,
                          data_provider_queried: Tuple[Any]) -> int:
        nodes_capacities, assigned_apps_counts, apps_spec = data_provider_queried

        used, free, requested = used_free_requested(node_name, app_name, self.dimensions,
                                                    *data_provider_queried)

        # Parse "requested" as dict from defaultdict to get better string representation.
        log.log(TRACE, "[Prioritize][%s][%s] Requested %s Free %s Used %s",
                app_name, node_name, dict(requested), free, used)

        requested_fraction = app_requested_fraction(self.dimensions, requested, free)

        log.log(TRACE, "[Prioritize][%s][%s] Requested fraction: %s",
                app_name, node_name, requested_fraction)

        # Least used.
        weights = self.least_used_weights
        weights_sum = sum([weight for weight in weights.values()])
        free_fraction = {dim: 1.0-fraction for dim, fraction in requested_fraction.items()}
        least_used_score = \
            sum([free_fraction*weights[dim] for dim, free_fraction in free_fraction.items()]) \
            / weights_sum * self.max_node_score

        log.log(TRACE, "[Prioritize][%s][%s] Least used score: %s",
                app_name, node_name, least_used_score)

        # priority according to variance of dimensions
        mean = sum([v for v in requested_fraction.values()])/len(requested_fraction)

        log.log(TRACE, "[Prioritize][%s][%s] Mean: %s",
                app_name, node_name, mean)

        if len(requested_fraction) > 2:
            variance = sum([(fraction - mean)*(fraction - mean)
                            for fraction in requested_fraction.values()]) \
                       / len(requested_fraction)
        elif len(requested_fraction) == 1:
            variance = abs(requested_fraction[0] - requested_fraction[1])
        else:
            variance = 0

        log.log(TRACE, "[Prioritize][%s][%s] Variance: %s",
                app_name, node_name, variance)

        bar_score = int((1-variance) * self.max_node_score)

        log.log(TRACE, "[Prioritize][%s][%s] Bar score: %s",
                app_name, node_name, bar_score)

        result = (bar_score + least_used_score) / 2

        log.log(TRACE, "[Prioritize][%s][%s] Result: %s",
                app_name, node_name, result)

        return result


def app_requested_fraction(dimensions, requested, free) -> Dict[rt, float]:
    """Flats MEMBW_WRITE and MEMBW_READ to single dimension MEMBW_FLAT"""
    fractions = {}
    for dimension in dimensions:
        if dimension not in (rt.MEMBW_READ, rt.MEMBW_WRITE):
            fractions[dimension] = float(requested[dimension]) / float(free[dimension])
    if rt.MEMBW_READ in dimensions:
        assert rt.MEMBW_WRITE in dimensions
        fractions[rt.MEMBW_FLAT] = (requested[rt.MEMBW_READ] + 4*requested[rt.MEMBW_WRITE]) \
            / (free[rt.MEMBW_READ] + 4*free[rt.MEMBW_WRITE])
    return fractions


def used_free_requested(
        node_name, app_name, dimensions,
        nodes_capacities, assigned_apps_counts, apps_spec):
    """Helper function not making any new calculations."""
    used = used_resources_on_node(dimensions, assigned_apps_counts[node_name], apps_spec)
    free = free_resources_on_node(dimensions, nodes_capacities[node_name], used)  # allocable
    requested = apps_spec[app_name]
    return used, free, requested
