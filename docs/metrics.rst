
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
	:widths: 5, 5, 5, 5 

	"instructions [numeric/counter]", "Linux Perf counter for instructions per container.", "perf event", "cpu"
	"cycles [numeric/counter]", "Linux Perf counter for cycles per container.", "perf event", "cpu"
	"cache_misses [numeric/counter]", "Linux Perf counter for cache-misses per container.", "perf event", "cpu"
	"cpu_usage_per_cpu [10ms/counter]", "Logical CPU usage in 1/USER_HZ (usually 10ms).Calculated using values based on /proc/stat.", "/proc", "cpu"
	"cpu_usage_per_task [numeric/counter]", "cpuacct.usage (total kernel and user space).", "cgroup", ""
	"memory_bandwidth [bytes/counter]", "Total memory bandwidth using Memory Bandwidth Monitoring.", "resctrl", ""
	"memory_usage_per_task_bytes [bytes/gauge]", "Memory usage_in_bytes per tasks returned from cgroup memory subsystem.", "cgroup", ""
	"memory_max_usage_per_task_bytes [bytes/gauge]", "Memory max_usage_in_bytes per tasks returned from cgroup memory subsystem.", "cgroup", ""
	"memory_limit_per_task_bytes [bytes/gauge]", "Memory limit_in_bytes per tasks returned from cgroup memory subsystem.", "cgroup", ""
	"memory_soft_limit_per_task_bytes [bytes/gauge]", "Memory soft_limit_in_bytes per tasks returned from cgroup memory subsystem.", "cgroup", ""
	"llc_occupancy [bytes/gauge]", "LLC occupancy.", "resctrl", ""
	"stalls_mem_load [numeric/counter]", "Mem stalled loads.", "perf event", "cpu"
	"cache_references [numeric/counter]", "Cache references.", "perf event", "cpu"
	"memory_numa_stat [numeric/gauge]", "NUMA Stat TODO!", "cgroup", "numa_node"
	"memory_bandwidth_local [bytes/counter]", "Total local memory bandwidth using Memory Bandwidth Monitoring.", "resctrl", ""
	"memory_bandwidth_remote [bytes/counter]", "Total remote memory bandwidth using Memory Bandwidth Monitoring.", "resctrl", ""
	"offcore_requests_l3_miss_demand_data_rd [numeric/counter]", "Increment each cycle of the number of offcore outstanding demand data read requests from SQ that missed L3.", "perf event", ""
	"offcore_requests_outstanding_l3_miss_demand_data_rd [numeric/counter]", "Demand data read requests that missed L3.", "perf event", ""
	"cpus [numeric/gauge]", "Tasks resources cpus initial requests.", "generic", ""
	"mem [numeric/gauge]", "Tasks resources memory initial requests.", "generic", ""
	"last_seen [numeric/counter]", "Time the task was last seen.", "generic", ""
	"ipc [numeric/gauge]", "Instructions per cycle.", "derived", ""
	"ips [numeric/gauge]", "Instructions per second.", "derived", ""
	"cache_hit_ratio [numeric/gauge]", "Cache hit ratio, based on cache-misses and cache-references.", "derived", ""
	"cache_misses_per_kilo_instructions [numeric/gauge]", "Cache misses per kilo instructions.", "derived", ""
	"memstalls__ra310 [numeric/counter]", "Memory stalls...", "perf event", "cpu"
	"mem_load_retired_local_pmm__rd180 [numeric/counter]", "mem_load_retired_local_pmm__rd180", "perf event", "cpu"
	"mem_inst_retired_all_loads__rd081 [numeric/counter]", "mem_load_retired_local_pmm__rd180", "perf event", "cpu"
	"mem_inst_retired_all_stores__rd082 [numeric/counter]", "TODO:", "perf event", "cpu"
	"dtlb_load_misses__r080e [numeric/counter]", "TBD", "perf event", "cpu"



Platform's metrics
==================

.. csv-table::
	:header: "Name", "Help", "Source", "Levels"
	:widths: 5, 5, 5, 5 

	"memory_usage [bytes/gauge]", "Total memory used by platform in bytes based on /proc/meminfo and uses heuristic based on linux free tool (total - free - buffers - cache).", "/proc", ""
	"scaling_factor_max [numeric/gauge]", "Perf metric scaling factor, MAX value.", "perf event", ""
	"scaling_factor_avg [numeric/gauge]", "Perf metric scaling factor, average from all CPUs.", "perf event", ""
	"memory_stat_page_faults [numeric/counter]", "Page faults", "cgroup", ""
	"memory_numa_free [numeric/gauge]", "NUMA memory free per numa node TODO!", "/proc", "numa_node"
	"memory_numa_used [numeric/gauge]", "NUMA memory used per numa node TODO!", "/proc", "numa_node"
	"pmm_bandwidth_read [numeric/counter]", "Persistent memory module number of reads.", "perf event", "cpu, pmu"
	"pmm_bandwidth_write [numeric/counter]", "Persistent memory module number of writes.", "perf event", "cpu, pmu"
	"cas_count_read [numeric/counter]", "Column adress select number of reads", "perf event", "cpu, pmu"
	"cas_count_write [numeric/counter]", "Column adress select number of writes", "perf event", "cpu, pmu"
	"pmm_reads_mb_per_second [numeric/gauge]", "TBD", "derived", "cpu, pmu"
	"pmm_writes_mb_per_second [numeric/gauge]", "TBD", "derived", "cpu, pmu"
	"pmm_total_mb_per_second [numeric/gauge]", "TBD", "derived", "cpu, pmu"
	"dram_reads_mb_per_second [numeric/gauge]", "TBD", "derived", "cpu, pmu"
	"dram_writes_mb_per_second [numeric/gauge]", "TBD", "derived", "cpu, pmu"
	"dram_total_mb_per_second [numeric/gauge]", "TBD", "perf event", "cpu, pmu"
	"dram_hit [numeric/gauge]", "TBD", "derived", "cpu, pmu"
	"upi_txl_flits [numeric/counter]", "TBD", "perf event", "cpu, pmu"
	"upi_rxl_flits [numeric/counter]", "TBD", "perf event", "cpu, pmu"
	"upi_bandwidth_mb_per_second [numeric/counter]", "TBD", "derived", "cpu, pmu"



Internal metrics
================

.. csv-table::
	:header: "Name", "Help", "Source", "Levels"
	:widths: 5, 5, 5, 5 

	"up [numeric/counter]", "Time the WCA was last seen.", "internal", ""
	"up [numeric/counter]", "Time the WCA was last seen.", "internal", ""

