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

import json
from dataclasses import dataclass
from enum import Enum
from typing import Dict

from runner import default_shell_run, annotate
from kernel_parameters import set_numa_balancing, set_toptier_scale_factor

from time import sleep, time


class ExperimentType(Enum):
    DRAM = 'dram'
    PMEM = 'pmem'
    HMEM_NUMA_BALANCING = 'hmem_numa_balancing'
    HMEM_NO_NUMA_BALANCING = 'hmem_no_numa_balancig'
    COLD_START = 'cold_start'
    TOPTIER = 'toptier'
    TOPTIER_WITH_COLDSTART = 'toptier_with_coldstart'


EXPERIMENT_DESCRIPTION = {
    ExperimentType.DRAM: 'workloads running exclusively on dram',
    ExperimentType.PMEM: 'workloads running exclusively on pmem',
    ExperimentType.HMEM_NUMA_BALANCING: 'workloads running on dram and pmem '
                                        'with numa balancing turned on',
    ExperimentType.HMEM_NO_NUMA_BALANCING: 'workloads running on dram and pmem '
                                           'with numa balancing turned off',
    ExperimentType.COLD_START: 'workload starts to run on pmem and after set time passes '
                               'can move to dram if necessary for workload performance',
    ExperimentType.TOPTIER: 'workloads have toptier limit; if limit is exceeded some of the '
                            'memory from dram goes to pmem',
    ExperimentType.TOPTIER_WITH_COLDSTART: 'workload starts to run on pmem and after set time '
                                           'passes can move to dram if necessary for workload '
                                           'performance; workloads have toptier limit; if '
                                           'limit is exceeded some of the memory from dram '
                                           'goes to pmem'
}


@dataclass
class Experiment:
    name: str
    number_of_workloads: Dict[str, int]
    type: ExperimentType
    description: str
    start_timestamp: float = None
    stop_timestamp: float = None


@dataclass
class ExperimentConfiguration:
    numa_balancing: bool
    toptier_scale_factor: str = '2000'


ONLY_NUMA_BALANCING_CONF = ExperimentConfiguration(numa_balancing=True)
TOPTIER_CONF = ExperimentConfiguration(numa_balancing=True, toptier_scale_factor='10000')

EXPERIMENT_CONFS = {ExperimentType.DRAM: ONLY_NUMA_BALANCING_CONF,
                    ExperimentType.PMEM: ONLY_NUMA_BALANCING_CONF,
                    ExperimentType.HMEM_NUMA_BALANCING: ONLY_NUMA_BALANCING_CONF,
                    ExperimentType.HMEM_NO_NUMA_BALANCING: ExperimentConfiguration(
                       numa_balancing=False),
                    ExperimentType.COLD_START: ONLY_NUMA_BALANCING_CONF,
                    ExperimentType.TOPTIER: TOPTIER_CONF,
                    ExperimentType.TOPTIER_WITH_COLDSTART: TOPTIER_CONF}


def experiment_to_json(experiment: Experiment, output_file: str):
    experiment_dict = {'meta':
                       {'name': experiment.name,
                        'description': EXPERIMENT_DESCRIPTION[experiment.type],
                        'params': {
                            'workloads_count': experiment.number_of_workloads,
                            'type': experiment.type.value,
                        }
                        },
                       'experiment': {
                           'description': experiment.description,
                           'start': experiment.start_timestamp,
                           'end': experiment.stop_timestamp
                       }
                       }
    with open(output_file, 'w+') as experiment_json_file:
        json.dump(experiment_dict, experiment_json_file)


def _scale_workload(workload_name, number_of_workloads=1):
    cmd_scale = "kubectl scale sts {} --replicas={}".format(
        workload_name, number_of_workloads)
    default_shell_run(cmd_scale)


def _set_configuration(configuration: ExperimentConfiguration):
    set_numa_balancing(configuration.numa_balancing)
    set_toptier_scale_factor(configuration.toptier_scale_factor)


def _run_workloads(number_of_workloads: Dict,
                   sleep_duration: int):
    for workload_name in number_of_workloads.keys():
        _scale_workload(workload_name, number_of_workloads[workload_name])
    sleep(sleep_duration)
    for workload_name in number_of_workloads.keys():
        _scale_workload(workload_name, 0)


def run_experiment(scenario_name: str,
                   number_of_workloads: Dict[str, int], sleep_duration: int,
                   experiment_type: ExperimentType):
    _set_configuration(EXPERIMENT_CONFS[experiment_type])
    start_timestamp = time()
    annotate('Running experiment: {}'.format(scenario_name))
    _run_workloads(number_of_workloads, sleep_duration)
    stop_timestamp = time()
    return Experiment(scenario_name, number_of_workloads, experiment_type,
                      EXPERIMENT_DESCRIPTION[experiment_type], start_timestamp, stop_timestamp)
