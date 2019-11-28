
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
	:header: "Name", "Help", "Source", "Levels/Labels"
	:widths: 5, 5, 5, 5 

		:width: 90% 

	"instructions", "Linux Perf counter for instructions per container. [numeric](counter)", "perf event", "cpu"
	"cycles", "Linux Perf counter for cycles per container. [numeric](counter)", "perf event", "cpu"
	"cache_misses", "Linux Perf counter for cache-misses per container. [numeric](counter)", "perf event", "cpu"
	"cpu_usage_per_cpu", "Logical CPU usage in 1/USER_HZ (usually 10ms).Calculated using values based on /proc/stat. [10ms](counter)", "/proc", "cpu"
	"cpu_usage_per_task", "cpuacct.usage (total kernel and user space). [numeric](counter)", "cgroup", ""
	"memory_bandwidth", "Total memory bandwidth using Memory Bandwidth Monitoring. [bytes](counter)", "resctrl", ""
	"memory_usage_per_task_bytes", "Memory usage_in_bytes per tasks returned from cgroup memory subsystem. [bytes](gauge)", "cgroup", ""
	"memory_max_usage_per_task_bytes", "Memory max_usage_in_bytes per tasks returned from cgroup memory subsystem. [bytes](gauge)", "cgroup", ""
	"memory_limit_per_task_bytes", "Memory limit_in_bytes per tasks returned from cgroup memory subsystem. [bytes](gauge)", "cgroup", ""
	"memory_soft_limit_per_task_bytes", "Memory soft_limit_in_bytes per tasks returned from cgroup memory subsystem. [bytes](gauge)", "cgroup", ""
	"llc_occupancy", "LLC occupancy. [bytes](gauge)", "resctrl", ""
	"stalls_mem_load", "Mem stalled loads. [numeric](counter)", "perf event", "cpu"
	"cache_references", "Cache references. [numeric](counter)", "perf event", "cpu"
	"memory_numa_stat", "NUMA Stat TODO! [numeric](gauge)", "cgroup", "numa_node"
	"memory_bandwidth_local", "Total local memory bandwidth using Memory Bandwidth Monitoring. [bytes](counter)", "resctrl", ""
	"memory_bandwidth_remote", "Total remote memory bandwidth using Memory Bandwidth Monitoring. [bytes](counter)", "resctrl", ""
	"offcore_requests_l3_miss_demand_data_rd", "Increment each cycle of the number of offcore outstanding demand data read requests from SQ that missed L3. [numeric](counter)", "perf event", ""
	"offcore_requests_outstanding_l3_miss_demand_data_rd", "Demand data read requests that missed L3. [numeric](counter)", "perf event", ""
	"cpus", "Tasks resources cpus initial requests. [numeric](gauge)", "generic", ""
	"mem", "Tasks resources memory initial requests. [numeric](gauge)", "generic", ""
	"last_seen", "Time the task was last seen. [numeric](counter)", "generic", ""
	"ipc", "Instructions per cycle. [numeric](gauge)", "derived", ""
	"ips", "Instructions per second. [numeric](gauge)", "derived", ""
	"cache_hit_ratio", "Cache hit ratio, based on cache-misses and cache-references. [numeric](gauge)", "derived", ""
	"cache_misses_per_kilo_instructions", "Cache misses per kilo instructions. [numeric](gauge)", "derived", ""
	"memstalls__ra310", "Memory stalls... [numeric](counter)", "perf event", "cpu"
	"mem_load_retired_local_pmm__rd180", "mem_load_retired_local_pmm__rd180 [numeric](counter)", "perf event", "cpu"
	"mem_inst_retired_all_loads__rd081", "mem_load_retired_local_pmm__rd180 [numeric](counter)", "perf event", "cpu"
	"mem_inst_retired_all_stores__rd082", "TODO: [numeric](counter)", "perf event", "cpu"
	"dtlb_load_misses__r080e", "TBD [numeric](counter)", "perf event", "cpu"



Platform's metrics
==================

.. csv-table::
	:header: "Name", "Help", "Source", "Levels/Labels"
	:widths: 5, 5, 5, 5 

		:width: 90% 

	"memory_usage", "Total memory used by platform in bytes based on /proc/meminfo and uses heuristic based on linux free tool (total - free - buffers - cache). [bytes](gauge)", "/proc", ""
	"scaling_factor_max", "Perf metric scaling factor, MAX value. [numeric](gauge)", "perf event", ""
	"scaling_factor_avg", "Perf metric scaling factor, average from all CPUs. [numeric](gauge)", "perf event", ""
	"memory_stat_page_faults", "Page faults [numeric](counter)", "cgroup", ""
	"memory_numa_free", "NUMA memory free per numa node TODO! [numeric](gauge)", "/proc", "numa_node"
	"memory_numa_used", "NUMA memory used per numa node TODO! [numeric](gauge)", "/proc", "numa_node"
	"pmm_bandwidth_read", "Persistent memory module number of reads. [numeric](counter)", "perf event", "cpu, pmu"
	"pmm_bandwidth_write", "Persistent memory module number of writes. [numeric](counter)", "perf event", "cpu, pmu"
	"cas_count_read", "Column adress select number of reads [numeric](counter)", "perf event", "cpu, pmu"
	"cas_count_write", "Column adress select number of writes [numeric](counter)", "perf event", "cpu, pmu"
	"pmm_reads_mb_per_second", "TBD [numeric](gauge)", "derived", "cpu, pmu"
	"pmm_writes_mb_per_second", "TBD [numeric](gauge)", "derived", "cpu, pmu"
	"pmm_total_mb_per_second", "TBD [numeric](gauge)", "derived", "cpu, pmu"
	"dram_reads_mb_per_second", "TBD [numeric](gauge)", "derived", "cpu, pmu"
	"dram_writes_mb_per_second", "TBD [numeric](gauge)", "derived", "cpu, pmu"
	"dram_total_mb_per_second", "TBD [numeric](gauge)", "perf event", "cpu, pmu"
	"dram_hit", "TBD [numeric](gauge)", "derived", "cpu, pmu"
	"upi_txl_flits", "TBD [numeric](counter)", "perf event", "cpu, pmu"
	"upi_rxl_flits", "TBD [numeric](counter)", "perf event", "cpu, pmu"
	"upi_bandwidth_mb_per_second", "TBD [numeric](counter)", "derived", "cpu, pmu"



Internal metrics
================

.. csv-table::
	:header: "Name", "Help", "Source", "Levels/Labels"
	:widths: 5, 5, 5, 5 

		:width: 90% 

	"up", "Time the WCA was last seen. [numeric](counter)", "internal", ""
	"up", "Time the WCA was last seen. [numeric](counter)", "internal", ""

