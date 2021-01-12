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
    TASK_MEM_BANDWIDTH_LOCAL = 'task_mem_bandwidth_local_bytes'
    TASK_MEM_BANDWIDTH_REMOTE = 'task_mem_bandwidth_remote_bytes'
    TASK_MEM_MBW_LOCAL = 'task_mem_bandwidth_local_bytes'
    TASK_MEM_MBW_REMOTE = 'task_mem_bandwidth_remote_bytes'

    # platform
    TASK_UP = 'task_up'
    WCA_UP = 'wca_up'
    # POD_SCHEDULED = 'platform_tasks_scheduled'
    PLATFORM_MEM_USAGE = 'platform_mem_usage'
    PLATFORM_CPU_REQUESTED = 'platform_cpu_requested'
    PLATFORM_CPU_UTIL = 'platform_cpu_util'
    PLATFORM_MBW_READS = 'platform_mbw_reads'
    PLATFORM_MBW_WRITES = 'platform_mbw_writes'
    PLATFORM_WSS_USED = 'platform_wss_used'
    # hmem
    TASK_MEM_NUMA_PAGES = 'task_mem_numa_pages'

    # raw:
    # group 1
    PLATFORM_CAS_COUNT_READS = 'platform_cas_count_reads'
    PLATFORM_CAS_COUNT_WRITES = 'platform_cas_count_writes'
    PLATFORM_PMM_BANDWIDTH_READS = 'platform_pmm_bandwidth_reads'
    PLATFORM_PMM_BANDWIDTH_WRITES = 'platform_pmm_bandwidth_writes'
    # group 2
    PLATFORM_UPI_RXL_FLITS = 'platform_upi_rxl_flits'
    PLATFORM_UPI_TXL_FLITS = 'platform_upi_txl_flits'
    # group 3
    PLATFORM_RPQ_OCCUPANCY = 'platform_rpq_occupancy'
    PLATFORM_RPQ_INSERTS = 'platform_rpq_inserts'
    PLATFORM_IMC_CLOCKTICKS = 'platform_imc_clockticks'

    # derived_metrics
    PLATFORM_PMM_READS_BYTES_PER_SECOND = 'platform_pmm_reads_bytes_per_second'
    PLATFORM_PMM_WRITES_BYTES_PER_SECOND = 'platform_pmm_writes_bytes_per_second'
    PLATFORM_PMM_TOTAL_BYTES_PER_SECOND = 'platform_pmm_total_bytes_per_second'
    PLATFORM_DRAM_READS_BYTES_PER_SECOND = 'platform_dram_reads_bytes_per_second'
    PLATFORM_DRAM_WRITES_BYTES_PER_SECOND = 'platform_dram_writes_bytes_per_second'
    PLATFORM_DRAM_TOTAL_BYTES_PER_SECOND = 'platform_dram_total_bytes_per_second'
    PLATFORM_DRAM_HIT_RATIO = 'platform_dram_hit_ratio'
    PLATFORM_UPI_BANDWIDTH_BYTES_PER_SECOND = 'platform_upi_bandwidth_bytes_per_second'
    PLATFORM_RPQ_READ_LATENCY_SECONDS = 'platform_rpq_read_latency_seconds'

    # vmstat
    PLATFORM_VMSTAT_NUMA_HINT_FAULTS = 'platform_vmstat_numa_hint_faults'
    PLATFORM_VMSTAT_NUMA_HINT_FAULTS_LOCAL = 'platform_vmstat_numa_hint_faults_local'
    PLATFORM_VMSTAT_PGMIGRATE_SUCCESS = 'platform_vmstat_pgmigrate_success'
    PLATFORM_VMSTAT_PGMIGRATE_FAIL = 'platform_vmstat_pgmigrate_fail'

    HMEM_RECLAIM_DEMOTE_SRC_0 = 'hmem_reclaim_demote_src:0'
    HMEM_RECLAIM_DEMOTE_SRC_1 = 'hmem_reclaim_demote_src:1'
    HMEM_RECLAIM_PROMOTE_DST_0 = 'hmem_reclaim_promote_dst:0'
    HMEM_RECLAIM_PROMOTE_DST_1 = 'hmem_reclaim_promote_dst:1'

    NUMA_PAGES_MIGRATED = 'numa_pages_migrated'


platform_metrics = [
    Metric.PLATFORM_PMM_READS_BYTES_PER_SECOND,
    Metric.PLATFORM_PMM_WRITES_BYTES_PER_SECOND,
    Metric.PLATFORM_PMM_TOTAL_BYTES_PER_SECOND,
    Metric.PLATFORM_DRAM_READS_BYTES_PER_SECOND,
    Metric.PLATFORM_DRAM_WRITES_BYTES_PER_SECOND,
    Metric.PLATFORM_DRAM_TOTAL_BYTES_PER_SECOND,
    Metric.PLATFORM_DRAM_HIT_RATIO,
    Metric.PLATFORM_UPI_BANDWIDTH_BYTES_PER_SECOND,
    Metric.PLATFORM_RPQ_READ_LATENCY_SECONDS,
]

migration_platform_metrics = [
    Metric.HMEM_RECLAIM_DEMOTE_SRC_0,
    Metric.HMEM_RECLAIM_DEMOTE_SRC_1,
    Metric.HMEM_RECLAIM_PROMOTE_DST_0,
    Metric.HMEM_RECLAIM_PROMOTE_DST_1,
    Metric.NUMA_PAGES_MIGRATED,
]

MetricLegends = {
    Metric.PLATFORM_PMM_READS_BYTES_PER_SECOND:
        {'unit': 'GB/s', 'helper': '1e9', 'name': 'pmm reads'},
    Metric.PLATFORM_PMM_WRITES_BYTES_PER_SECOND:
        {'unit': 'GB/s', 'helper': '1e9', 'name': 'pmm writes'},
    Metric.PLATFORM_PMM_TOTAL_BYTES_PER_SECOND:
        {'unit': 'GB/s', 'helper': '1e9', 'name': 'pmm total'},
    Metric.PLATFORM_DRAM_READS_BYTES_PER_SECOND:
        {'unit': 'GB/s', 'helper': '1e9', 'name': 'dram reads '},
    Metric.PLATFORM_DRAM_WRITES_BYTES_PER_SECOND:
        {'unit': 'GB/s', 'helper': '1e9', 'name': 'dram writes'},
    Metric.PLATFORM_DRAM_TOTAL_BYTES_PER_SECOND:
        {'unit': 'GB/s', 'helper': '1e9', 'name': 'dram total'},
    Metric.PLATFORM_DRAM_HIT_RATIO:
        {'unit': 'ratio', 'helper': '1', 'name': 'dram hit ratio'},
    Metric.PLATFORM_UPI_BANDWIDTH_BYTES_PER_SECOND:
        {'unit': 'GB/s', 'helper': '1e9', 'name': 'upi bandwidth '},
    Metric.PLATFORM_RPQ_READ_LATENCY_SECONDS:
        {'unit': 'nanosecond', 'helper': '1e-12', 'name': 'rpq read latency'},
    Metric.PLATFORM_VMSTAT_NUMA_HINT_FAULTS:
        {'unit': 'ops', 'helper': '1', 'name': 'vmstat hint faults'},
    Metric.PLATFORM_VMSTAT_NUMA_HINT_FAULTS_LOCAL:
        {'unit': 'ops', 'helper': '1', 'name': 'vmstat hint faults local'},
    Metric.PLATFORM_VMSTAT_PGMIGRATE_SUCCESS:
        {'unit': 'ops', 'helper': '1', 'name': 'vmstat pgmigrate success'},
    Metric.PLATFORM_VMSTAT_PGMIGRATE_FAIL:
        {'unit': 'ops', 'helper': '1', 'name': 'vmstat pgmigrate fail'},
    Metric.NUMA_PAGES_MIGRATED:
        {'unit': 'MB', 'helper': '1e6', 'name': 'numa pages migrated',
         'rate': 'rate(platform_vmstat{'
                 'key="numa_pages_migrated"}[]) * 4096',
         'delta': 'delta(platform_vmstat{'
                  'key="numa_pages_migrated"}[]) * 4096',
         },
    Metric.HMEM_RECLAIM_DEMOTE_SRC_0:
        {'unit': 'MB', 'helper': '1e6', 'name': 'hmem demote_src:0',
         'rate': 'rate(platform_zoneinfo{'
                 'key="hmem_reclaim_demote_src",'
                 'numa_node="0",zone="Normal"}[]) * 4096',
         'delta': 'delta(platform_zoneinfo{'
                  'key="hmem_reclaim_demote_src",'
                  'numa_node="0",zone="Normal"}[]) * 4096',
         },
    Metric.HMEM_RECLAIM_DEMOTE_SRC_1:
        {'unit': 'MB', 'helper': '1e6', 'name': 'hmem demote_src:1',
         'rate': 'rate(platform_zoneinfo{'
                 'key="hmem_reclaim_demote_src",'
                 'numa_node="1",zone="Normal"}[]) * 4096',
         'delta': 'delta(platform_zoneinfo{'
                  'key="hmem_reclaim_demote_src",'
                  'numa_node="1",zone="Normal"}[]) * 4096',
         },
    Metric.HMEM_RECLAIM_PROMOTE_DST_0:
        {'unit': 'MB', 'helper': '1e6', 'name': 'hmem promote_dst:0',
         'rate': 'rate(platform_zoneinfo{'
                 'key="hmem_reclaim_promote_dst",'
                 'numa_node="0",zone="Normal"}[]) * 4096',
         'delta': 'delta(platform_zoneinfo{'
                  'key="hmem_reclaim_promote_dst",'
                  'numa_node="0",zone="Normal"}[]) * 4096',
         },
    Metric.HMEM_RECLAIM_PROMOTE_DST_1:
        {'unit': 'MB', 'helper': '1e6', 'name': 'hmem promote_dst:1',
         'rate': 'rate(platform_zoneinfo{'
                 'key="hmem_reclaim_promote_dst",'
                 'numa_node="1",zone="Normal"}[]) * 4096',
         'delta': 'delta(platform_zoneinfo{'
                  'key="hmem_reclaim_promote_dst",'
                  'numa_node="1",zone="Normal"}[]) * 4096',
         },
}

MetricsQueries = {
    Metric.TASK_THROUGHPUT: 'apm_sli2',
    Metric.TASK_LATENCY: 'apm_sli',
    Metric.TASK_MEM_MBW_LOCAL: 'task_mem_bandwidth_local_bytes',
    Metric.TASK_MEM_MBW_REMOTE: 'task_mem_bandwidth_remote_bytes',

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

    # raw:
    # group 1
    Metric.PLATFORM_CAS_COUNT_READS: 'platform_cas_count_reads',
    Metric.PLATFORM_CAS_COUNT_WRITES: 'platform_cas_count_writes',
    Metric.PLATFORM_PMM_BANDWIDTH_READS: 'platform_pmm_bandwidth_reads',
    Metric.PLATFORM_PMM_BANDWIDTH_WRITES: 'platform_pmm_bandwidth_writes',
    # group 2
    Metric.PLATFORM_UPI_RXL_FLITS: 'platform_upi_rxl_flits',
    Metric.PLATFORM_UPI_TXL_FLITS: 'platform_upi_txl_flits',
    # group 3
    Metric.PLATFORM_RPQ_OCCUPANCY: 'platform_rpq_occupancy',
    Metric.PLATFORM_RPQ_INSERTS: 'platform_rpq_inserts',
    Metric.PLATFORM_IMC_CLOCKTICKS: 'platform_imc_clockticks',

    # derived_metrics
    Metric.PLATFORM_PMM_READS_BYTES_PER_SECOND:
        'sum(platform_pmm_reads_bytes_per_second{}) by (__name__, nodename, socket)',
    Metric.PLATFORM_PMM_WRITES_BYTES_PER_SECOND:
        'sum(platform_pmm_writes_bytes_per_second{}) by (__name__, nodename, socket)',
    Metric.PLATFORM_PMM_TOTAL_BYTES_PER_SECOND:
        'sum(platform_pmm_total_bytes_per_second{}) by (__name__, nodename, socket)',
    Metric.PLATFORM_DRAM_READS_BYTES_PER_SECOND:
        'sum(platform_dram_reads_bytes_per_second{}) by (__name__, nodename, socket)',
    Metric.PLATFORM_DRAM_WRITES_BYTES_PER_SECOND:
        'sum(platform_dram_writes_bytes_per_second{}) by (__name__, nodename, socket)',
    Metric.PLATFORM_DRAM_TOTAL_BYTES_PER_SECOND:
        'sum(platform_dram_total_bytes_per_second{}) by (__name__, nodename, socket)',
    Metric.PLATFORM_DRAM_HIT_RATIO:
        'avg(platform_dram_hit_ratio{}) by (__name__, nodename, socket)',
    Metric.PLATFORM_UPI_BANDWIDTH_BYTES_PER_SECOND:
        'sum(platform_upi_bandwidth_bytes_per_second{}) by (__name__, nodename, socket)',
    Metric.PLATFORM_RPQ_READ_LATENCY_SECONDS:
        'avg(platform_rpq_read_latency_seconds{}) by (__name__, nodename, socket)',

    Metric.PLATFORM_VMSTAT_NUMA_HINT_FAULTS:
        'platform_vmstat_numa_hint_faults',
    Metric.PLATFORM_VMSTAT_NUMA_HINT_FAULTS_LOCAL:
        'platform_vmstat_numa_hint_faults_local',
    Metric.PLATFORM_VMSTAT_PGMIGRATE_SUCCESS:
        'platform_vmstat_pgmigrate_success',
    Metric.PLATFORM_VMSTAT_PGMIGRATE_FAIL:
        'platform_vmstat_pgmigrate_fail',
}


class Function(Enum):
    AVG = 'avg_over_time'
    QUANTILE = 'quantile_over_time'
    STDEV = 'stddev_over_time'
    RATE = 'rate'


FunctionsDescription = {
    Function.AVG: 'avg',
    Function.QUANTILE: 'q',
    Function.STDEV: 'stdev',
    Function.RATE: 'rate'
}
