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

from abc import ABC, abstractmethod
from typing import List, Tuple, Iterable, Any
import logging

from wca.metrics import Metric
from wca.logger import TRACE
from wca.scheduler.types import ExtenderArgs, ExtenderFilterResult, HostPriority, \
                                NodeName, Resources
from wca.scheduler.types import ResourceType as rt
from wca.scheduler.data_providers import DataProvider
from wca.scheduler.utils import extract_common_input

log = logging.getLogger(__name__)


class Algorithm(ABC):
    @abstractmethod
    def filter(self, extender_args: ExtenderArgs) -> Tuple[
            ExtenderFilterResult, List[Metric]]:
        pass

    @abstractmethod
    def prioritize(self, extender_args: ExtenderArgs) -> Tuple[
            List[HostPriority], List[Metric]]:
        pass


class BaseAlgorithm(Algorithm):
    """Implementing some basic functionalities which probably
       each Algorithm subclass will need to do. However forcing
       some way of implementing filtering and prioritizing which may
       not match everybody needs."""

    def __init__(self, data_provider: DataProvider,
                 dimensions: Iterable[rt] = (rt.CPU, rt.MEM, rt.MEMBW_READ, rt.MEMBW_WRITE)):
        self.data_provider = data_provider
        self.dimensions = dimensions
        self.metrics = []

    def filter(self, extender_args: ExtenderArgs) -> Tuple[
            ExtenderFilterResult, List[Metric]]:
        log.debug('[Filter] ExtenderArgs: %r' % extender_args)
        app_name, nodes_names, namespace, name = extract_common_input(extender_args)

        extender_filter_result = ExtenderFilterResult()

        # Clear for new metrics.
        self.metrics = []

        data_provider_queried = self.query_data_provider()

        for node_name in nodes_names:
            passed, message = self.app_fit_node(node_name, app_name, data_provider_queried)
            if not passed:
                log.log(TRACE, 'Failed Node %r, %r', node_name, message)
                extender_filter_result.FailedNodes[node_name] = message
            else:
                extender_filter_result.NodeNames.append(node_name)

        return extender_filter_result, self.metrics

    def prioritize(self, extender_args: ExtenderArgs) -> Tuple[
            List[HostPriority], List[Metric]]:
        app_name, nodes_names, namespace, name = extract_common_input(extender_args)

        priorities = []

        # Clear for new metrics.
        self.metrics = []

        data_provider_queried = self.query_data_provider()

        for node_name in sorted(nodes_names):
            priority = self.priority_for_node(node_name, app_name, data_provider_queried)
            priorities.append(HostPriority(node_name, priority))

        return priorities, self.metrics

    @abstractmethod
    def app_fit_node(self, node_name: NodeName, app_name: str,
                     data_provider_queried: Tuple[Any]) -> bool:
        """Consider if the app match the given node."""
        pass

    @abstractmethod
    def priority_for_node(self, node_name: str, app_name: str,
                          data_provider_queried: Tuple[Any]) -> int:
        """Considering priority of the given node."""
        pass

    def query_data_provider(self) -> Tuple:
        """Should be overwritten if one needs more data from DataProvider."""
        dp = self.data_provider
        assigned_apps_counts, apps_unassigned = dp.get_apps_counts()
        nodes_capacities = dp.get_nodes_capacities(self.dimensions)
        apps_spec = dp.get_apps_requested_resources(self.dimensions)
        return nodes_capacities, assigned_apps_counts, apps_spec


def used_resources_on_node(dimensions, assigned_apps_counts, apps_spec) -> Resources:
    """Calculate used resources on a given node using data returned by data provider."""
    used = {dim: 0 for dim in dimensions}
    for app, count in assigned_apps_counts.items():
        for dim in dimensions:
            used[dim] += apps_spec[app][dim] * count
    return used


def free_resources_on_node(
        dimensions: Iterable[rt], capacity: Resources,
        used: Resources) -> Resources:
    """Returns free resources on node, by substracting capacity-used"""
    free = capacity.copy()
    for dimension in dimensions:
        if dimension not in (rt.MEMBW_READ, rt.MEMBW_WRITE):
            free[dimension] -= used[dimension]
    if rt.MEMBW_READ in dimensions:
        assert rt.MEMBW_WRITE in dimensions
        read, write = rt.MEMBW_READ, rt.MEMBW_WRITE
        R = float(capacity[rt.MEMBW_READ])/float(capacity[rt.MEMBW_WRITE])
        free[read] = capacity[read] - (used[read] + used[write] * R)
        free[write] = capacity[write] - (used[write] + used[read] / R)
    return free


def membw_check(requested: Resources, used: Resources, capacity: Resources) -> bool:
    """
    read/write ratio, e.g. 40GB/s / 10GB/s = 4,
    what means reading is 4 time faster
    """
    # Assert that required dimensions are available.
    for resource in (rt.MEMBW_WRITE, rt.MEMBW_READ,):
        for source in (requested, used):
            if resource not in source:
                return True

    # To shorten the notation.
    WRITE = rt.MEMBW_WRITE
    READ = rt.MEMBW_READ
    R = float(capacity[rt.MEMBW_READ])/float(capacity[rt.MEMBW_WRITE])

    return (used[READ]+requested[READ]) + R * (used[WRITE]+requested[WRITE]) < capacity[READ]


def sum_resources(a: Resources, b: Resources) -> Resources:
    assert set(a.keys()) == set(b.keys()), \
        'the same dimensions must be provided for both resources'
    c = {}
    for resource in a.keys():
        c[resource] = a[resources] + b[resources]
    return c


def substract_resources(a: Resources, b: Resources, membw_read_write_ratio: float) -> Resources:
    assert set(a.keys()) == set(b.keys()), \
        'the same dimensions must be provided for both resources'
    assert type(membw_read_write_ratio) == float
    dimensions = set(a.keys())

    c = a.copy()
    for dimension in dimensions:
        if dimension not in (rt.MEMBW_READ, rt.MEMBW_WRITE):
            c[dimension] = a[dimensions] - b[dimension]
    if rt.MEMBW_READ in dimensions:
        assert rt.MEMBW_WRITE in dimensions
        read, write = rt.MEMBW_READ, rt.MEMBW_WRITE
        c[read] = a[read] - (b[read] + b[write] * membw_read_write_ratio)
        c[write] = a[write] - (b[write] + b[read] / membw_read_write_ratio)
    return c
