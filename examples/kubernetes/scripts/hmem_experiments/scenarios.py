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
from enum import Enum
from typing import List, Dict


class ExperimentType(Enum):
    DRAM = 'dram'
    PMEM = 'pmem'
    HMEM_NUMA_BALANCING = 'hmem_numa_balancing'
    HMEM_NO_NUMA_BALANCING = 'hmem_no_numa_balancig'
    COLD_START = 'cold_start'
    TOPTIER = 'toptier'
    TOPTIER_WITH_COLDSTART = 'toptier_with_coldstart'


@dataclass
class Scenario:
    name: str
    # List of workload counts in every step of the experiment
    # e.g. [{'workload1': 1}, {'workload1': 3}] means that in first loop
    # workload1 will have one instance and three in the second
    workloads_count: List[Dict[str, int]]
    sleep_duration: int
    experiment_type: ExperimentType
    # If for some reason you do not want to scale workloads to 0 replicas
    # after each step set this flag to false
    reset_workloads_between_steps: bool = True


# ----------------- REDIS WORKLOADS --------------------------
#     ----------------- BIG ----------------
REDIS_MEMTIER_BIG_DRAM = 'redis-memtier-big-dram'
REDIS_MEMTIER_BIG_PMEM = 'redis-memtier-big-pmem'
REDIS_MEMTIER_BIG_DRAM_PMEM = 'redis-memtier-big-dram-pmem'
REDIS_MEMTIER_BIG_COLDSTART_TOPTIER = 'redis-memtier-big-coldstart-toptier'
REDIS_MEMTIER_BIG_TOPTIER = 'redis-memtier-big-toptier'
#     --------------- BIG WSS --------------
REDIS_MEMTIER_BIG_WSS_DRAM = 'redis-memtier-big-wss-dram'
REDIS_MEMTIER_BIG_WSS_PMEM = 'redis-memtier-big-wss-pmem'
REDIS_MEMTIER_BIG_WSS_DRAM_PMEM = 'redis-memtier-big-wss-dram-pmem'
REDIS_MEMTIER_BIG_WSS_COLDSTART_TOPTIER = 'redis-memtier-big-wss-coldstart-toptier'
REDIS_MEMTIER_BIG_WSS_TOPTIER = 'redis-memtier-big-wss-toptier'
#     --------------- MEDIUM ---------------
REDIS_MEMTIER_MEDIUM_COLDSTART_TOPTIER = 'redis-memtier-medium-coldstart-toptier'
REDIS_MEMTIER_MEDIUM_DRAM = 'redis-memtier-medium-dram'
REDIS_MEMTIER_MEDIUM_DRAM_PMEM = 'redis-memtier-medium-dram-pmem'
REDIS_MEMTIER_MEDIUM_PMEM = 'redis-memtier-medium-pmem'
REDIS_MEMTIER_MEDIUM_TOPTIER = 'redis-memtier-medium-toptier'
#     ------------- MEDIUM WSS -------------
REDIS_MEMTIER_MEDIUM_WSS_COLDSTART_TOPTIER = 'redis-memtier-medium-wss-coldstart-toptier'
REDIS_MEMTIER_MEDIUM_WSS_DRAM = 'redis-memtier-medium-wss-dram'
REDIS_MEMTIER_MEDIUM_WSS_DRAM_PMEM = 'redis-memtier-medium-wss-dram-pmem'
REDIS_MEMTIER_MEDIUM_WSS_PMEM = 'redis-memtier-medium-wss-pmem'
REDIS_MEMTIER_MEDIUM_WSS_TOPTIER = 'redis-memtier-medium-wss-toptier'
# ----------------- REDIS SCENARIOS --------------------------
SLEEP_DURATION = 900
WORKLOAD_COUNT = 1

REDIS_SCENARIOS = [
    # Dram redis memtier big
    Scenario(name='redis-memtier-big-dram',
             workloads_count=[{REDIS_MEMTIER_BIG_DRAM: 1}, {REDIS_MEMTIER_BIG_DRAM: 2}],
             sleep_duration=SLEEP_DURATION, experiment_type=ExperimentType.DRAM,
             reset_workloads_between_steps=False),
    # Pmem redis memtier big
    Scenario(name='redis-memtier-big-pmem',
             workloads_count=[{REDIS_MEMTIER_BIG_PMEM: 1}, {REDIS_MEMTIER_BIG_PMEM: 2}],
             sleep_duration=SLEEP_DURATION, experiment_type=ExperimentType.PMEM,
             reset_workloads_between_steps=False),
    # First touch policy redis memtier big
    Scenario(name='redis-memtier-big-first-touch-policy',
             workloads_count=[{REDIS_MEMTIER_BIG_DRAM_PMEM: 1}, {REDIS_MEMTIER_BIG_DRAM_PMEM: 2},
                              {REDIS_MEMTIER_BIG_DRAM_PMEM: 3}, {REDIS_MEMTIER_BIG_DRAM_PMEM: 4}],
             sleep_duration=SLEEP_DURATION, experiment_type=ExperimentType.HMEM_NO_NUMA_BALANCING,
             reset_workloads_between_steps=False),
    # Numa balancing redis memtier big
    Scenario(name='redis-memtier-big-numa-balancing',
             workloads_count=[{REDIS_MEMTIER_BIG_DRAM_PMEM: 4}],
             sleep_duration=SLEEP_DURATION, experiment_type=ExperimentType.HMEM_NUMA_BALANCING),
    # Numa balancing redis memtier big run one by one
    Scenario(name='redis-memtier-big-numa-balancing-one-by-one',
             workloads_count=[{REDIS_MEMTIER_BIG_DRAM_PMEM: 1}, {REDIS_MEMTIER_BIG_DRAM_PMEM: 2},
                              {REDIS_MEMTIER_BIG_DRAM_PMEM: 3}, {REDIS_MEMTIER_BIG_DRAM_PMEM: 4}],
             sleep_duration=SLEEP_DURATION, experiment_type=ExperimentType.HMEM_NUMA_BALANCING,
             reset_workloads_between_steps=False),
    # Toptier limit redis memtier big
    Scenario(name='redis-memtier-big-toptier-limit',
             workloads_count=[{REDIS_MEMTIER_BIG_TOPTIER: 4}],
             sleep_duration=SLEEP_DURATION, experiment_type=ExperimentType.TOPTIER),
    # Toptier limit redis memtier big run one by one
    Scenario(name='redis-memtier-big-toptier-limit-one-by-one',
             workloads_count=[{REDIS_MEMTIER_BIG_TOPTIER: 1}, {REDIS_MEMTIER_BIG_TOPTIER: 2},
                              {REDIS_MEMTIER_BIG_TOPTIER: 3}, {REDIS_MEMTIER_BIG_TOPTIER: 4}],
             sleep_duration=SLEEP_DURATION, experiment_type=ExperimentType.TOPTIER,
             reset_workloads_between_steps=False),
    # Toptier with coldstart redis memtier big
    Scenario(name='redis-memtier-toptier-coldstart',
             workloads_count=[{REDIS_MEMTIER_BIG_COLDSTART_TOPTIER: 4}],
             sleep_duration=SLEEP_DURATION, experiment_type=ExperimentType.TOPTIER_WITH_COLDSTART)
]
REDIS_WSS_SCENARIOS = [
    # Dram redis memtier big wss
    Scenario(name='redis-memtier-big-wss-dram',
             workloads_count=[{REDIS_MEMTIER_BIG_WSS_DRAM: 1}, {REDIS_MEMTIER_BIG_WSS_DRAM: 2}],
             sleep_duration=SLEEP_DURATION, experiment_type=ExperimentType.DRAM,
             reset_workloads_between_steps=False),
    # Pmem redis memtier big wss
    Scenario(name='redis-memtier-big-wss-pmem',
             workloads_count=[{REDIS_MEMTIER_BIG_WSS_PMEM: 1}, {REDIS_MEMTIER_BIG_WSS_PMEM: 2}],
             sleep_duration=SLEEP_DURATION, experiment_type=ExperimentType.PMEM,
             reset_workloads_between_steps=False),
    # First touch policy redis memtier big wss
    Scenario(name='redis-memtier-big-wss-first-touch-policy',
             workloads_count=[{REDIS_MEMTIER_BIG_WSS_DRAM_PMEM: 1},
                              {REDIS_MEMTIER_BIG_WSS_DRAM_PMEM: 2},
                              {REDIS_MEMTIER_BIG_WSS_DRAM_PMEM: 3},
                              {REDIS_MEMTIER_BIG_WSS_DRAM_PMEM: 4}],
             sleep_duration=SLEEP_DURATION, experiment_type=ExperimentType.HMEM_NO_NUMA_BALANCING,
             reset_workloads_between_steps=False),
    # Numa balancing redis memtier big wss
    Scenario(name='redis-memtier-big-wss-numa-balancing',
             workloads_count=[{REDIS_MEMTIER_BIG_WSS_DRAM_PMEM: 4}],
             sleep_duration=SLEEP_DURATION, experiment_type=ExperimentType.HMEM_NUMA_BALANCING),
    # Numa balancing redis memtier big wss run one by one
    Scenario(name='redis-memtier-big-wss-numa-balancing-one-by-one',
             workloads_count=[{REDIS_MEMTIER_BIG_WSS_DRAM_PMEM: 1},
                              {REDIS_MEMTIER_BIG_WSS_DRAM_PMEM: 2},
                              {REDIS_MEMTIER_BIG_WSS_DRAM_PMEM: 3},
                              {REDIS_MEMTIER_BIG_WSS_DRAM_PMEM: 4}],
             sleep_duration=SLEEP_DURATION, experiment_type=ExperimentType.HMEM_NUMA_BALANCING,
             reset_workloads_between_steps=False),
    # Toptier limit redis memtier big wss
    Scenario(name='redis-memtier-big-wss-toptier-limit',
             workloads_count=[{REDIS_MEMTIER_BIG_WSS_TOPTIER: 4}],
             sleep_duration=SLEEP_DURATION, experiment_type=ExperimentType.TOPTIER),
    # Toptier limit redis memtier big wss run one by one
    Scenario(name='redis-memtier-big-wss-toptier-limit-one-by-one',
             workloads_count=[{REDIS_MEMTIER_BIG_WSS_TOPTIER: 1},
                              {REDIS_MEMTIER_BIG_WSS_TOPTIER: 2},
                              {REDIS_MEMTIER_BIG_WSS_TOPTIER: 3},
                              {REDIS_MEMTIER_BIG_WSS_TOPTIER: 4}],
             sleep_duration=SLEEP_DURATION, experiment_type=ExperimentType.TOPTIER,
             reset_workloads_between_steps=False),
    # Toptier with coldstart redis memtier big wss
    Scenario(name='redis-memtier-big-wss-toptier-coldstart',
             workloads_count=[{REDIS_MEMTIER_BIG_WSS_COLDSTART_TOPTIER: 4}],
             sleep_duration=SLEEP_DURATION, experiment_type=ExperimentType.TOPTIER_WITH_COLDSTART)
]
BASE_REDIS_SCENARIOS = [    # Dram redis memtier big
    Scenario(name='redis-memtier-big-dram',
             workloads_count=[{REDIS_MEMTIER_BIG_DRAM: 1}],
             sleep_duration=SLEEP_DURATION, experiment_type=ExperimentType.DRAM),
    # Pmem redis memtier big
    Scenario(name='redis-memtier-big-pmem',
             workloads_count=[{REDIS_MEMTIER_BIG_PMEM: 1}],
             sleep_duration=SLEEP_DURATION, experiment_type=ExperimentType.PMEM),
    # First touch policy redis memtier big
    Scenario(name='redis-memtier-big-first-touch-policy',
             workloads_count=[{REDIS_MEMTIER_BIG_DRAM_PMEM: 1}],
             sleep_duration=SLEEP_DURATION, experiment_type=ExperimentType.HMEM_NO_NUMA_BALANCING,
             reset_workloads_between_steps=False),
    # Numa balancing redis memtier big
    Scenario(name='redis-memtier-big-numa-balancing',
             workloads_count=[{REDIS_MEMTIER_BIG_DRAM_PMEM: 1}],
             sleep_duration=SLEEP_DURATION, experiment_type=ExperimentType.HMEM_NUMA_BALANCING),
    # Toptier limit redis memtier big
    Scenario(name='redis-memtier-big-toptier-limit',
             workloads_count=[{REDIS_MEMTIER_BIG_TOPTIER: 1}],
             sleep_duration=SLEEP_DURATION, experiment_type=ExperimentType.TOPTIER),
    # Toptier with coldstart redis memtier big
    Scenario(name='redis-memtier-toptier-coldstart',
             workloads_count=[{REDIS_MEMTIER_BIG_COLDSTART_TOPTIER: 1}],
             sleep_duration=SLEEP_DURATION, experiment_type=ExperimentType.TOPTIER_WITH_COLDSTART)]

BASE_REDIS_WSS_SCENARIOS = [
    # Dram redis memtier big wss
    Scenario(name='redis-memtier-big-wss-dram',
             workloads_count=[{REDIS_MEMTIER_BIG_WSS_DRAM: 1}],
             sleep_duration=SLEEP_DURATION, experiment_type=ExperimentType.DRAM),
    # Pmem redis memtier big wss
    Scenario(name='redis-memtier-big-wss-pmem',
             workloads_count=[{REDIS_MEMTIER_BIG_WSS_PMEM: 1}],
             sleep_duration=SLEEP_DURATION, experiment_type=ExperimentType.PMEM),
    # First touch policy redis memtier big wss
    Scenario(name='redis-memtier-big-wss-first-touch-policy',
             workloads_count=[{REDIS_MEMTIER_BIG_WSS_DRAM_PMEM: 1}],
             sleep_duration=SLEEP_DURATION, experiment_type=ExperimentType.HMEM_NO_NUMA_BALANCING,
             reset_workloads_between_steps=False),
    # Numa balancing redis memtier big wss
    Scenario(name='redis-memtier-big-wss-numa-balancing',
             workloads_count=[{REDIS_MEMTIER_BIG_WSS_DRAM_PMEM: 1}],
             sleep_duration=SLEEP_DURATION, experiment_type=ExperimentType.HMEM_NUMA_BALANCING),
    # Toptier limit redis memtier big wss
    Scenario(name='redis-memtier-big-wss-toptier-limit',
             workloads_count=[{REDIS_MEMTIER_BIG_WSS_TOPTIER: 1}],
             sleep_duration=SLEEP_DURATION, experiment_type=ExperimentType.TOPTIER),
    # Toptier with coldstart redis memtier big wss
    Scenario(name='redis-memtier-big-wss-toptier-coldstart',
             workloads_count=[{REDIS_MEMTIER_BIG_WSS_COLDSTART_TOPTIER: 1}],
             sleep_duration=SLEEP_DURATION, experiment_type=ExperimentType.TOPTIER_WITH_COLDSTART)]

# ----------------- PMBENCH WORKLOADS --------------------------
#     ----------------- BIG ----------------
PMBENCH_BIG_DRAM = 'pmbench-big-dram'
PMBENCH_BIG_PMEM = 'pmbench-big-pmem'
PMBENCH_BIG_DRAM_PMEM = 'pmbench-big-dram-pmem'
PMBENCH_BIG_COLDSTART_TOPTIER = 'pmbench-big-coldstart-toptier'
PMBENCH_BIG_TOPTIER = 'pmbench-big-toptier'
#     --------------- BIG WSS --------------
PMBENCH_BIG_WSS_DRAM = 'pmbench-big-wss-dram'
PMBENCH_BIG_WSS_PMEM = 'pmbench-big-wss-pmem'
PMBENCH_BIG_WSS_DRAM_PMEM = 'pmbench-big-wss-dram-pmem'
PMBENCH_BIG_WSS_COLDSTART_TOPTIER = 'pmbench-big-wss-coldstart-toptier'
PMBENCH_BIG_WSS_TOPTIER = 'pmbench-big-wss-toptier'
#     --------------- MEDIUM ---------------
PMBENCH_MEDIUM_COLDSTART_TOPTIER = 'pmbench-medium-coldstart-toptier'
PMBENCH_MEDIUM_DRAM = 'pmbench-medium-dram'
PMBENCH_MEDIUM_DRAM_PMEM = 'pmbench-medium-dram-pmem'
PMBENCH_MEDIUM_PMEM = 'pmbench-medium-pmem'
PMBENCH_MEDIUM_TOPTIER = 'pmbench-medium-toptier'
#     ------------- MEDIUM WSS -------------
PMBENCH_MEDIUM_WSS_COLDSTART_TOPTIER = 'pmbench-medium-wss-coldstart-toptier'
PMBENCH_MEDIUM_WSS_DRAM = 'pmbench-medium-wss-dram'
PMBENCH_MEDIUM_WSS_DRAM_PMEM = 'pmbench-medium-wss-dram-pmem'
PMBENCH_MEDIUM_WSS_PMEM = 'pmbench-medium-wss-pmem'
PMBENCH_MEDIUM_WSS_TOPTIER = 'pmbench-medium-wss-toptier'
# ----------------- PMBENCH SCENARIOS --------------------------
SLEEP_DURATION = 900
BASE_PMBENCH_SCENARIOS = [
    Scenario(name='pmbench-big-dram',
             workloads_count=[{PMBENCH_BIG_DRAM: 1}],
             sleep_duration=SLEEP_DURATION, experiment_type=ExperimentType.DRAM),
    # Pmem pmbench big
    Scenario(name='pmbench-big-pmem',
             workloads_count=[{PMBENCH_BIG_PMEM: 1}],
             sleep_duration=SLEEP_DURATION, experiment_type=ExperimentType.PMEM),
    # First touch policy pmbench big
    Scenario(name='pmbench-big-first-touch-policy',
             workloads_count=[{PMBENCH_BIG_DRAM_PMEM: 1}],
             sleep_duration=SLEEP_DURATION, experiment_type=ExperimentType.HMEM_NO_NUMA_BALANCING,
             reset_workloads_between_steps=False),
    # Numa balancing pmbench big
    Scenario(name='pmbench-big-numa-balancing',
             workloads_count=[{PMBENCH_BIG_DRAM_PMEM: 1}],
             sleep_duration=SLEEP_DURATION, experiment_type=ExperimentType.HMEM_NUMA_BALANCING),
    # Toptier limit pmbench big
    Scenario(name='pmbench-big-toptier-limit',
             workloads_count=[{PMBENCH_BIG_TOPTIER: 1}],
             sleep_duration=SLEEP_DURATION, experiment_type=ExperimentType.TOPTIER),
    # Toptier with coldstart pmbench big
    Scenario(name='pmbench-toptier-coldstart',
             workloads_count=[{PMBENCH_BIG_COLDSTART_TOPTIER: 1}],
             sleep_duration=SLEEP_DURATION, experiment_type=ExperimentType.TOPTIER_WITH_COLDSTART)
]

PMBENCH_SCENARIOS = [
    # Dram pmbench big
    Scenario(name='pmbench-big-dram',
             workloads_count=[{PMBENCH_BIG_DRAM: 1}, {PMBENCH_BIG_DRAM: 2}],
             sleep_duration=SLEEP_DURATION, experiment_type=ExperimentType.DRAM,
             reset_workloads_between_steps=False),
    # Pmem pmbench big
    Scenario(name='pmbench-big-pmem',
             workloads_count=[{PMBENCH_BIG_PMEM: 1}, {PMBENCH_BIG_PMEM: 2}],
             sleep_duration=SLEEP_DURATION, experiment_type=ExperimentType.PMEM,
             reset_workloads_between_steps=False),
    # First touch policy pmbench big
    Scenario(name='pmbench-big-first-touch-policy',
             workloads_count=[{PMBENCH_BIG_DRAM_PMEM: 1}, {PMBENCH_BIG_DRAM_PMEM: 2},
                              {PMBENCH_BIG_DRAM_PMEM: 3}, {PMBENCH_BIG_DRAM_PMEM: 4}],
             sleep_duration=SLEEP_DURATION, experiment_type=ExperimentType.HMEM_NO_NUMA_BALANCING,
             reset_workloads_between_steps=False),
    # Numa balancing pmbench big
    Scenario(name='pmbench-big-numa-balancing',
             workloads_count=[{PMBENCH_BIG_DRAM_PMEM: 4}],
             sleep_duration=SLEEP_DURATION, experiment_type=ExperimentType.HMEM_NUMA_BALANCING),
    # Numa balancing pmbench big run one by one
    Scenario(name='pmbench-big-numa-balancing-one-by-one',
             workloads_count=[{PMBENCH_BIG_DRAM_PMEM: 1}, {PMBENCH_BIG_DRAM_PMEM: 2},
                              {PMBENCH_BIG_DRAM_PMEM: 3}, {PMBENCH_BIG_DRAM_PMEM: 4}],
             sleep_duration=SLEEP_DURATION, experiment_type=ExperimentType.HMEM_NUMA_BALANCING,
             reset_workloads_between_steps=False),
    # Toptier limit pmbench big
    Scenario(name='pmbench-big-toptier-limit',
             workloads_count=[{PMBENCH_BIG_TOPTIER: 4}],
             sleep_duration=SLEEP_DURATION, experiment_type=ExperimentType.TOPTIER),
    # Toptier limit pmbench big run one by one
    Scenario(name='pmbench-big-toptier-limit-one-by-one',
             workloads_count=[{PMBENCH_BIG_TOPTIER: 1}, {PMBENCH_BIG_TOPTIER: 2},
                              {PMBENCH_BIG_TOPTIER: 3}, {PMBENCH_BIG_TOPTIER: 4}],
             sleep_duration=SLEEP_DURATION, experiment_type=ExperimentType.TOPTIER,
             reset_workloads_between_steps=False),
    # Toptier with coldstart pmbench big
    Scenario(name='pmbench-toptier-coldstart',
             workloads_count=[{PMBENCH_BIG_COLDSTART_TOPTIER: 4}],
             sleep_duration=SLEEP_DURATION, experiment_type=ExperimentType.TOPTIER_WITH_COLDSTART)
]

# ----------------- MEMCACHCED-MUTILATE WORKLOADS --------------------------
#     ----------------- BIG ----------------
MEMCACHED_MUTILATE_BIG_DRAM = 'memcached-mutilate-big-dram'
MEMCACHED_MUTILATE_BIG_PMEM = 'memcached-mutilate-big-pmem'
MEMCACHED_MUTILATE_BIG_DRAM_PMEM = 'memcached-mutilate-big-dram-pmem'
MEMCACHED_MUTILATE_BIG_COLDSTART_TOPTIER = 'memcached-mutilate-big-coldstart-toptier'
MEMCACHED_MUTILATE_BIG_TOPTIER = 'memcached-mutilate-big-toptier'
#     --------------- BIG WSS --------------
MEMCACHED_MUTILATE_BIG_WSS_DRAM = 'memcached-mutilate-big-wss-dram'
MEMCACHED_MUTILATE_BIG_WSS_PMEM = 'memcached-mutilate-big-wss-pmem'
MEMCACHED_MUTILATE_BIG_WSS_DRAM_PMEM = 'memcached-mutilate-big-wss-dram-pmem'
MEMCACHED_MUTILATE_BIG_WSS_COLDSTART_TOPTIER = 'memcached-mutilate-big-wss-coldstart-toptier'
MEMCACHED_MUTILATE_BIG_WSS_TOPTIER = 'memcached-mutilate-big-wss-toptier'
#     --------------- MEDIUM ---------------
MEMCACHED_MUTILATE_MEDIUM_COLDSTART_TOPTIER = 'memcached-mutilate-medium-coldstart-toptier'
MEMCACHED_MUTILATE_MEDIUM_DRAM = 'memcached-mutilate-medium-dram'
MEMCACHED_MUTILATE_MEDIUM_DRAM_PMEM = 'memcached-mutilate-medium-dram-pmem'
MEMCACHED_MUTILATE_MEDIUM_PMEM = 'memcached-mutilate-medium-pmem'
MEMCACHED_MUTILATE_MEDIUM_TOPTIER = 'memcached-mutilate-medium-toptier'
#     ------------- MEDIUM WSS -------------
MEMCACHED_MUTILATE_MEDIUM_WSS_COLDSTART_TOPTIER = 'memcached-mutilate-medium-wss-coldstart-toptier'
MEMCACHED_MUTILATE_MEDIUM_WSS_DRAM = 'memcached-mutilate-medium-wss-dram'
MEMCACHED_MUTILATE_MEDIUM_WSS_DRAM_PMEM = 'memcached-mutilate-medium-wss-dram-pmem'
MEMCACHED_MUTILATE_MEDIUM_WSS_PMEM = 'memcached-mutilate-medium-wss-pmem'
MEMCACHED_MUTILATE_MEDIUM_WSS_TOPTIER = 'memcached-mutilate-medium-wss-toptier'
# ----------------- MEMCACHED_MUTILATE SCENARIOS --------------------------
SLEEP_DURATION = 900
BASE_MEMCACHED_MUTILATE_SCENARIOS = [
    Scenario(name='memcached-mutilate-big-dram',
             workloads_count=[{MEMCACHED_MUTILATE_BIG_DRAM: 1}],
             sleep_duration=SLEEP_DURATION, experiment_type=ExperimentType.DRAM),
    # Pmem memcached-mutilate big
    Scenario(name='memcached-mutilate-big-pmem',
             workloads_count=[{MEMCACHED_MUTILATE_BIG_PMEM: 1}],
             sleep_duration=SLEEP_DURATION, experiment_type=ExperimentType.PMEM),
    # First touch policy memcached-mutilate big
    Scenario(name='memcached-mutilate-big-first-touch-policy',
             workloads_count=[{MEMCACHED_MUTILATE_BIG_DRAM_PMEM: 1}],
             sleep_duration=SLEEP_DURATION, experiment_type=ExperimentType.HMEM_NO_NUMA_BALANCING,
             reset_workloads_between_steps=False),
    # Numa balancing memcached-mutilate big
    Scenario(name='memcached-mutilate-big-numa-balancing',
             workloads_count=[{MEMCACHED_MUTILATE_BIG_DRAM_PMEM: 1}],
             sleep_duration=SLEEP_DURATION, experiment_type=ExperimentType.HMEM_NUMA_BALANCING),
    # Toptier limit memcached-mutilate big
    Scenario(name='memcached-mutilate-big-toptier-limit',
             workloads_count=[{MEMCACHED_MUTILATE_BIG_TOPTIER: 1}],
             sleep_duration=SLEEP_DURATION, experiment_type=ExperimentType.TOPTIER),
    # Toptier with coldstart memcached-mutilate big
    Scenario(name='memcached-mutilate-toptier-coldstart',
             workloads_count=[{MEMCACHED_MUTILATE_BIG_COLDSTART_TOPTIER: 1}],
             sleep_duration=SLEEP_DURATION, experiment_type=ExperimentType.TOPTIER_WITH_COLDSTART)
]

MEMCACHED_MUTILATE_SCENARIOS = [
    # Dram memcached big
    Scenario(name='memcached-mutilate-big-dram',
             workloads_count=[{MEMCACHED_MUTILATE_BIG_DRAM: 1}, {MEMCACHED_MUTILATE_BIG_DRAM: 2}],
             sleep_duration=SLEEP_DURATION, experiment_type=ExperimentType.DRAM,
             reset_workloads_between_steps=False),
    # Pmem memcached big
    Scenario(name='memcached-mutilate-big-pmem',
             workloads_count=[{MEMCACHED_MUTILATE_BIG_PMEM: 1}, {MEMCACHED_MUTILATE_BIG_PMEM: 2}],
             sleep_duration=SLEEP_DURATION, experiment_type=ExperimentType.PMEM,
             reset_workloads_between_steps=False),
    # First touch policy memcached big
    Scenario(name='memcached-mutilate-big-first-touch-policy',
             workloads_count=[{MEMCACHED_MUTILATE_BIG_DRAM_PMEM: 1},
                              {MEMCACHED_MUTILATE_BIG_DRAM_PMEM: 2},
                              {MEMCACHED_MUTILATE_BIG_DRAM_PMEM: 3},
                              {MEMCACHED_MUTILATE_BIG_DRAM_PMEM: 4}],
             sleep_duration=SLEEP_DURATION, experiment_type=ExperimentType.HMEM_NO_NUMA_BALANCING,
             reset_workloads_between_steps=False),
    # Numa balancing memcached big
    Scenario(name='memcached-mutilate-big-numa-balancing',
             workloads_count=[{MEMCACHED_MUTILATE_BIG_DRAM_PMEM: 4}],
             sleep_duration=SLEEP_DURATION, experiment_type=ExperimentType.HMEM_NUMA_BALANCING),
    # Numa balancing redis memtier big run one by one
    Scenario(name='memcached-mutilate-big-numa-balancing-one-by-one',
             workloads_count=[{MEMCACHED_MUTILATE_BIG_DRAM_PMEM: 1},
                              {MEMCACHED_MUTILATE_BIG_DRAM_PMEM: 2},
                              {MEMCACHED_MUTILATE_BIG_DRAM_PMEM: 3},
                              {MEMCACHED_MUTILATE_BIG_DRAM_PMEM: 4}],
             sleep_duration=SLEEP_DURATION, experiment_type=ExperimentType.HMEM_NUMA_BALANCING,
             reset_workloads_between_steps=False),
    # Toptier limit memcached big
    Scenario(name='memcached-mutilate-big-toptier-limit',
             workloads_count=[{MEMCACHED_MUTILATE_BIG_TOPTIER: 4}],
             sleep_duration=SLEEP_DURATION, experiment_type=ExperimentType.TOPTIER),
    # Toptier limit memcached big run one by one
    Scenario(name='memcached-mutilate-big-toptier-limit-one-by-one',
             workloads_count=[{MEMCACHED_MUTILATE_BIG_TOPTIER: 1},
                              {MEMCACHED_MUTILATE_BIG_TOPTIER: 2},
                              {MEMCACHED_MUTILATE_BIG_TOPTIER: 3},
                              {MEMCACHED_MUTILATE_BIG_TOPTIER: 4}],
             sleep_duration=SLEEP_DURATION, experiment_type=ExperimentType.TOPTIER,
             reset_workloads_between_steps=False),
    # Toptier with coldstart memcached big
    Scenario(name='memcached-mutilate-toptier-coldstart',
             workloads_count=[{MEMCACHED_MUTILATE_BIG_COLDSTART_TOPTIER: 4}],
             sleep_duration=SLEEP_DURATION, experiment_type=ExperimentType.TOPTIER_WITH_COLDSTART)
]
