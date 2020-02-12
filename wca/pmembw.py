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
import subprocess  # nosec: B404, we deliberately use this module
import shlex

from wca.metrics import MetricName, Measurements

log = logging.getLogger(__name__)


# returns tuple with potential read and write bandwidth in GB/s
# all values are theoretical and might deviate from real
# arguments: power in Watts, number of NVDIMMs in interleave set, size in GB
def _calculate_bandwidth(power, count, size):
    # bandwidth per NVDIMM type:  10W, 12W, 15W, 18W
    # zeroes are where there is no data available
    power_set = (10, 12, 15, 18)
    read_sdp = (2.4, 4.3, 6.8, 0)
    write_sdp = (0.88, 1.48, 1.85, 0)
    read_ddp = (0, 4.1, 6.8, 8.3)
    write_ddp = (0, 1.45, 2.3, 3.0)
    read_qdp = (0, 2.65, 5.3, 7.8)
    write_qdp = (0, 1.02, 1.89, 2.68)

    use_power_index = 0
    for index, it_power in enumerate(power_set):
        if int(power) >= int(it_power):
            use_power_index = index

    # used simplified sizes
    if size < 200:
        read = read_sdp[use_power_index]
        write = write_sdp[use_power_index]
    elif 200 <= size < 500:
        read = read_ddp[use_power_index]
        write = write_ddp[use_power_index]
    else:
        read = read_qdp[use_power_index]
        write = write_qdp[use_power_index]

    read = round(count * read, 2)
    write = round(count * write, 2)
    return read, write


def _get_ipmctl():
    """Execute ipmctl to get platform information"""
    try:
        # nosec: B603. We deliberately use 'subprocess'. There is a permanent input.
        ipmctl_region = subprocess.check_output(  # nosec
            shlex.split('ipmctl show -a -u B -region')).decode("utf-8")
        # typical output. Executing without root yields empty result as there were no pmem modules
        # ---ISetID=0x5876eeb8014a2444---
        #    SocketID=0x0000
        #    PersistentMemoryType=AppDirect
        #    Capacity=541165879296 B
        #    FreeCapacity=541165879296 B
        #    HealthState=Healthy
        #    DimmID=0x0001, 0x0101
        # ---ISetID=0x4e66eeb83e4c2444---
        #    SocketID=0x0001
        #    PersistentMemoryType=AppDirect
        #    Capacity=541165879296 B
        #    FreeCapacity=541165879296 B
        #    HealthState=Healthy
        #    DimmID=0x1001, 0x1101

        # nosec: B603. We deliberately use 'subprocess'. There is a permanent input.
        ipmctl_dimm = subprocess.check_output(  # nosec
            shlex.split('ipmctl show -u B -d '
                        'AvgPowerBudget,Capacity,'
                        'SocketID -dimm')).decode("utf-8")
        # typical output. Executing without root yields empty result as there were no pmem modules
        # ---DimmID=0x0001---
        #    Capacity=271070789632 B
        #    SocketID=0x0000
        #    AvgPowerBudget=15000 mW
        # ---DimmID=0x0101---
        #    Capacity=271070789632 B
        #    SocketID=0x0000
        #    AvgPowerBudget=15000 mW

    except FileNotFoundError as e:
        log.warning('ipmctl unavailable, cannot read memory mode size: %s', e)
        return None, None
    except subprocess.CalledProcessError as e:
        log.warning('ipmctl unavailable (call error), cannot read memory mode size: %s', e)
        return None, None
    return ipmctl_region, ipmctl_dimm


def _get_ipmctl_dimm_info(ipmctl_dimm):
    """Parse information from ipmctl dimm output"""
    socket_nvdimms = dict()
    avg_power_per_nvdimm, capacity_per_nvdimm = None, None
    for line in ipmctl_dimm.split():
        if line.startswith('Capacity'):
            # values should be the same for each nvdimm
            capacity_per_nvdimm = line.split('=')[1]
        elif line.startswith('AvgPowerBudget'):
            # values should be the same for each nvdimm
            avg_power_per_nvdimm = int(line.split('=')[1]) / 1000
        elif line.startswith('SocketID'):
            socket_string = line.split('=')[1]
            if socket_string in socket_nvdimms:
                socket_nvdimms[socket_string] += 1
            else:
                socket_nvdimms[socket_string] = 1
    return avg_power_per_nvdimm, int(capacity_per_nvdimm), socket_nvdimms


def _get_ipmctl_region_info(ipmctl_region):
    """Parse information from ipmctl region output"""
    regions = dict()
    iset_id = ''
    for line in ipmctl_region.replace('   ', '').split('\n'):
        if line.startswith('---ISetID'):
            iset_id = line.split('=')[1].replace('-', '')
            regions[iset_id] = {}
        elif line.startswith(SOCKET):
            regions[iset_id].update({SOCKET: line.split('=')[1]})
        elif line.startswith(CAPACITY):
            regions[iset_id].update(
                {CAPACITY: line.split('=')[1].replace(' B', '')})
        elif line.startswith(DIMM):
            regions[iset_id].update({DIMM: line.split('=')[1].split(', ')})
    return regions


SOCKET = 'SocketID'
CAPACITY = 'Capacity'
DIMM = 'DimmID'


def get_bandwidth() -> Measurements:
    ipmctl_region, ipmctl_dimm = _get_ipmctl()
    if ipmctl_region is None and ipmctl_dimm is None:
        return {}
    measurements = {MetricName.PLATFORM_NVDIMM_READ_BANDWIDTH_BYTES_PER_SECOND: {},
                    MetricName.PLATFORM_NVDIMM_WRITE_BANDWIDTH_BYTES_PER_SECOND: {}}
    avg_power_per_nvdimm, capacity_per_nvdimm, socket_nvdimms = _get_ipmctl_dimm_info(ipmctl_dimm)
    regions = _get_ipmctl_region_info(ipmctl_region)
    GB = 1e9
    capacity_per_nvdimm_in_gigabytes = capacity_per_nvdimm / GB

    def socket_to_label(socket):
        """
        Convert socket representation from hex to decimal.
        example: '0x003' -> '3'
        """
        return str(int(socket, 16))

    for region in regions:
        nvdimm_count = len(regions[region][DIMM])
        rwt = _calculate_bandwidth(avg_power_per_nvdimm, nvdimm_count,
                                   capacity_per_nvdimm_in_gigabytes)

        socket_label = socket_to_label(regions[region][SOCKET])

        measurements[MetricName.PLATFORM_NVDIMM_READ_BANDWIDTH_BYTES_PER_SECOND].update(
            {socket_label: rwt[0] * GB})
        measurements[MetricName.PLATFORM_NVDIMM_WRITE_BANDWIDTH_BYTES_PER_SECOND].update(
            {socket_label: rwt[1] * GB})

    if not regions:
        for socket in socket_nvdimms:
            rwt = _calculate_bandwidth(avg_power_per_nvdimm,
                                       socket_nvdimms[socket],
                                       capacity_per_nvdimm_in_gigabytes)

            socket_label = socket_to_label(socket)

            measurements[MetricName.PLATFORM_NVDIMM_READ_BANDWIDTH_BYTES_PER_SECOND].update(
                {socket_label: rwt[0] * GB})
            measurements[MetricName.PLATFORM_NVDIMM_WRITE_BANDWIDTH_BYTES_PER_SECOND].update(
                {socket_label: rwt[1] * GB})

    measurements[MetricName.PLATFORM_CAPACITY_PER_NVDIMM_BYTES] = capacity_per_nvdimm
    measurements[MetricName.PLATFORM_AVG_POWER_PER_NVDIMM_WATTS] = avg_power_per_nvdimm

    return measurements
