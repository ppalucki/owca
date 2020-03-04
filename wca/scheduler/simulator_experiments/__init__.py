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
import itertools
import logging
import os

import shutil
from typing import List, Tuple, Callable, Dict

from wca.nodes import Node, Task
from wca.scheduler.algorithms import Algorithm
from wca.scheduler.cluster_simulator import ClusterSimulator
from wca.scheduler.data_providers.cluster_simulator_data_provider import (
        ClusterSimulatorDataProvider)
from wca.scheduler.simulator_experiments.reporting import (
    IterationData, wrapper_iteration_finished_callback,
    generate_subexperiment_report, generate_experiment_report)

log = logging.getLogger(__name__)


def experiments_set__generic(experiment_name, extra_charts, *args):
    """takes the same arguments as experiment__generic but as lists. @TODO"""

    reports_root_directory: str = 'experiments_results'
    experiment_stats: List = []

    def experiment__generic(
            exp_iter: int,
            max_iteration: int,
            task_creation_fun_def: Tuple[Callable, Dict],
            nodes: List[Node],
            scheduler_init: Tuple[Algorithm, Dict],
    ):
        scheduler_class, scheduler_kwargs = scheduler_init
        input_args = locals()
        input_args.pop('experiment_stats')
        iterations_data: List[IterationData] = []

        simulator = ClusterSimulator(tasks=[], nodes=nodes, scheduler=None)
        data_proxy = ClusterSimulatorDataProvider(simulator)
        simulator.scheduler = scheduler_class(data_provider=data_proxy, **scheduler_kwargs)

        task_creation_class, task_creation_args = task_creation_fun_def
        task_creation_fun = task_creation_class(**task_creation_args)

        run_n_iter(max_iteration, simulator, task_creation_fun,
                   wrapper_iteration_finished_callback(iterations_data))

        if extra_charts:
            filter_metrics = simulator.scheduler.get_metrics_names()
        else:
            filter_metrics = []

        dimensions = len(scheduler_kwargs.get('dimensions', []))

        stats = generate_subexperiment_report(
            experiment_name,
            '%d_%snodes_%s_%s' % (exp_iter, len(nodes), task_creation_fun, simulator.scheduler),
            input_args, iterations_data,
            reports_root_directory=reports_root_directory,
            filter_metrics=filter_metrics,
            task_gen=task_creation_fun,
            scheduler=simulator.scheduler,
            charts=False,
        )

        log.debug('Finished experiment.', experiment_name, exp_iter)
        log.debug('Stats:', stats)
        experiment_stats.append(stats)
        return iterations_data

    if os.path.isdir('experiments_results/{}'.format(experiment_name)):
        shutil.rmtree('experiments_results/{}'.format(experiment_name))
    iterations_data_list = []
    for exp_iter, params in enumerate(itertools.product(*args)):
        iterations_data = experiment__generic(exp_iter, *params)
        iterations_data_list.append(iterations_data)

    exp_dir = '{}/{}'.format(reports_root_directory, experiment_name)

    generate_experiment_report(experiment_stats, exp_dir)

    return iterations_data_list


def run_n_iter(iterations_count: int, simulator: ClusterSimulator,
               task_creation_fun: Callable[[int], Task],
               iteration_finished_callback: Callable):
    iteration = 0
    while iteration < iterations_count:
        simulator.iterate_single_task(task_creation_fun(iteration))
        iteration_finished_callback(iteration, simulator)
        iteration += 1
    return simulator
