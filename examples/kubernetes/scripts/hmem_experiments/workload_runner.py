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
import logging
import subprocess

from dataclasses import dataclass
from typing import Dict
from time import sleep, time

from kernel_parameters import set_numa_balancing, set_toptier_scale_factor
from scenarios import Scenario, ExperimentType


FORMAT = "%(asctime)-15s:%(levelname)s %(module)s %(message)s"
logging.basicConfig(format=FORMAT, level=logging.DEBUG)

DRY_RUN = False
if DRY_RUN:
    logging.info("[DRY_RUN] Running in DRY_RUN mode!")


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
NUMA_BALANCING_OFF_CONF = ExperimentConfiguration(numa_balancing=False)
TOPTIER_CONF = ExperimentConfiguration(numa_balancing=True, toptier_scale_factor='10000')

EXPERIMENT_CONFS = {ExperimentType.DRAM: NUMA_BALANCING_OFF_CONF,
                    ExperimentType.PMEM: NUMA_BALANCING_OFF_CONF,
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
                   sleep_duration: int,
                   reset_workload=True):
    for workload_name in number_of_workloads.keys():
        _scale_workload(workload_name, number_of_workloads[workload_name])
    sleep(sleep_duration)
    if reset_workload:
        for workload_name in number_of_workloads.keys():
            _scale_workload(workload_name, 0)


def run_experiment(scenario: Scenario, number_of_workloads):
    # making sure that toptier limit value is as should be
    # even if previous toptier limit experiment was stopped before
    # restoring the old value
    if not scenario.modify_toptier_limit and (
            scenario.experiment_type == ExperimentType.TOPTIER_WITH_COLDSTART or
            scenario.experiment_type == ExperimentType.TOPTIER):
        for workload_name in scenario.workloads_count.keys():
            base_toptier_value = get_base_toptier_limit(workload_name)
            patch_toptier_limit(workload_name, base_toptier_value)

    _set_configuration(EXPERIMENT_CONFS[scenario.experiment_type])
    if scenario.modify_toptier_limit:
        for worklad_name, toptier_value in scenario.modify_toptier_limit.items():
            patch_toptier_limit(worklad_name, toptier_value)
    start_timestamp = time()
    _run_workloads(number_of_workloads, scenario.sleep_duration,
                   scenario.reset_workloads_between_steps)
    stop_timestamp = time()
    # restore old toptier value
    if scenario.modify_toptier_limit:
        for workload_name in scenario.modify_toptier_limit.keys():
            patch_toptier_limit(workload_name, get_base_toptier_limit(workload_name))
    return Experiment(scenario.name, number_of_workloads, scenario.experiment_type,
                      EXPERIMENT_DESCRIPTION[scenario.experiment_type],
                      start_timestamp, stop_timestamp)


TOPTIER_ANNOTATION_KEY = 'toptierlimit.cri-resource-manager.intel.com/pod'
SPEC = 'spec'
TEMPLATE = 'template'
METADATA = 'metadata'
ANNOTATIONS = 'annotations'


def get_base_toptier_limit(workload_name):
    """Returns toptier limit as declared in original stateful set definition.
    Patching stateful set's toptier limit value for pod template WILL NOT change this value"""
    get_sts_cmd = 'kubectl get sts {} -o json'.format(workload_name)
    statefulset_spec = subprocess.run([get_sts_cmd], stdout=subprocess.PIPE, shell=True)
    json_output = json.loads(statefulset_spec.stdout.decode('utf-8'))
    # this value should never change for the stateful set, that is why we use it
    # to read base toptier limit for given stateful set
    toptier_limit = json_output[METADATA][ANNOTATIONS][TOPTIER_ANNOTATION_KEY]
    return toptier_limit


def patch_toptier_limit(workload_name, toptier_value):
    patch = {SPEC:
             {TEMPLATE:
              {METADATA:
               {ANNOTATIONS:
                {TOPTIER_ANNOTATION_KEY: toptier_value}}}}}
    json_patch = json.dumps(patch)
    patch_cmd = 'kubectl patch statefulset {} -p \'{}\''.format(workload_name, json_patch)
    default_shell_run(patch_cmd)


def default_shell_run(command, verbose=True):
    """Default way of running commands."""
    if verbose:
        logging.debug('command run in shell >>{}<<'.format(command))
    if not DRY_RUN:
        r = subprocess.run(command, shell=True, check=True,
                           stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        return r.stdout.decode('utf-8'), r.stderr.decode('utf-8')
    else:
        return None, None


def scale_down_all_workloads(wait_time: int):
    """Kill all workloads"""
    command = "kubectl scale sts --all --replicas=0 && sleep {wait_time}".format(
        wait_time=wait_time)
    default_shell_run(command)
