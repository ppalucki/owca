#!/usr/bin/env python3.6

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
import json
from typing import Dict, List
import logging

from model import Task, Node
from serializator import AnalyzerQueries
from results import ExperimentResults

FORMAT = "%(asctime)-15s:%(levelname)s %(module)s %(message)s"
logging.basicConfig(format=FORMAT, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)


def read_experiment_data(file: str):
    with open(file, 'r') as experiment_data_file:
        json_data = json.load(experiment_data_file)
    return json_data


def main():
    experiment_name = ['pmbench_base_results_', 'pmbench_advanced_results_',
                       'redis_base_results_', 'redis_advanced_results_',
                       'memcached_base_results_', 'memcached_advanced_results_']
    # example date
    date = '2020-10-21-16-55'

    for exp in experiment_name:
        name = exp + date
        results_dir = '../hmem_experiments/' + name
        latex_file = ExperimentResults('Experiment-' + name)

        analyzer_queries = AnalyzerQueries('http://100.64.176.36:30900')

        for file in os.listdir(results_dir):
            experiment_data = read_experiment_data(os.path.join(results_dir, file))
            t_start = experiment_data["experiment"]["start"]
            t_end = experiment_data["experiment"]["end"]
            description = experiment_data["experiment"]["description"]
            experiment_name = experiment_data["meta"]["name"]
            experiment_type = experiment_data['meta']['params']['type']
            nodes: List[Node] = analyzer_queries.query_node_list(t_end)
            tasks: Dict[str, Task] = analyzer_queries.query_tasks_list(t_end)
            analyzer_queries.query_task_performance_metrics(
                t_end, tasks)
            analyzer_queries.query_task_numa_pages(t_end, tasks)
            latex_file.discover_experiment_data(experiment_name, experiment_type,
                                                tasks, nodes, description, t_start)
        latex_file.generate_pdf()


if __name__ == "__main__":
    main()
