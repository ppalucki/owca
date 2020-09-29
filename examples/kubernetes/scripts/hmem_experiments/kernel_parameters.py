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

NUMA_BALANCING_FILE = '/proc/sys/kernel/numa_balancing'
TOPTIER_BALANCING_FILE = '/proc/sys/vm/toptier_scale_factor'


def set_numa_balancing(turned_on=True):
    numa_balancing_value = '2'
    if not turned_on:
        numa_balancing_value = '1'
    with open(NUMA_BALANCING_FILE, 'w') as numa_balancing_file:
        numa_balancing_file.write(numa_balancing_value)


def set_toptier_scale_factor(value='2000'):
    with open(TOPTIER_BALANCING_FILE, 'w') as toptier_scale_factor_file:
        toptier_scale_factor_file.write(value)
