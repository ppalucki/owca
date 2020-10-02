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

from dataclasses import dataclass
from typing import List, Dict

from workload_runner import ExperimentType


@dataclass
class Scenario:
    name: str
    # List of workload counts in every step of the experiment
    # e.g. [{'workload1': 1}, {'workload1': 3}] means that in first loop
    # workload1 will have one instance and three in the second
    workloads_count: List[Dict[str, int]]
    sleep_duration: int
    experiment_type: ExperimentType


# ----------------- REDIS SCENARIOS --------------------------
DRAM_REDIS_MEMTIER = 'redis-memtier-big-wss-dram'
PMEM_REDIS_MEMTIER = 'redis-memtier-big-wss-pmem'
DRAM_PMEM_REDIS_MEMTIER = 'redis-memtier-big-wss-dram-pmem'
DRAM_PMEM_COLDSTART_REDIS_MEMTIER = 'redis-memtier-big-wss-coldstart-toptier'
DRAM_PMEM_TOPTIER_REDIS_MEMTIER = 'redis-memtier-big-wss-toptier'

SLEEP_DURATION = 900
REDIS_SCENARIOS = [
    # Dram redis memtier scenario
    Scenario(name='redis-memtier-dram',
             workloads_count=[{DRAM_REDIS_MEMTIER: x} for x in range(2, 6, 2)],
             sleep_duration=SLEEP_DURATION, experiment_type=ExperimentType.DRAM),
    # PMEM redis memtier scenario
    Scenario(name='redis-memtier-pmem',
             workloads_count=[{PMEM_REDIS_MEMTIER: x} for x in range(2, 6, 2)],
             sleep_duration=SLEEP_DURATION, experiment_type=ExperimentType.PMEM),
    # Mixed redis memtier scenario with numa balancing
    Scenario(name='redis-memtier-hmem-numa-balancing',
             workloads_count=[{DRAM_PMEM_REDIS_MEMTIER: x} for x in range(2, 6, 2)],
             sleep_duration=SLEEP_DURATION, experiment_type=ExperimentType.HMEM_NUMA_BALANCING),
    # Mixed redis memtier scenario without numa balancing
    Scenario(name='redis-memtier-hmem-no-numa-balancing',
             workloads_count=[{DRAM_PMEM_REDIS_MEMTIER: x} for x in range(2, 6, 2)],
             sleep_duration=SLEEP_DURATION, experiment_type=ExperimentType.HMEM_NO_NUMA_BALANCING),
    # Mixed toptier redis memier scenario
    Scenario(name='redis-memtier-toptier',
             workloads_count=[{DRAM_PMEM_TOPTIER_REDIS_MEMTIER: x} for x in range(2, 6, 2)],
             sleep_duration=SLEEP_DURATION, experiment_type=ExperimentType.TOPTIER),
    # Mixed coldstart-toptier redis memtier scenario
    Scenario(name='redis-memtier-coldstart-toptier',
             workloads_count=[{DRAM_PMEM_COLDSTART_REDIS_MEMTIER: x} for x in range(2, 6, 2)],
             sleep_duration=SLEEP_DURATION, experiment_type=ExperimentType.TOPTIER_WITH_COLDSTART)
]

# ----------------- MEMCACHED SCENARIOS --------------------------
DRAM_MEMCACHED_MUTILATE = 'h-dram-memcached-mutilate-big'
PMEM_MEMCACHED_MUTILATE = 'h-pmem-memcached-mutilate-big'
DRAM_PMEM_MEMCACHED_MUTILATE = 'h-mix-memcached-mutilate-big'

MEMCACHED_SCENARIOS = [
    # dram scenario
    Scenario(name='memcached-mutilate-dram',
             workloads_count=[{DRAM_MEMCACHED_MUTILATE: x} for x in range(2, 6, 2)],
             sleep_duration=SLEEP_DURATION, experiment_type=ExperimentType.DRAM),
    # pmem scenario
    Scenario(name='memcached-mutilate-pmem',
             workloads_count=[{PMEM_MEMCACHED_MUTILATE: x} for x in range(2, 6, 2)],
             sleep_duration=SLEEP_DURATION, experiment_type=ExperimentType.PMEM),
    # Mixed scenario
    Scenario(name='memcached-mutilate-hmem-numa-balancing',
             workloads_count=[{DRAM_PMEM_MEMCACHED_MUTILATE: x} for x in range(2, 6, 2)],
             sleep_duration=SLEEP_DURATION, experiment_type=ExperimentType.HMEM_NUMA_BALANCING)
]
