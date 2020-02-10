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
from typing import List, Tuple

from wca.metrics import Metric, MetricType
from wca.logger import TRACE
from wca.scheduler.algorithms import BaseAlgorithm, used_resources_on_node, membw_check
from wca.scheduler.metrics import MetricName
from wca.scheduler.types import (ExtenderArgs, HostPriority, NodeName)
from wca.scheduler.types import ResourceType as rt

log = logging.getLogger(__name__)


class FitGeneric(BaseAlgorithm):
    """Filter all nodes where the scheduled app does not fit.
       Supporting any number of dimensions.
       Treats MEMBW_READ and MEMBW_WRITE differently than other dimensions."""

    def app_fit_node(self, node_name: NodeName, app_name: str,
                     data_provider_queried: Tuple) -> Tuple[bool, str]:
        nodes_capacities, assigned_apps_counts, apps_spec = data_provider_queried

        used = used_resources_on_node(self.dimensions, assigned_apps_counts[node_name], apps_spec)
        capacity = nodes_capacities[node_name]
        requested = apps_spec[app_name]

        broken_capacities = set([r for r in self.dimensions
                                 if requested[r] > capacity[r] - used[r]])

        log.log(TRACE, "Requested %s Capacity %s Used %s", requested, capacity, used)

        if not membw_check(requested, used, capacity):
            for broken in broken_capacities:
                if broken in (rt.MEMBW, rt.MEMBW_READ, rt.MEMBW_WRITE):
                    log.warning('Not enough resources! [%s]: %r' %
                                (broken, (capacity[broken] - used[broken] - requested[broken])))
            broken_capacities.update((rt.MEMBW_READ, rt.MEMBW_READ,))

        broken_capacities_str = ','.join([str(e) for e in broken_capacities])

        # Prepare metrics.
        for resource in used:
            self.metrics.append(
                Metric(name=MetricName.NODE_USED_RESOURCE,
                       value=used[resource],
                       labels=dict(node=node_name, resource=resource),
                       type=MetricType.GAUGE,))

        for resource in capacity:
            self.metrics.append(
                Metric(name=MetricName.NODE_CAPACITY_RESOURCE,
                       value=capacity[resource],
                       labels=dict(node=node_name, resource=resource),
                       type=MetricType.GAUGE,))

        for resource in requested:
            self.metrics.append(
                Metric(name=MetricName.APP_REQUESTED_RESOURCE,
                       value=used[resource],
                       labels=dict(resource=resource, app=app_name),
                       type=MetricType.GAUGE,))

        if not broken_capacities:
            return True, ''
        else:
            log.debug("Broken_capacities: {}".format(broken_capacities))
            return False, 'Could not fit node for dimensions: ({}).'.format(broken_capacities_str)

    def priority_for_node(self, node_name: str, app_name: str,
                          data_provider_queried: Tuple) -> int:
        """no prioritization method for FitGeneric"""
        return 0


class FitGenericTesting(FitGeneric):
    """with some testing cluster specific hacks"""

    def prioritize(self, extender_args: ExtenderArgs) -> List[HostPriority]:
        nodes = extender_args.NodeNames
        log.info('[Prioritize] Nodes: %r' % nodes)
        nodes = sorted(extender_args.NodeNames)
        return self.testing_prioritize(nodes)

    @staticmethod
    def testing_prioritize(nodes):
        priorities = []

        # Trick to not prioritize:
        # nodeSelector:
        #   goal: load_generator
        if nodes[0] == 'node200':
            return priorities

        if len(nodes) > 0:
            for node in sorted(nodes):
                priorities.append(HostPriority(node, 0))
            priorities[0].Score = 100
        return priorities
