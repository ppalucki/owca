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

import os
import datetime
import logging
import itertools
from functools import partial
from collections import Counter
import pprint
from typing import Dict, List, Any, Callable, Tuple
import shutil

import random
from dataclasses import dataclass

from wca.logger import init_logging
from wca.scheduler.algorithms import Algorithm
from wca.scheduler.algorithms.bar import BARGeneric
from wca.scheduler.algorithms.fit import FitGeneric
from wca.scheduler.cluster_simulator import ClusterSimulator, Node, Resources, Task
from wca.scheduler.data_providers.cluster_simulator_data_provider import (
    ClusterSimulatorDataProvider)
from wca.scheduler.types import ResourceType as rt

log = logging.getLogger(__name__)


# taken from 2lm contention demo slides:
# wca_load_balancing_multidemnsional_2lm_v0.2
tasks__2lm_contention_demo = [
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


def extend_membw_dimensions_to_write_read(taskset):
    """replace dimensions rt.MEMBW with rt.MEMBW_WRITE and rt.MEMBW_READ"""
    new_taskset = []
    for task in taskset:
        task_ = task.copy()
        membw = task_.requested.data[rt.MEMBW]
        task_.remove_dimension(rt.MEMBW)
        task_.add_dimension(rt.MEMBW_READ, membw)
        task_.add_dimension(rt.MEMBW_WRITE, 0)
        new_taskset.append(task_)
    return new_taskset


def randonly_choose_from_taskset(taskset, size, seed):
    random.seed(seed)
    r = []
    for i in range(size):
        random_idx = random.randint(0, len(taskset) - 1)
        task = taskset[random_idx].copy()
        task.name += Task.CORE_NAME_SEP + str(i)
        r.append(task)
    return r


def randonly_choose_from_taskset_single(taskset, dimensions, name_sufix):
    random_idx = random.randint(0, len(taskset) - 1)
    task = taskset[random_idx].copy()
    task.name += Task.CORE_NAME_SEP + str(name_sufix)

    task_dim = set(task.requested.data.keys())
    dim_to_remove = task_dim.difference(dimensions)
    for dim in dim_to_remove:
        task.remove_dimension(dim)

    return task


@dataclass
class IterationData:
    cluster_resource_usage: Resources
    per_node_resource_usage: Dict[Node, Resources]
    broken_assignments: Dict[Node, int]
    tasks_types_count: Dict[str, int]


def wrapper_iteration_finished_callback(iterations_data: List[IterationData]):
    def iteration_finished_callback(iteration: int, simulator: ClusterSimulator):
        per_node_resource_usage = simulator.per_node_resource_usage(True)
        cluster_resource_usage = simulator.cluster_resource_usage(True)
        broken_assignments = simulator.rough_assignments_per_node.copy()
        tasks_types_count = Counter([task.get_core_name() for task in simulator.tasks])

        iterations_data.append(IterationData(
            cluster_resource_usage, per_node_resource_usage,
            broken_assignments, tasks_types_count))

    return iteration_finished_callback


def create_report(title: str, subtitle: str,
                  header: Dict[str, Any], iterations_data: List[IterationData]):
    plt.style.use('ggplot')
    iterd = iterations_data

    iterations = np.arange(0, len(iterd))
    cpu_usage = np.array([iter_.cluster_resource_usage.data[rt.CPU] for iter_ in iterd])
    mem_usage = np.array([iter_.cluster_resource_usage.data[rt.MEM] for iter_ in iterd])

    if rt.MEMBW_READ in iterd[0].cluster_resource_usage.data:
        membw_usage = np.array([iter_.cluster_resource_usage.data[rt.MEMBW_READ]
                                for iter_ in iterd])
    else:
        membw_usage = np.array([iter_.cluster_resource_usage.data[rt.MEMBW] for iter_ in iterd])
    # ---
    fig, axs = plt.subplots(2)
    fig.set_size_inches(11, 11)
    axs[0].plot(iterations, cpu_usage, 'r--')
    axs[0].plot(iterations, mem_usage, 'b--')
    axs[0].plot(iterations, membw_usage, 'g--')
    axs[0].legend(['cpu usage', 'mem usage', 'membw usage'])
    # ---
    axs[0].set_title('{} {}'.format(title, subtitle), fontsize=10)
    # ---
    axs[0].set_xlim(iterations.min() - 1, iterations.max() + 1)
    axs[0].set_ylim(0, 1)

    broken_assignments = np.array([sum(list(iter_.broken_assignments.values())) for iter_ in iterd])
    axs[1].plot(iterations, broken_assignments, 'g--')
    axs[1].legend(['broken assignments'])
    axs[1].set_xlabel('iteration')
    axs[1].set_ylabel('')
    axs[1].set_xlim(iterations.min() - 1, iterations.max() + 1)
    axs[1].set_ylim(broken_assignments.min() - 1, broken_assignments.max() + 1)

    if not os.path.isdir('experiments_results/{}'.format(title)):
        os.makedirs('experiments_results/{}'.format(title))
    fig.savefig('experiments_results/{}/{}.png'.format(title, subtitle))

    with open('experiments_results/{}/{}.txt'.format(title, subtitle), 'w') as fref:
        t_ = datetime.datetime.strftime(datetime.datetime.now(), '%Y%m%d_%H%M')
        fref.write("Start of experiment: {}\n".format(t_))
        fref.write("Run params: {}\n".format(pprint.pformat(header, indent=4)))
        fref.write("Iterations: {}\n".format(len(iterations_data)))
        fref.write("Assigned tasks: {}\n".format(iterations_data[-1].tasks_types_count))
        fref.write("Broken assignments: {}\n".format(
            sum(iterations_data[-1].broken_assignments.values())))

        rounded_last_iter_resources = \
            map(partial(round, ndigits=2), (cpu_usage[-1], mem_usage[-1], membw_usage[-1],))
        fref.write("resource_usage(cpu, mem, membw_flat) = ({}, {}, {})\n".format(
            *rounded_last_iter_resources))

        for node, usages in iterations_data[-1].per_node_resource_usage.items():
            rounded_last_iter_resources = map(
                partial(round, ndigits=2),
                (usages.data[rt.CPU], usages.data[rt.MEM], usages.data[rt.MEMBW_READ],))
            fref.write(
                "resource_usage_per_node(node={}, cpu, mem, membw_flat) = ({}, {}, {})\n".format(
                    node.name, *rounded_last_iter_resources))

    with open('experiments_results/{}/README.txt'.format(title), 'a') as fref:
        fref.write("Subexperiment: {}\n".format(subtitle))
        fref.write("Run params: {}\n\n".format(pprint.pformat(header, indent=4)))


def experiments_set__generic(experiment_name, *args):
    """takes the same arguments as experiment__generic but as lists. @TODO"""
    def experiment__generic(
                exp_iter: int,
                max_iteration: int,
                task_creation_fun: Callable,
                scheduler_init: Tuple[Algorithm, Dict],
                nodes: List[Node]):
        scheduler_class, scheduler_kwargs = scheduler_init
        input_args = locals()
        iterations_data: List[IterationData] = []

        simulator = ClusterSimulator(tasks=[], nodes=nodes, scheduler=None)
        data_proxy = ClusterSimulatorDataProvider(simulator)
        simulator.scheduler = scheduler_class(data_provider=data_proxy, **scheduler_kwargs)

        run_n_iter(max_iteration, simulator, task_creation_fun,
                   wrapper_iteration_finished_callback(iterations_data))

        create_report(experiment_name, exp_iter, input_args, iterations_data)
        log.info('Finished experiment.')

    if os.path.isdir('experiments_results/{}'.format(experiment_name)):
        shutil.rmtree('experiments_results/{}'.format(experiment_name))
    for exp_iter, params in enumerate(itertools.product(*args)):
        experiment__generic(exp_iter, *params)


class TaskGenerator__2lm_contention_demo:
    """takes randomly from >>tasks__2lm_contention_demo<<"""
    def __init__(self, max_items, seed):
        self.max_items = max_items
        random.seed(seed)

    def __call__(self, index: int):
        if index >= self.max_items:
            return None
        return self.rand_from_taskset(str(index))

    @staticmethod
    def rand_from_taskset(name_suffix: str):
        return randonly_choose_from_taskset_single(
                extend_membw_dimensions_to_write_read(tasks__2lm_contention_demo),
                {rt.CPU, rt.MEM, rt.MEMBW_READ, rt.MEMBW_WRITE}, name_suffix)


class TaskGenerator_equal:
    """Multiple each possible kind of tasks by replicas"""
    def __init__(self, replicas):
        self.replicas = replicas
        self.tasks = []

        tasks = extend_membw_dimensions_to_write_read(tasks__2lm_contention_demo)
        for task in tasks:
            self.tasks.extend([task]*replicas)

    def __call__(self, index: int):
        return self.tasks.pop()


def run_n_iter(iterations_count: int, simulator: ClusterSimulator,
               task_creation_fun: Callable[[int], Task],
               iteration_finished_callback: Callable):
    iteration = 0
    while iteration < iterations_count:
        simulator.iterate_single_task(task_creation_fun(iteration))
        iteration_finished_callback(iteration, simulator)
        iteration += 1
    return simulator


def prepare_NxMxK_nodes__demo_configuration(
        apache_pass_count, dram_only_v1_count,
        dram_only_v2_count,
        dimensions={rt.CPU, rt.MEM, rt.MEMBW_READ, rt.MEMBW_WRITE}) -> List[Node]:
    """Taken from WCA team real cluster."""
    apache_pass = {rt.CPU: 40, rt.MEM: 1000, rt.MEMBW: 40, rt.MEMBW_READ: 40,
                   rt.MEMBW_WRITE: 10, rt.WSS: 256}
    dram_only_v1 = {rt.CPU: 48, rt.MEM: 192, rt.MEMBW: 200, rt.MEMBW_READ: 150,
                    rt.MEMBW_WRITE: 150, rt.WSS: 192}
    dram_only_v2 = {rt.CPU: 40, rt.MEM: 394, rt.MEMBW: 200, rt.MEMBW_READ: 200,
                    rt.MEMBW_WRITE: 200, rt.WSS: 394}
    nodes_spec = [apache_pass, dram_only_v1, dram_only_v2]

    # Filter only dimensions required.
    for i, node_spec in enumerate(nodes_spec):
        nodes_spec[i] = {dim: val for dim, val in node_spec.items() if dim in dimensions}

    inode = 0
    nodes = []
    for i_node_type, node_type_count in enumerate((apache_pass_count, dram_only_v1_count,
                                                   dram_only_v2_count,)):
        for i in range(node_type_count):
            node = Node(str(inode), available_resources=Resources(nodes_spec[i_node_type]))
            nodes.append(node)
            inode += 1
    return nodes


def run():
    # dimensions supported by simulator
    experiments_set__generic(
        'comparing_bar2d_vs_bar3d__option_A',
        (200,),
        (
            # TaskGenerator__2lm_contention_demo(max_items=200, seed=300),
            TaskGenerator_equal(10,),
        ),
        (
            (FitGeneric, {'dimensions': {rt.CPU, rt.MEM}}),
            # (FitGeneric, {'dimensions': {rt.CPU, rt.MEM, rt.MEMBW_READ, rt.MEMBW_WRITE}}),
            # (BARGeneric, {'dimensions': {rt.CPU, rt.MEM}}),
            # (BARGeneric, {'dimensions': {rt.CPU, rt.MEM, rt.MEMBW_READ, rt.MEMBW_WRITE}}),
        ),
        (prepare_NxMxK_nodes__demo_configuration(5, 10, 5),))


if __name__ == "__main__":
    try:
        import matplotlib.pyplot as plt
        import numpy as np
    except ImportError:
        # No installed packages required for report generation.
        exit(1)

    init_logging('trace', 'scheduler_extender_simulator_experiments')
    logging.basicConfig(level=logging.INFO)

    run()