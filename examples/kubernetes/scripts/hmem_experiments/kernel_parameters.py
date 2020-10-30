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
import subprocess

NUMA_BALANCING_FILE = '/proc/sys/kernel/numa_balancing'
TOPTIER_BALANCING_FILE = '/proc/sys/vm/toptier_scale_factor'

NUMA_BALANCING_HOT_THRESHOLD = '/proc/sys/kernel/numa_balancing_hot_threshold_ms'
NUMA_BALANCING_RATE_LIMIT = '/proc/sys/kernel/numa_balancing_rate_limit_mbps'
NUMA_BALANCING_SCAN_DELAY = '/proc/sys/kernel/numa_balancing_scan_delay_ms'
NUMA_BALANCING_SCAN_PERIOD_MAX = '/proc/sys/kernel/numa_balancing_scan_period_max_ms'
NUMA_BALANCING_SCAN_PERIOD_MIN = '/proc/sys/kernel/numa_balancing_scan_period_min_ms'
NUMA_BALANCING_SCAN_SIZE = '/proc/sys/kernel/numa_balancing_scan_size_mb'

TRACING_ON = '/sys/kernel/debug/tracing/tracing_on'
MIGRATION_PATH_NODE_0 = '/sys/devices/system/node/node0/migration_path'
MIGRATION_PATH_NODE_1 = '/sys/devices/system/node/node1/migration_path'

DEMOTION_RATELIMIT = '/proc/sys/vm/demotion_ratelimit_mbytes_per_sec'
PROMOTION_RATELIMIT = '/proc/sys/vm/promotion_ratelimit_mbytes_per_sec'

PARAMETER_VALUES = {NUMA_BALANCING_HOT_THRESHOLD: '1000',
                    NUMA_BALANCING_RATE_LIMIT: '0',
                    NUMA_BALANCING_SCAN_DELAY: '1000',
                    NUMA_BALANCING_SCAN_PERIOD_MAX: '60000',
                    NUMA_BALANCING_SCAN_PERIOD_MIN: '1000',
                    NUMA_BALANCING_SCAN_SIZE: '256',
                    TRACING_ON: '0',
                    MIGRATION_PATH_NODE_0: '2',
                    MIGRATION_PATH_NODE_1: '3'}


def check_if_pmem_nodes_are_present():
    numactl = subprocess.run(["numactl", "-H"], stdout=subprocess.PIPE)
    numactl_output = str(numactl.stdout)
    assert 'node 2' in numactl_output, 'Node 2 is missing!'
    assert 'node 3' in numactl_output, 'Node 3 is missing!'
    logging.debug('>>PMEM nodes found<<')


def set_necessary_parameters():
    for file_name, value in PARAMETER_VALUES.items():
        with open(file_name, 'w') as file:
            file.write(value)


def show_frequency():
    frequency = subprocess.run(['lscpu | grep \'CPU MHz\''], stdout=subprocess.PIPE, shell=True)
    logging.debug('Frequency: {}'.format(str(frequency.stdout)))


def set_numa_balancing(turned_on=True):
    numa_balancing_value = '2'
    if not turned_on:
        numa_balancing_value = '0'
    with open(NUMA_BALANCING_FILE, 'w') as numa_balancing_file:
        numa_balancing_file.write(numa_balancing_value)


def set_toptier_scale_factor(value='2000'):
    '''Set toptier scale factor in /proc/sys/vm/toptier_scale_factor
       file. The default kernel value for this file is 2000.'''
    with open(TOPTIER_BALANCING_FILE, 'w') as toptier_scale_factor_file:
        toptier_scale_factor_file.write(value)
