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

from time import time

from runner import scale_down_all_workloads
from workload_runner import run_experiment, experiment_to_json
from scenarios import Scenario, REDIS_SCENARIOS


def run_scenario(scenario: Scenario):
    for workload_count in scenario.workloads_count:
        experiment = run_experiment(scenario.name, workload_count,
                                    scenario.sleep_duration, scenario.experiment_type)
        experiment_to_json(experiment, 'results/{}-{}.json'.format(scenario.name, time()))
    scale_down_all_workloads(wait_time=10)


def main():
    # redis
    for scenario in REDIS_SCENARIOS:
        run_scenario(scenario)


if __name__ == '__main__':
    main()
