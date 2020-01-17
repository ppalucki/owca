# Copyright (c) 2018 Intel Corporation
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

from wca.pmembw import _get_ipmctl_dimm_info, _get_ipmctl_region_info, \
    get_bandwidth, _calculate_bandwidth

from unittest.mock import patch


def test_get_ipmctl_dimm_info():
    with open('tests/fixtures/ipmctl_dimm.txt') as dimm:
        ipmctl_dimm = dimm.read()
        avg_power_per_nvdimm, capacity_per_nvdimm, socket_nvdimms = \
            _get_ipmctl_dimm_info(ipmctl_dimm)
        assert avg_power_per_nvdimm == 15.0
        assert capacity_per_nvdimm == 1000000
        assert socket_nvdimms == {'0x0000': 2, '0x0001': 2}


def test_get_ipmctl_region_info():
    with open('tests/fixtures/ipmctl_region.txt') as region:
        ipmctl_region = region.read()
        region = {
            '0x1234abc5678d9012':
                {'SocketID': '0x0000',
                 'Capacity': '5000000',
                 'DimmID': ['0x0001', '0x0101']},
            '0x1234abc5678d9013':
                {'SocketID': '0x0001',
                 'Capacity': '5000000',
                 'DimmID': ['0x1001', '0x1101']}}
        assert region == _get_ipmctl_region_info(ipmctl_region)


@patch('wca.pmembw._get_ipmctl',
       return_value=(
               open('tests/fixtures/bandwidth_ipmctl_region.txt').read(),
               open('tests/fixtures/bandwidth_ipmctl_dimm.txt').read()))
def test_get_bandwidth(*mock):
    measurements = {'platform_nvdimm_read_bandwidth_bytes_per_second':
                    {'0x0000': 136000000000, '0x0001': 136000000000},
                    'platform_nvdimm_write_bandwidth_bytes_per_second':
                    {'0x0000': 37000000000, '0x0001': 37000000000},
                    'platform_capacity_per_nvdimm_bytes': 100000000000,
                    'platform_avg_power_per_nvdimm_watts': 15.0}
    assert measurements == get_bandwidth()


@pytest.mark.parametrize('power,count,size,expected', [
    (15.0, 2, 20, (13.6, 3.7)),
    (15.0, 2, 201, (13.6, 4.6)),
    (15.0, 2, 500, (10.6, 3.78))
])
def test_calculate_bandwidth(power, count, size, expected):
    assert expected == _calculate_bandwidth(power, count, size)
