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
from typing import Dict, List

from wca.logger import TRACE
from wca.metrics import Metric, MetricType
from wca.scheduler.algorithms.base import get_requested_fraction
from wca.scheduler.algorithms.fit import Fit
from wca.scheduler.data_providers import DataProvider
from wca.scheduler.metrics import MetricName
from wca.scheduler.types import ResourceType
from wca.scheduler.types import ResourceType as rt

log = logging.getLogger(__name__)


class BAR(Fit):
    def __init__(self,
                 data_provider: DataProvider,
                 dimensions: List[ResourceType] = [rt.CPU, rt.MEM, rt.MEMBW_READ, rt.MEMBW_WRITE],
                 bar_weights: Dict[rt, float] = None,
                 alias=None,
                 max_node_score: float = 10.,
                 ):
        Fit.__init__(self, data_provider, dimensions, alias=alias, max_node_score=max_node_score)
        self.bar_weights = bar_weights or {}

    def priority_for_node(self, node_name, app_name, data_provider_queried) -> float:
        """ BAR """
        nodes_capacities, assigned_apps_counts, apps_spec, _ = data_provider_queried
        requested_fraction, metrics = get_requested_fraction(
            app_name, apps_spec, assigned_apps_counts, node_name, nodes_capacities, self.dimensions)
        self.metrics.extend(metrics)

        # Mean - priority according to variance of dimensions
        mean = sum([v for v in requested_fraction.values()]) / len(requested_fraction)
        log.log(TRACE, "[Prioritize][app=%s][node=%s][bar] Mean: %s", app_name, node_name, mean)
        self.metrics.add(
            Metric(name=MetricName.BAR_MEAN,
                   value=mean, labels=dict(app=app_name, node=node_name),
                   type=MetricType.GAUGE))

        # Variance
        if len(requested_fraction) > 2:
            variance = sum([((fraction - mean) * (fraction - mean)) * self.bar_weights.get(rt, 1)
                            for rt, fraction in requested_fraction.items()]) \
                       / len(requested_fraction)
        elif len(requested_fraction) == 2:
            values = list(requested_fraction.values())
            variance = abs(values[0] - values[1])
        else:
            variance = 0

        log.log(TRACE,
                "[Prioritize][app=%s][node=%s][bar] "
                "Variance(weighted quadratic sum of requested_fraction-mean): %s",
                app_name, node_name, variance)
        self.metrics.add(
            Metric(name=MetricName.BAR_VARIANCE,
                   value=variance, labels=dict(app=app_name, node=node_name),
                   type=MetricType.GAUGE))

        bar_score = (1.0 - variance)
        log.debug("[Prioritize][app=%s][node=%s][bar] Bar score: %s", app_name, node_name,
                  bar_score)
        self.metrics.add(
            Metric(name=MetricName.BAR_SCORE,
                   value=bar_score, labels=dict(app=app_name, node=node_name),
                   type=MetricType.GAUGE))

        return bar_score
