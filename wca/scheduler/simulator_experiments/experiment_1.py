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
import logging
from logging import DEBUG

from wca.logger import TRACE
from wca.scheduler.algorithms.bar import BAR
from wca.scheduler.algorithms.fit import Fit
from wca.scheduler.algorithms.hierbar import HierBAR
from wca.scheduler.algorithms.least_used import LeastUsed
from wca.scheduler.algorithms.least_used_bar import LeastUsedBAR
from wca.scheduler.algorithms.nop_algorithm import NOPAlgorithm
from wca.scheduler.algorithms.score import Score
from wca.scheduler.algorithms.static_assigner import StaticAssigner
from wca.scheduler.simulator_experiments.generic_experiment import experiments_iterator
from wca.scheduler.simulator_experiments.nodes_generators import prepare_nodes
from wca.scheduler.simulator_experiments.nodesets import (
    NODES_DEFINITIONS_2TYPES, NODES_DEFINITIONS_3TYPES)
from wca.scheduler.simulator_experiments.task_generators import TaskGeneratorEqual, \
    TaskGeneratorClasses, taskset_dimensions
from wca.scheduler.simulator_experiments.tasksets import TASKS_3TYPES, TASKS_2TYPES
from wca.scheduler.simulator_experiments.tasksets import TASKS_6TYPES
from wca.scheduler.types import WSS, MEM, CPU, MEMBW_WRITE, MEMBW_READ

x = DEBUG, TRACE  # to not be auto removed during import cleanup

log = logging.getLogger(__name__)

DIM5 = {CPU, MEM, MEMBW_READ, MEMBW_WRITE, WSS}
DIM4 = {CPU, MEM, MEMBW_READ, MEMBW_WRITE}
DIM2 = {CPU, MEM}


def experiment_mini():
    dim = DIM2
    experiments_iterator(
        'mini',
        [dict(retry_scheduling=True)],  # Simulator configuration
        [10],
        [
            (TaskGeneratorEqual,
             dict(task_definitions=TASKS_2TYPES, dimensions=dim, replicas=3,
                  duration=None, node_name='dram_0')),
        ],
        [
            prepare_nodes(NODES_DEFINITIONS_2TYPES, dict(aep=1, dram=1), dim),
        ],
        [
            (Fit, dict(dimensions=dim)),
        ],
        rmtree=False,
        charts=False,
        metrics=False,  # can be as list of metric names
    )


def experiment_score():
    dim = DIM2
    experiments_iterator(
        'score',
        [  # Simulator & data provider configuration
            dict(retry_scheduling=True, data_provider_args=dict(normalization_dimension=CPU)),
            dict(retry_scheduling=True, data_provider_args=dict(normalization_dimension=MEM)),
        ],
        [20],
        [
            (TaskGeneratorEqual,
             dict(task_definitions=TASKS_3TYPES, dimensions=dim, replicas=3,
                  duration=None, node_name='dram_0')),
        ],
        [
            prepare_nodes(NODES_DEFINITIONS_2TYPES, dict(aep=1, dram=1), dim),
        ],
        [
            (Score, dict(dimensions=dim)),
        ],
        rmtree=False,
        charts=False,
        metrics=False,  # can be as list of metric names
    )


def experiment_debug():
    task_scale = 1
    cluster_scale = 1
    dim = DIM4
    length = 90
    experiments_iterator(
        'debug',
        [dict(retry_scheduling=True)],
        [length * task_scale],
        [
            (TaskGeneratorEqual,
             dict(task_definitions=TASKS_3TYPES, replicas=10 * task_scale, duration=30,
                  alias='long', dimensions=dim)),
            (TaskGeneratorEqual,
             dict(task_definitions=TASKS_3TYPES, replicas=10 * task_scale, duration=5,
                  alias='short', dimensions=dim)),
            (TaskGeneratorEqual,
             dict(task_definitions=TASKS_3TYPES, replicas=10 * task_scale, duration=None,
                  dimensions=dim)),
        ],
        [
            prepare_nodes(NODES_DEFINITIONS_2TYPES,
                          dict(aep=2 * cluster_scale, dram=6 * cluster_scale), dim),
        ],
        [
            (LeastUsedBAR, dict(alias='BAR__LU_OFF', dimensions=DIM4, least_used_weight=0)),
        ],
    )


def experiment_bar():
    task_scale = 1
    cluster_scale = 1
    nodes_dimensions = DIM4

    experiments_iterator(
        'bar_weights',
        [{}],
        [30 * task_scale, ],
        [
            (TaskGeneratorClasses, dict(task_definitions=taskset_dimensions(nodes_dimensions,
                                                                            TASKS_6TYPES),
                                        counts=dict(mbw=20 * task_scale, cpu=5 * task_scale,
                                                    mem=5 * task_scale))),
        ],
        [
            prepare_nodes(NODES_DEFINITIONS_2TYPES,
                          dict(aep=2 * cluster_scale, dram=6 * cluster_scale), nodes_dimensions),
        ],
        [
            (LeastUsedBAR,
             dict(alias='BAR__LU_ON__WEIGHTS_UNEQUAL', dimensions=DIM4, least_used_weight=1,
                  bar_weights={MEM: 0.5})),
            (LeastUsedBAR,
             dict(alias='BAR__LU_ON__WEIGHTS_EQUAL', dimensions=DIM4, least_used_weight=1)),
            (LeastUsedBAR,
             dict(alias='BAR__LU_ON__WEIGHTS_100x', dimensions=DIM4, least_used_weight=100)),
            (LeastUsedBAR, dict(alias='BAR__LU_OFF', dimensions=DIM4, least_used_weight=0)),
        ],
    )


def experiment_full(task_scale=1, cluster_scale=1):
    dim = DIM4
    experiments_iterator(
        'intel_demo_local',
        [{}],
        [30 * task_scale],
        [
            (TaskGeneratorEqual,
             dict(task_definitions=TASKS_3TYPES, replicas=10 * task_scale, dimensions=dim)),
            (TaskGeneratorClasses, dict(task_definitions=TASKS_3TYPES,
                                        counts=dict(mbw=3 * task_scale, cpu=12 * task_scale,
                                                    mem=15 * task_scale), dimensions=dim)),
            (TaskGeneratorClasses, dict(task_definitions=TASKS_3TYPES,
                                        counts=dict(mbw=20 * task_scale, cpu=5 * task_scale,
                                                    mem=5 * task_scale), dimensions=dim)),
            (TaskGeneratorClasses, dict(task_definitions=TASKS_3TYPES,
                                        counts=dict(mbw=30 * task_scale, cpu=0 * task_scale,
                                                    mem=0 * task_scale), dimensions=dim)),
            (TaskGeneratorClasses, dict(task_definitions=TASKS_3TYPES,
                                        counts=dict(mbw=0 * task_scale, cpu=0 * task_scale,
                                                    mem=30 * task_scale), dimensions=dim)),
        ],
        [
            prepare_nodes(NODES_DEFINITIONS_2TYPES, dict(aep=0, dram=6 * cluster_scale),
                          dim),
            prepare_nodes(NODES_DEFINITIONS_2TYPES,
                          dict(aep=2 * cluster_scale, dram=6 * cluster_scale), dim),
            prepare_nodes(NODES_DEFINITIONS_2TYPES, dict(aep=0, dram=8 * cluster_scale),
                          dim),
            prepare_nodes(NODES_DEFINITIONS_2TYPES, dict(aep=cluster_scale, dram=cluster_scale),
                          dim, ),
        ],
        [
            (NOPAlgorithm, {}),
            (Fit, dict(dimensions=DIM2)),
            (Fit, dict(dimensions=DIM4)),
            (LeastUsed, dict(dimensions=DIM2)),
            (LeastUsed, dict(dimensions=DIM4)),
            (BAR, dict(dimensions=DIM2)),
            (HierBAR, dict(dimensions=DIM2)),
            (LeastUsedBAR,
             dict(alias='kubernetes_baseline', dimensions={CPU, MEM})),
            (LeastUsedBAR, dict(alias='BAR__LU_OFF', dimensions=DIM4, least_used_weight=0)),
            (LeastUsedBAR,
             dict(alias='BAR__LU_ON__WEIGHTS_EQUAL', dimensions=DIM4, least_used_weight=1)),
            (LeastUsedBAR,
             dict(alias='BAR__LU_ON__WEIGHTS_UNEQUAL', dimensions=DIM4, least_used_weight=1,
                  bar_weights={MEM: 0.5})),
        ],
    )


def experiment_static_assigner():
    dim = DIM2
    targeted_assigned_apps_counts = \
        {'aep_0': {'cputask': 1, 'memtask': 2},
         'dram_0': {'cputask': 1, 'memtask': 0}}

    experiments_iterator(
        'static_assigner',
        [{}],
        [6],
        [
            (TaskGeneratorClasses,
             dict(task_definitions=TASKS_2TYPES,
                  counts=dict(cputask=2, memtask=2), dimensions=dim)),
        ],
        [
            prepare_nodes(NODES_DEFINITIONS_2TYPES, dict(aep=1, dram=1), dim),
        ],
        [
            (StaticAssigner,
             dict(alias='StaticAssigner',
                  targeted_assigned_apps_counts=targeted_assigned_apps_counts,
                  dimensions=dim
                  )
             ),
        ],
    )


def experiment_hierbar():
    dim = DIM4
    iterations = 60
    experiments_iterator(
        'hierbar',
        [{}],
        [iterations],
        [
            (TaskGeneratorEqual, dict(task_definitions=TASKS_3TYPES, replicas=10, dimensions=dim)),
            (TaskGeneratorClasses,
             dict(task_definitions=TASKS_3TYPES, counts=dict(mem=30), dimensions=dim)),  # AEP
            (TaskGeneratorClasses,
             dict(task_definitions=TASKS_3TYPES, counts=dict(mbw=30), dimensions=dim)),  # no AEP
            (TaskGeneratorClasses,
             dict(task_definitions=TASKS_3TYPES, counts=dict(cpu=5, mem=5, mbw=20),
                  dimensions=dim)),
            (TaskGeneratorClasses,
             dict(task_definitions=TASKS_3TYPES, counts=dict(cpu=5, mem=20, mbw=5),
                  dimensions=dim)),
        ],
        [
            prepare_nodes(NODES_DEFINITIONS_3TYPES, dict(aep=2, sml=4, big=2), dim)
        ],
        [
            (LeastUsedBAR, dict(dimensions=DIM2, alias='native')),
            (HierBAR, dict(dimensions=dim)),
            (HierBAR, dict(dimensions=dim, merge_threshold=1, alias='extender')),
        ],
    )


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.WARN, format='%(levelname)s:%(module)s:%(funcName)s:%(lineno)d %(message)s')
    # logging.getLogger('wca.algorithms').setLevel(logging.DEBUG)
    # logging.getLogger('wca.scheduler.cluster_simulator').setLevel(TRACE)
    # experiment_mini()
    experiment_score()
    # experiment_debug()
    # experiment_bar()
    # experiment_hierbar()
    # experiment_static_assigner()
    # experiment_full()  # takes about 30 seconds
