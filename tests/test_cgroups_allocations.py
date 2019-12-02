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

import pytest

from unittest.mock import patch, call, Mock

from tests.testing import allocation_metric
from wca.allocators import AllocationConfiguration, AllocationType
from wca.allocations import InvalidAllocations
from wca.cgroups_allocations import (QuotaAllocationValue, SharesAllocationValue,
                                     CPUSetCPUSAllocationValue, CPUSetMEMSAllocationValue,
                                     MigratePagesAllocationValue)
from wca.containers import Container
from wca.metrics import Metric, MetricType
from wca.platforms import Platform, RDTInformation


@patch('wca.perf.PerfCounters')
@patch('wca.cgroups.Cgroup')
def test_cgroup_allocations(Cgroup_mock, PerfCounters_mock):
    rdt_information = RDTInformation(True, True, True, True, '0', '0', 0, 0, 0)

    platform_mock = Mock(
        spec=Platform,
        cpus=10,
        sockets=1,
        rdt_information=rdt_information,
        node_cpus={0: [0, 1], 1: [2, 3]},
    )

    foo_container = Container('/somepath', platform=platform_mock)
    foo_container._cgroup.allocation_configuration = AllocationConfiguration()
    foo_container._cgroup.platform = platform_mock

    quota_allocation_value = QuotaAllocationValue(0.2, foo_container, dict(foo='bar'))
    quota_allocation_value.perform_allocations()
    assert quota_allocation_value.generate_metrics() == [
        allocation_metric('cpu_quota', 0.2, foo='bar')
    ]

    shares_allocation_value = SharesAllocationValue(0.5, foo_container, dict(foo='bar'))
    shares_allocation_value.perform_allocations()

    assert shares_allocation_value.generate_metrics() == [
        allocation_metric('cpu_shares', 0.5, foo='bar')
    ]

    cpuset_cpus_allocation_value = CPUSetCPUSAllocationValue('0-2,4,6-8', foo_container,
                                                             dict(foo='bar'))
    cpuset_cpus_allocation_value.perform_allocations()

    cpuset_mems_allocation_value = CPUSetMEMSAllocationValue('0-1', foo_container, dict(foo='bar'))
    cpuset_mems_allocation_value.perform_allocations()

    assert cpuset_cpus_allocation_value.generate_metrics() == [
        Metric(name='allocation_cpuset_cpus_number_of_cpus', value=7,
               labels={'allocation_type': AllocationType.CPUSET_CPUS, 'foo': 'bar'},
               type=MetricType.GAUGE)
    ]

    assert cpuset_mems_allocation_value.generate_metrics() == [
        Metric(name='allocation_cpuset_mems_number_of_mems', value=2,
               labels={'allocation_type': AllocationType.CPUSET_MEMS, 'foo': 'bar'},
               type=MetricType.GAUGE)
    ]

    Cgroup_mock.assert_has_calls([
        call().set_quota(0.2),
        call().set_shares(0.5),
        call().set_cpuset_cpus({0, 1, 2, 4, 6, 7, 8}),
        call().set_cpuset_mems({0, 1})
    ], True)


@patch('wca.platforms.read_proc_meminfo',
       return_value='SwapCached: 3000kB \nSwapTotal: 123000kB\nSwapFree: 20000kB')
@patch('wca.cgroups.Cgroup')
def test_migrate_pages_raise_exception_when_swap_is_enabled(*mocks):
    rdt_information = RDTInformation(True, True, True, True, '0', '0', 0, 0, 0)

    platform_mock = Mock(
        spec=Platform,
        cpus=10,
        sockets=1,
        rdt_information=rdt_information,
        node_cpus={0: [0, 1], 1: [2, 3]},
        numa_nodes=2,
        swap_enabled=True
    )

    foo_container = Container(
        '/somepath', platform=platform_mock)

    foo_container._cgroup.platform = platform_mock

    migrate_pages = MigratePagesAllocationValue(0, foo_container, dict(foo='bar'))

    with pytest.raises(
            InvalidAllocations,
            match="Swap should be disabled due to possibility of OOM killer occurrence!"):
        migrate_pages.validate()
