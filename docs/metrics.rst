
================================
Available metrics
================================

**This software is pre-production and should not be deployed to production servers.**

.. contents:: Table of Contents


Metrics sources
===============

Check out `metrics sources documentation <metrics_sources.rst>`_  to learn how measurement them.

Task's metrics
==============

.. csv-table::
	:header: "Name", "Help", "Source", "Levels"
	:widths: auto

	"instructions[MetricUnit.NUMERIC] (MetricType.COUNTER)", "Linux Perf counter for instructions per container.", "perf event", "cpu"
	"cycles[MetricUnit.NUMERIC] (MetricType.COUNTER)", "Linux Perf counter for cycles per container.", "perf event", "cpu"
	"cache_misses[MetricUnit.NUMERIC] (MetricType.COUNTER)", "Linux Perf counter for cache-misses per container.", "perf event", "cpu"
	"cpu_usage_per_cpu[MetricUnit.TEN_MILLISECOND] (MetricType.COUNTER)", "Logical CPU usage in 1/USER_HZ (usually 10ms).Calculated using values based on /proc/stat.", "/proc", "cpu"
	"cpu_usage_per_task[MetricUnit.NUMERIC] (MetricType.COUNTER)", "cpuacct.usage (total kernel and user space).", "cgroup", ""
	"memory_bandwidth[MetricUnit.BYTES] (MetricType.COUNTER)", "Total memory bandwidth using Memory Bandwidth Monitoring.", "resctrl", ""
	"memory_usage_per_task_bytes[MetricUnit.BYTES] (MetricType.GAUGE)", "Memory usage_in_bytes per tasks returned from cgroup memory subsystem.", "cgroup", ""
	"memory_max_usage_per_task_bytes[MetricUnit.BYTES] (MetricType.GAUGE)", "Memory max_usage_in_bytes per tasks returned from cgroup memory subsystem.", "cgroup", ""
	"memory_limit_per_task_bytes[MetricUnit.BYTES] (MetricType.GAUGE)", "Memory limit_in_bytes per tasks returned from cgroup memory subsystem.", "cgroup", ""
	"memory_soft_limit_per_task_bytes[MetricUnit.BYTES] (MetricType.GAUGE)", "Memory soft_limit_in_bytes per tasks returned from cgroup memory subsystem.", "cgroup", ""
	"llc_occupancy[MetricUnit.BYTES] (MetricType.GAUGE)", "LLC occupancy.", "resctrl", ""
	"stalls_mem_load[MetricUnit.NUMERIC] (MetricType.COUNTER)", "Mem stalled loads.", "perf event", "cpu"
	"cache_references[MetricUnit.NUMERIC] (MetricType.COUNTER)", "Cache references.", "perf event", "cpu"
	"memory_numa_stat[MetricUnit.NUMERIC] (MetricType.GAUGE)", "NUMA Stat TODO!", "cgroup", "numa_node"
	"memory_bandwidth_local[MetricUnit.BYTES] (MetricType.COUNTER)", "Total local memory bandwidth using Memory Bandwidth Monitoring.", "resctrl", ""
	"memory_bandwidth_remote[MetricUnit.BYTES] (MetricType.COUNTER)", "Total remote memory bandwidth using Memory Bandwidth Monitoring.", "resctrl", ""
	"offcore_requests_l3_miss_demand_data_rd[MetricUnit.NUMERIC] (MetricType.COUNTER)", "Increment each cycle of the number of offcore outstanding demand data read requests from SQ that missed L3.", "perf event", ""
	"offcore_requests_outstanding_l3_miss_demand_data_rd[MetricUnit.NUMERIC] (MetricType.COUNTER)", "Demand data read requests that missed L3.", "perf event", ""
	"cpus[MetricUnit.NUMERIC] (MetricType.GAUGE)", "Tasks resources cpus initial requests.", "generic", ""
	"mem[MetricUnit.NUMERIC] (MetricType.GAUGE)", "Tasks resources memory initial requests.", "generic", ""
	"last_seen[MetricUnit.NUMERIC] (MetricType.COUNTER)", "Time the task was last seen.", "generic", ""
	"ipc[MetricUnit.NUMERIC] (MetricType.GAUGE)", "Instructions per cycle.", "derived", ""
	"ips[MetricUnit.NUMERIC] (MetricType.GAUGE)", "Instructions per second.", "derived", ""
	"cache_hit_ratio[MetricUnit.NUMERIC] (MetricType.GAUGE)", "Cache hit ratio, based on cache-misses and cache-references.", "derived", ""
	"cache_misses_per_kilo_instructions[MetricUnit.NUMERIC] (MetricType.GAUGE)", "Cache misses per kilo instructions.", "derived", ""
	"memstalls__ra310[MetricUnit.NUMERIC] (MetricType.COUNTER)", "Memory stalls...", "perf event", "cpu"
	"mem_load_retired_local_pmm__rd180[MetricUnit.NUMERIC] (MetricType.COUNTER)", "mem_load_retired_local_pmm__rd180", "perf event", "cpu"
	"mem_inst_retired_all_loads__rd081[MetricUnit.NUMERIC] (MetricType.COUNTER)", "mem_load_retired_local_pmm__rd180", "perf event", "cpu"
	"mem_inst_retired_all_stores__rd082[MetricUnit.NUMERIC] (MetricType.COUNTER)", "TODO:", "perf event", "cpu"
	"dtlb_load_misses__r080e[MetricUnit.NUMERIC] (MetricType.COUNTER)", "TBD", "perf event", "cpu"



Platform's metrics
==================

.. csv-table::
	:header: "Name", "Help", "Source", "Levels"
	:widths: auto

	"memory_usage[MetricUnit.BYTES] (MetricType.GAUGE)", "Total memory used by platform in bytes based on /proc/meminfo and uses heuristic based on linux free tool (total - free - buffers - cache).", "/proc", ""
	"scaling_factor_max[MetricUnit.NUMERIC] (MetricType.GAUGE)", "Perf metric scaling factor, MAX value.", "perf event", ""
	"scaling_factor_avg[MetricUnit.NUMERIC] (MetricType.GAUGE)", "Perf metric scaling factor, average from all CPUs.", "perf event", ""
	"memory_stat_page_faults[MetricUnit.NUMERIC] (MetricType.COUNTER)", "Page faults", "cgroup", ""
	"memory_numa_free[MetricUnit.NUMERIC] (MetricType.GAUGE)", "NUMA memory free per numa node TODO!", "/proc", "numa_node"
	"memory_numa_used[MetricUnit.NUMERIC] (MetricType.GAUGE)", "NUMA memory used per numa node TODO!", "/proc", "numa_node"
	"pmm_bandwidth_read[MetricUnit.NUMERIC] (MetricType.COUNTER)", "Persistent memory module number of reads.", "perf event", "cpu pmu"
	"pmm_bandwidth_write[MetricUnit.NUMERIC] (MetricType.COUNTER)", "Persistent memory module number of writes.", "perf event", "cpu pmu"
	"cas_count_read[MetricUnit.NUMERIC] (MetricType.COUNTER)", "Column adress select number of reads", "perf event", "cpu pmu"
	"cas_count_write[MetricUnit.NUMERIC] (MetricType.COUNTER)", "Column adress select number of writes", "perf event", "cpu pmu"
	"pmm_reads_mb_per_second[MetricUnit.NUMERIC] (MetricType.GAUGE)", "TBD", "derived", "cpu pmu"
	"pmm_writes_mb_per_second[MetricUnit.NUMERIC] (MetricType.GAUGE)", "TBD", "derived", "cpu pmu"
	"pmm_total_mb_per_second[MetricUnit.NUMERIC] (MetricType.GAUGE)", "TBD", "derived", "cpu pmu"
	"dram_reads_mb_per_second[MetricUnit.NUMERIC] (MetricType.GAUGE)", "TBD", "derived", "cpu pmu"
	"dram_writes_mb_per_second[MetricUnit.NUMERIC] (MetricType.GAUGE)", "TBD", "derived", "cpu pmu"
	"dram_total_mb_per_second[MetricUnit.NUMERIC] (MetricType.GAUGE)", "TBD", "perf event", "cpu pmu"
	"dram_hit[MetricUnit.NUMERIC] (MetricType.GAUGE)", "TBD", "derived", "cpu pmu"
	"upi_txl_flits[MetricUnit.NUMERIC] (MetricType.COUNTER)", "TBD", "perf event", "cpu pmu"
	"upi_rxl_flits[MetricUnit.NUMERIC] (MetricType.COUNTER)", "TBD", "perf event", "cpu pmu"
	"upi_bandwidth_mb_per_second[MetricUnit.NUMERIC] (MetricType.COUNTER)", "TBD", "derived", "cpu pmu"



Internal metrics
================

.. csv-table::
	:header: "Name", "Help", "Source", "Levels"
	:widths: auto

	"up[MetricUnit.NUMERIC] (MetricType.COUNTER)", "Time the WCA was last seen.", "internal", ""
	"up[MetricUnit.NUMERIC] (MetricType.COUNTER)", "Time the WCA was last seen.", "internal", ""

