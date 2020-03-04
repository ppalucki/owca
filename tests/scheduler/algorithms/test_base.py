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
from wca.scheduler.types import ResourceType as rt
from wca.scheduler.algorithms.base import used_resources_on_node, sum_resources, \
    substract_resources, flat_membw_read_write, divide_resources


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
    sub_ = substract_resources(build_resources(cpu=3, mem=3), build_resources(cpu=2, mem=2), 4.0)
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
    assert c[rt.CPU] == 3.0/2.0 and c[rt.MEM] == 3.0/2.0
    assert c[rt.MEMBW_FLAT] == 0.5


def test_used_resources_on_node():
    dimensions = {rt.CPU, rt.MEM}
    assigned_apps_counts = {'stress_ng': 8}
    apps_spec = {'stress_ng': {rt.CPU: 8, rt.MEM: 10}}
    r = used_resources_on_node(dimensions, assigned_apps_counts, apps_spec)
    assert r[rt.CPU] == 64
    assert r[rt.MEM] == 80
