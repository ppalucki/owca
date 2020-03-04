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
from typing import Tuple

from wca.scheduler.algorithms import DataMissingException
from wca.scheduler.algorithms.base import BaseAlgorithm, sum_resources, substract_resources, \
    used_free_requested

log = logging.getLogger(__name__)


class Fit(BaseAlgorithm):
    """Filter all nodes where the scheduled app does not fit.
       Supporting any number of dimensions.
       Treats MEMBW_READ and MEMBW_WRITE differently than other dimensions."""

    def app_fit_node(self, node_name, app_name, data_provider_queried) -> Tuple[bool, str]:
        nodes_capacities, assigned_apps_counts, apps_spec, _ = data_provider_queried

        # Current node context: used and free currently
        used, free, requested, capacity, membw_read_write_ratio, metrics = \
            used_free_requested(node_name, app_name, self.dimensions,
                                nodes_capacities, assigned_apps_counts, apps_spec)
        self.metrics.extend(metrics)

        # SUBTRACT: "free" after simulated assigment of requested
        try:
            requested_and_used = sum_resources(requested, used)
        except ValueError as e:
            msg = 'cannot sum app=%s requested=%s and node=%s used=%s: %s' % (
                    app_name, requested, node_name, used, e)
            log.error(msg)
            raise DataMissingException(msg) from e

        free_after_bind = substract_resources(
            capacity,
            requested_and_used,
            membw_read_write_ratio,
        )

        # CHECK
        broken_capacities = {r: abs(v) for r, v in free_after_bind.items() if v < 0}

        if not broken_capacities:
            log.debug('[Filter][app=%s][node=%s] ok free_after_bind=%r',
                      app_name, node_name, free_after_bind)
            return True, ''
        else:
            broken_capacities_str = \
                ','.join(['({}: {})'.format(r, v) for r, v in broken_capacities.items()])
            log.debug('[Filter][app=%s][node=%s] broken capacities: missing %r',
                      app_name, node_name, broken_capacities_str)
            return False, 'Could not fit node for dimensions: missing {}.'.format(
                    broken_capacities_str)

    def priority_for_node(self, node_name: str, app_name: str,
                          data_provider_queried: Tuple) -> float:
        """no prioritization method for FitGeneric"""
        return 0.0
