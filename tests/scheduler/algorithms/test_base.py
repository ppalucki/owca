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
import pytest
from typing import Dict

from wca.scheduler.algorithms.base import (
        used_resources_on_node, sum_resources,
        subtract_resources, flat_membw_read_write,
        divide_resources, used_free_requested, get_requested_fraction,
        get_nodes_used_resources)
from wca.scheduler.types import ResourceType as rt, Apps, NodeName


def build_resources(cpu=None, mem=None, membw_read=None, membw_write=None):
    r = {rt.CPU: cpu, rt.MEM: mem, rt.MEMBW_READ: membw_read, rt.MEMBW_WRITE: membw_write}
    r = {resource: val for resource, val in r.items() if val is not None}
    return r


def build_resources_2(membw_read=None, membw_write=None):
    return build_resources(None, None, membw_read, membw_write)


def test_sum_resources():
    sum_ = sum_resources(build_resources(3, 3), build_resources(2, 2))
    assert sum_[rt.CPU] == 5 and sum_[rt.MEM] == 5


def test_substract_resources():
    sub_ = subtract_resources(build_resources(cpu=3, mem=3), build_resources(cpu=2, mem=2), 4.0)
    assert sub_[rt.CPU] == 1 and sub_[rt.MEM] == 1


def test_flat_membw_read_write():
    r = flat_membw_read_write(build_resources(3, 3, 4, 1), 4.0)
    assert rt.MEMBW_READ not in r and rt.MEMBW_WRITE not in r
    assert r[rt.MEMBW_FLAT] == 8.0
    assert r[rt.CPU] == 3 and r[rt.MEM] == 3


def test_divide_resources():
    a = build_resources(3, 3, 4, 1)
    b = build_resources(2, 2, 8, 2)
    c = divide_resources(a, b, 4.0)
    assert c[rt.CPU] == 3.0 / 2.0 and c[rt.MEM] == 3.0 / 2.0
    assert c[rt.MEMBW_FLAT] == 0.5


def test_used_free_requested_and_requested_fraction():
    dimensions = {rt.CPU, rt.MEM}
    app_name = 'app1'
    node_name = 'node1'
    # Assuming app2 is already scheduled.
    apps_spec = {app_name: {rt.CPU: 2, rt.MEM: 2}, 'app2': {rt.CPU: 1, rt.MEM: 1}}
    node_capacities = {node_name: {rt.CPU: 20, rt.MEM: 20}}
    assigned_apps: Dict[NodeName, Apps] = {
        node_name: {'app2': ['app2_0', 'app2_1', 'app2_2', 'app2_3', 'app2_4', 'app2_5']}}
    r = used_free_requested(node_name, app_name, dimensions, node_capacities, assigned_apps,
                            apps_spec)
    used, free, requested, capacity, membw_read_write_ratio, metrics = r
    assert used == {rt.CPU: 6, rt.MEM: 6}  # 6 x app2
    assert free == {rt.CPU: 14, rt.MEM: 14}  # 20 - 6 x app2
    assert requested == {rt.CPU: 2, rt.MEM: 2}  # app1 requested
    assert capacity == {rt.CPU: 20, rt.MEM: 20}  # node1 capacity
    assert membw_read_write_ratio is None

    # Assuming app2 is already assigned, do the calculation for app1
    requested_fraction, _ = get_requested_fraction(app_name, apps_spec, assigned_apps,
                                                   node_name,
                                                   node_capacities, dimensions)
    #
    assert requested_fraction == {'cpu': 0.4, 'mem': 0.4}


TEST_DIMENSIONS = set([
    rt.CPU,
    rt.MEM,
    rt.MEMBW_WRITE,
    rt.MEMBW_READ,
])

TEST_APP_SPEC = {
        'memcached-mutilate-big': {
            rt.CPU: 4.,
            rt.MEM: 40.,
            rt.MEMBW_READ: 4.,
            rt.MEMBW_WRITE: 2.
            },
        'memcached-mutilate-medium': {
            rt.CPU: 2.,
            rt.MEM: 20,
            rt.MEMBW_READ: 2.,
            rt.MEMBW_WRITE: 1.
        },
        'memcached-mutilate-small': {
            rt.CPU: 1.,
            rt.MEM: 10.,
            rt.MEMBW_READ: 1.,
            rt.MEMBW_WRITE: .5
            }
}


@pytest.mark.parametrize('dimensions, assigned_apps, apps_spec, expected', [
    (TEST_DIMENSIONS, {}, TEST_APP_SPEC, {'cpu': 0, 'mem': 0, 'membw_read': 0, 'membw_write': 0}),
    (TEST_DIMENSIONS, {'memcached-mutilate-big': 1}, TEST_APP_SPEC,
        {'cpu': 4.0, 'mem': 40.0, 'membw_read': 4.0, 'membw_write': 2.0}),
    (TEST_DIMENSIONS, {'memcached-mutilate-big': 4, 'memcached-mutilate-small': 2}, TEST_APP_SPEC,
        {'cpu': 18.0, 'mem': 180.0, 'membw_read': 18.0, 'membw_write': 9.0}),
])
def test_used_resources_on_node(dimensions, assigned_apps, apps_spec, expected):
    assert used_resources_on_node(dimensions, assigned_apps, apps_spec) == expected


@pytest.mark.parametrize('dimensions, apps_on_node, apps_spec, expected', [
    (TEST_DIMENSIONS, {}, TEST_APP_SPEC, {}),
    (TEST_DIMENSIONS, {
        'node101': {}
        },
        TEST_APP_SPEC, {
        'node101': {'cpu': 0, 'mem': 0, 'membw_read': 0, 'membw_write': 0}
        }),
    (TEST_DIMENSIONS, {
        'node101': {},
        'node102': {'memcached-mutilate-big': ['memcached-mutilate-big-0']}
        },
        TEST_APP_SPEC, {
        'node101': {'cpu': 0, 'mem': 0, 'membw_read': 0, 'membw_write': 0},
        'node102': {'cpu': 4.0, 'mem': 40.0, 'membw_read': 4.0, 'membw_write': 2.0}
        }),
    (TEST_DIMENSIONS, {
        'node101': {},
        'node102': {
            'memcached-mutilate-big': [
                'memcached-mutilate-big-0',
                'memcached-mutilate-big-1',
                'memcached-mutilate-big-2',
                'memcached-mutilate-big-3'],
            'memcached-mutilate-small': [
                'memcached-mutilate-small-0',
                'memcached-mutilate-small-1'],
            }
        },
        TEST_APP_SPEC, {
        'node101': {'cpu': 0, 'mem': 0, 'membw_read': 0, 'membw_write': 0},
        'node102': {'cpu': 18.0, 'mem': 180.0, 'membw_read': 18.0, 'membw_write': 9.0}
        }),
    ])
def test_get_nodes_used_resources(dimensions, apps_on_node, apps_spec, expected):
    assert get_nodes_used_resources(dimensions, apps_on_node, apps_spec) == expected
