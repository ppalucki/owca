from typing import Set
from wca.scheduler.cluster_simulator import Task
from wca.scheduler.types import ResourceType as rt
from wca.scheduler.cluster_simulator import Resources


# wca_load_balancing_multidemnsional_2lm_v0.2
TASK_DEFINITIONS__2LM_V02 = [
    Task(name='memcached_big',
         requested=Resources({rt.CPU: 2, rt.MEM: 28,
                              rt.MEMBW: 1.3, rt.WSS: 1.7})),
    Task(name='memcached_medium',
         requested=Resources({rt.CPU: 2, rt.MEM: 12,
                              rt.MEMBW: 1.0, rt.WSS: 1.0})),
    Task(name='memcached_small',
         requested=Resources({rt.CPU: 2, rt.MEM: 2.5,
                              rt.MEMBW: 0.4, rt.WSS: 0.4})),
    # ---
    Task(name='redis_big',
         requested=Resources({rt.CPU: 1, rt.MEM: 29,
                              rt.MEMBW: 0.5, rt.WSS: 14})),
    Task(name='redis_medium',
         requested=Resources({rt.CPU: 1, rt.MEM: 11,
                              rt.MEMBW: 0.4, rt.WSS: 10})),
    Task(name='redis_small',
         requested=Resources({rt.CPU: 1, rt.MEM: 1.5,
                              rt.MEMBW: 0.3, rt.WSS: 1.5})),
    # ---
    Task(name='stress_stream_big',
         requested=Resources({rt.CPU: 3, rt.MEM: 13,
                              rt.MEMBW: 18, rt.WSS: 12})),
    Task(name='stress_stream_medium',
         requested=Resources({rt.CPU: 1, rt.MEM: 12,
                              rt.MEMBW: 6, rt.WSS: 10})),
    Task(name='stress_stream_small',
         requested=Resources({rt.CPU: 1, rt.MEM: 7,
                              rt.MEMBW: 5, rt.WSS: 6})),
    # ---
    Task(name='sysbench_big',
         requested=Resources({rt.CPU: 3, rt.MEM: 9,
                              rt.MEMBW: 13, rt.WSS: 7.5})),
    Task(name='sysbench_medium',
         requested=Resources({rt.CPU: 2, rt.MEM: 2,
                              rt.MEMBW: 10, rt.WSS: 2})),
    Task(name='sysbench_small',
         requested=Resources({rt.CPU: 1, rt.MEM: 1,
                              rt.MEMBW: 8, rt.WSS: 1}))
]

TASK_DEFINITIONS__ARTIFICIAL_3TYPES = [
    # Artificial workloads
    Task(name='cpu', requested=Resources({rt.CPU: 10, rt.MEM: 50, rt.MEMBW_READ: 2, rt.MEMBW_WRITE: 1, rt.WSS: 1})),
    Task(name='mem', requested=Resources({rt.CPU: 1, rt.MEM: 100, rt.MEMBW_READ: 1, rt.MEMBW_WRITE: 0, rt.WSS: 1})),
    Task(name='mbw', requested=Resources({rt.CPU: 1, rt.MEM: 1,   rt.MEMBW_READ: 10, rt.MEMBW_WRITE: 5, rt.WSS: 1})),
]

TASK_DEFINITIONS__ARTIFICIAL_2DIM_2TYPES = [
    Task(name='cputask', requested=Resources(
        {rt.CPU: 20, rt.MEM: 40, rt.MEMBW_READ: 0, rt.MEMBW_WRITE: 0, rt.WSS: 0})),
    Task(name='memtask', requested=Resources(
        {rt.CPU: 10, rt.MEM: 200, rt.MEMBW_READ: 0, rt.MEMBW_WRITE: 0, rt.WSS: 0})),
]

TASK_DEFINITIONS__ARTIFICIAL_2 = [
    # Artificial workloads
    Task(name='cpu', requested=Resources({rt.CPU: 10, rt.MEM: 50, rt.MEMBW_READ: 2, rt.MEMBW_WRITE:1, rt.WSS: 1})),
    Task(name='cpu2', requested=Resources({rt.CPU: 5, rt.MEM: 25, rt.MEMBW_READ: 2, rt.MEMBW_WRITE:0, rt.WSS: 1})),
    Task(name='mem', requested=Resources({rt.CPU: 1, rt.MEM: 25, rt.MEMBW_READ: 1, rt.MEMBW_WRITE:0, rt.WSS: 1})),
    Task(name='mem2', requested=Resources({rt.CPU: 1, rt.MEM: 20, rt.MEMBW_READ: 1, rt.MEMBW_WRITE:1, rt.WSS: 1})),
    Task(name='mbw', requested=Resources({rt.CPU: 1, rt.MEM: 1, rt.MEMBW_READ: 10, rt.MEMBW_WRITE:5, rt.WSS: 1})),
    Task(name='mbw2', requested=Resources({rt.CPU: 1, rt.MEM: 1, rt.MEMBW_READ: 7, rt.MEMBW_WRITE:1, rt.WSS: 1})),
]


def taskset_dimensions(dimensions: Set[rt], taskset):
    new_taskset = []
    dimensions_to_remove = set(taskset[0].requested.data.keys()).difference(dimensions)
    for task in taskset:
        task_copy = task.copy()
        for dim in dimensions_to_remove:
            task_copy.remove_dimension(dim)
        new_taskset.append(task_copy)
    return new_taskset
