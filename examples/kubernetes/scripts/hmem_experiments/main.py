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
from time import time
from datetime import datetime

from runner import scale_down_all_workloads
from workload_runner import run_experiment, experiment_to_json
from scenarios import Scenario, REDIS_SCENARIOS, BASE_REDIS_SCENARIOS, \
    PMBENCH_SCENARIOS, BASE_PMBENCH_SCENARIOS, \
    MEMCACHED_MUTILATE_SCENARIOS, BASE_MEMCACHED_MUTILATE_SCENARIOS
from kernel_parameters import show_frequency, set_necessary_parameters,\
    check_if_pmem_nodes_are_present


def run_scenario(scenario: Scenario, save_dir):
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)

    scale_down_all_workloads(wait_time=10)
    for workload_count in scenario.workloads_count:
        experiment = run_experiment(scenario, workload_count)
        experiment_to_json(experiment, '{}/{}-{}.json'.format(save_dir, scenario.name, time()))
    scale_down_all_workloads(wait_time=10)


def main():
    # Settings and checks before running experiments
    show_frequency()
    check_if_pmem_nodes_are_present()
    set_necessary_parameters()

    date = datetime.today().strftime('%Y-%m-%d-%H-%M')
    # pmbench
    for scenario in BASE_PMBENCH_SCENARIOS:
        run_scenario(scenario, 'pmbench_base_results_'+date)
    for scenario in PMBENCH_SCENARIOS:
        run_scenario(scenario, 'pmbench_advanced_results_'+date)
    # redis
    for scenario in BASE_REDIS_SCENARIOS:
        run_scenario(scenario, 'redis_base_results_'+date)
    for scenario in REDIS_SCENARIOS:
        run_scenario(scenario, 'redis_advanced_results_'+date)
    # memcached
    for scenario in BASE_MEMCACHED_MUTILATE_SCENARIOS:
        run_scenario(scenario, 'memcached_base_results_'+date)
    for scenario in MEMCACHED_MUTILATE_SCENARIOS:
        run_scenario(scenario, 'memcached_advanced_results_'+date)


if __name__ == '__main__':
    main()
