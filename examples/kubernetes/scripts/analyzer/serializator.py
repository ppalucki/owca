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

from typing import Dict, List, Tuple
from connection import PrometheusClient
from model import Task, Node
from metrics import Metric, MetricsQueries, Function, FunctionsDescription, platform_metrics


def build_function_call_id(function: Function, arg: str):
    return "{}{}".format(FunctionsDescription[function], str(arg))


class AnalyzerQueries:
    """Class used for namespace"""

    def __init__(self, prometheus_url):
        self.prometheus_client = PrometheusClient(prometheus_url)

    def query_node_name_list(self, time) -> List[str]:
        query_result = self.prometheus_client.instant_query(MetricsQueries[Metric.WCA_UP], time)
        nodes = []
        for metric in query_result:
            node = metric['metric']['host']
            nodes.append(node)

        return nodes

    def query_node_list(self, time) -> List[Node]:
        node_names: List[str] = self.query_node_name_list(time)
        nodes: List[Node] = []
        for node_name in node_names:
            new_node = Node(name=node_name)
            new_node.performance_metrics[0] = {}
            new_node.performance_metrics[1] = {}
            for metric in platform_metrics:
                socket0, socket1 = \
                    self.query_platform_performance_metric(
                        time, metric, node_name)
                new_node.performance_metrics[0][metric.name], \
                    new_node.performance_metrics[1][metric.name] = socket0, socket1
            nodes.append(new_node)
        return nodes

    def query_tasks_list(self, time) -> Dict[str, Task]:
        query_result = self.prometheus_client.instant_query(MetricsQueries[Metric.TASK_UP], time)
        tasks = {}
        for metric in query_result:
            metric = metric['metric']
            task_name = metric['task_name']
            tasks[task_name] = Task(metric['task_name'], metric['app'],
                                    metric['nodename'])
        return tasks

    def query_platform_performance_metric(self, time: int, metric: Metric, node: str = ""):
        parametrize_query = \
            MetricsQueries[metric].replace('{}', '{{nodename="{node}"}}'.format(node=node))
        query_results = self.prometheus_client.instant_query(parametrize_query, time)

        if query_results:
            # return socket 0, socket 1; socket 0 always first;
            if query_results[0]['metric']['socket'] == '0':
                return query_results[0]['value'][1], query_results[1]['value'][1]
            else:
                return query_results[1]['value'][1], query_results[0]['value'][1]
        else:
            return 0, 0

    def query_performance_metrics(self, time: int, functions_args: Dict[Metric, List[Tuple]],
                                  metrics: List[Metric], window_length: int) -> Dict[Metric, Dict]:
        """performance metrics which needs aggregation over time"""
        query_results: Dict[Metric, Dict] = {}
        for metric in metrics:
            for function in functions_args[metric]:
                query_template = "{function}({arguments}{prom_metric}[{window_length}s])"
                query = query_template.format(function=function[0].value,
                                              arguments=function[1],
                                              window_length=window_length,
                                              prom_metric=MetricsQueries[metric])
                query_result = self.prometheus_client.instant_query(query, time)
                aggregation_name = build_function_call_id(function[0], function[1])

                if metric in query_results:
                    query_results[metric][aggregation_name] = query_result
                else:
                    query_results[metric] = {aggregation_name: query_result}
        return query_results

    def query_task_performance_metrics(self, time: int, tasks: Dict[str, Task],
                                       window_length: int = 120):

        metrics = [Metric.TASK_THROUGHPUT, Metric.TASK_LATENCY,
                   Metric.TASK_MEM_MBW_LOCAL, Metric.TASK_MEM_MBW_REMOTE]
        gauge_function_args = [(Function.AVG, ''), (Function.QUANTILE, '0.1,'),
                               (Function.QUANTILE, '0.9,')]
        counter_function_args = [(Function.RATE, '')]

        function_args = {Metric.TASK_THROUGHPUT: gauge_function_args,
                         Metric.TASK_LATENCY: gauge_function_args,
                         Metric.TASK_MEM_MBW_LOCAL: counter_function_args,
                         Metric.TASK_MEM_MBW_REMOTE: counter_function_args}

        query_results = self.query_performance_metrics(time, function_args, metrics, window_length)
        for metric, query_result in query_results.items():
            for aggregation_name, result in query_result.items():
                for per_app_result in result:
                    task_name = per_app_result['metric']['task_name']
                    value = per_app_result['value'][1]
                    if task_name in tasks and metric in tasks[task_name].performance_metrics:
                        tasks[task_name].performance_metrics[metric][aggregation_name] = value
                    elif task_name in tasks:
                        tasks[task_name].performance_metrics[metric] = {aggregation_name: value}

    def query_task_numa_pages(self, time: int, tasks: Dict[str, Task]):
        query_result = self.prometheus_client.instant_query('{}'.format(
            Metric.TASK_MEM_NUMA_PAGES.value), time)
        for metric in query_result:
            task_name = metric['metric']['task_name']
            value = metric['value'][1]
            numa_node = metric['metric']['numa_node']
            if Metric.TASK_MEM_NUMA_PAGES not in tasks[task_name].performance_metrics:
                tasks[task_name].performance_metrics[Metric.TASK_MEM_NUMA_PAGES] =\
                    {'0': 0, '1': 0, '2': 0, '3': 0}
            tasks[task_name].performance_metrics[Metric.TASK_MEM_NUMA_PAGES][numa_node] = value
