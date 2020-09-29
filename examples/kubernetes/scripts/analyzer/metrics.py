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

from enum import Enum


class Metric(Enum):
    TASK_THROUGHPUT = 'task_throughput'
    TASK_LATENCY = 'task_latency'

    # platform
    TASK_UP = 'task_up'
    WCA_UP = 'wca_up'
    # POD_SCHEDULED = 'platform_tasks_scheduled'
    PLATFORM_MEM_USAGE = 'platform_mem_usage'
    PLATFORM_CPU_REQUESTED = 'platform_cpu_requested'
    PLATFORM_CPU_UTIL = 'platform_cpu_util'
    PLATFORM_MBW_READS = 'platform_mbw_reads'
    PLATFORM_MBW_WRITES = 'platform_mbw_writes'
    PLATFORM_DRAM_HIT_RATIO = 'platform_dram_hit_ratio'
    PLATFORM_WSS_USED = 'platform_wss_used'
    # hmem
    TASK_MEM_NUMA_PAGES = 'task_mem_numa_pages'


MetricsQueries = {
    Metric.TASK_THROUGHPUT: 'apm_sli2',
    Metric.TASK_LATENCY: 'apm_sli',

    # platform
    Metric.TASK_UP: 'task_up',
    Metric.WCA_UP: 'wca_up',
    # Metric.POD_SCHEDULED: 'wca_tasks',
    Metric.PLATFORM_MEM_USAGE: 'sum(task_requested_mem_bytes) by (nodename) / 1e9',
    Metric.PLATFORM_CPU_REQUESTED: 'sum(task_requested_cpus) by (nodename)',
    # @TODO check if correct (with htop as comparison)
    Metric.PLATFORM_CPU_UTIL: "sum(1-rate(node_cpu_seconds_total{mode='idle'}[10s])) "
                              "by(nodename) / sum(platform_topology_cpus) by (nodename)",
    Metric.PLATFORM_MBW_READS: 'sum(platform_dram_reads_bytes_per_second + '
                               'platform_pmm_reads_bytes_per_second) by (nodename) / 1e9',
    Metric.PLATFORM_MBW_WRITES: 'sum(platform_dram_writes_bytes_per_second + '
                                'platform_pmm_writes_bytes_per_second) by (nodename) / 1e9',
    Metric.PLATFORM_DRAM_HIT_RATIO: 'avg(platform_dram_hit_ratio) by (nodename)',
    Metric.PLATFORM_WSS_USED: 'sum(avg_over_time(task_wss_referenced_bytes[15s])) '
                              'by (nodename) / 1e9',
    # hmem
    Metric.TASK_MEM_NUMA_PAGES: 'task_mem_numa_pages{host="nodename"} * 4096',
}


class Function(Enum):
    AVG = 'avg_over_time'
    QUANTILE = 'quantile_over_time'
    STDEV = 'stddev_over_time'


FunctionsDescription = {
    Function.AVG: 'avg',
    Function.QUANTILE: 'q',
    Function.STDEV: 'stdev',
}
