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
import statistics
import json
from typing import Dict, List, Union, Iterable
import pandas as pd
import logging
from dataclasses import dataclass

from serializator import AnalyzerQueries
from view import TxtStagesExporter
from model import Stat, Task, Node, ExperimentMeta, ExperimentType, WStat, ClusterInfoLoader
from results import ExperimentResults

FORMAT = "%(asctime)-15s:%(levelname)s %(module)s %(message)s"
logging.basicConfig(format=FORMAT, level=logging.DEBUG)
logging.getLogger("requests").setLevel(logging.WARNING)
logging.getLogger("urllib3").setLevel(logging.WARNING)

WINDOW_LENGTH = 60 * 5


# @dataclass
# class Experiment:
#

@dataclass
class Stage:
    def __init__(self, t_end: int):
        SAFE_DELTA = 60  # 60 seconds back
        t_end -= SAFE_DELTA

        self.tasks: List[Task] = AnalyzerQueries.query_tasks_list(t_end)
        AnalyzerQueries.query_task_performance_metrics(time=t_end, tasks=self.tasks)

        self.nodes: Dict[str, Node] = AnalyzerQueries.query_nodes_list(t_end)
        AnalyzerQueries.query_platform_performance_metrics(time=t_end, nodes=self.nodes)


def calculate_task_summaries(tasks: List[Task], workloads_baseline: Dict[str, WStat]) \
        -> List[Dict[str, Union[float, str]]]:
    tasks_summaries = []
    for task in tasks:
        workload = task.workload_name

        if not task.has_metrics():
            continue

        task_summary = {
            "L": task.get_latency('avg'),
            "L[avg][{}s]".format(WINDOW_LENGTH): task.get_latency('avg'),
            "L[q0.1][{}s]".format(WINDOW_LENGTH): task.get_latency('q0.1,'),
            "L[q0.9][{}s]".format(WINDOW_LENGTH): task.get_latency('q0.9,'),
            "L[stdev][{}s]".format(WINDOW_LENGTH): task.get_latency('stdev'),
            "L[stdev][{}s][%]".format(WINDOW_LENGTH): -1 if task.get_latency(
                'avg') == 0 else task.get_latency('stdev') / task.get_latency('avg') * 100,
            # ----
            "T": task.get_throughput('avg'),
            "T[avg][{}s]".format(WINDOW_LENGTH): task.get_throughput('avg'),
            "T[q0.9][{}s]".format(WINDOW_LENGTH): task.get_throughput('q0.9,'),
            "T[q0.1][{}s]".format(WINDOW_LENGTH): task.get_throughput('q0.1,'),
            "T[stdev][{}s]".format(WINDOW_LENGTH): task.get_throughput('stdev'),

            "T[stdev][{}s][%]".format(WINDOW_LENGTH): -1 if task.get_throughput(
                'avg') == 0 else task.get_throughput('stdev') / task.get_throughput('avg') * 100,
            # ----
            "L_nice[%]": task.get_latency('avg') / workloads_baseline[workload].latency.max * 100,
            "T_nice[%]":
                task.get_throughput('avg') / workloads_baseline[workload].throughput.min * 100,
            # # ----
            "L_avg[%]": task.get_latency('avg') / workloads_baseline[workload].latency.avg * 100,
            "T_avg[%]":
                task.get_throughput('avg') / workloads_baseline[workload].throughput.avg * 100,
            # # ----
            "L_strict[%]": task.get_latency('avg') / workloads_baseline[workload].latency.min * 100,
            "T_strict[%]":
                task.get_throughput('avg') / workloads_baseline[workload].throughput.max * 100,
            # ----
            "task": task.name,
            "app": task.workload_name,
            "node": task.node
        }

        for key, val in task_summary.items():
            if type(val) == float:
                task_summary[key] = round(val, 3)

        tasks_summaries.append(task_summary)

    return tasks_summaries


class StagesAnalyzer:
    def __init__(self, events, workloads):
        self.events_data = (events, workloads)
        assert len(self.events_data[0]) % 2 == 0
        self.stages_count = int(len(self.events_data[0]) / 2)

        # @Move to loader
        T_DELTA = os.environ.get('T_DELTA', 0)

        self.stages = []
        for i in range(self.stages_count):
            self.stages.append(Stage(t_end=events[i * 2 + 1][0].timestamp() + T_DELTA))

    def delete_report_files(self, report_root_dir):
        if os.path.isdir(report_root_dir):
            for file_ in os.listdir(report_root_dir):
                os.remove(os.path.join(report_root_dir, file_))

    def get_all_tasks_count_in_stage(self, stage: int) -> int:
        """Only returns tasks count, directly from metric."""
        return sum(int(node.performance_metrics['platform_tasks_scheduled']['instant'])
                   for node in self.stages[stage].nodes.values()
                   if 'platform_tasks_scheduled' in node.performance_metrics)

    def get_all_workloads_in_stage(self, stage_index: int):
        return set(task.workload_name for task in self.stages[stage_index].tasks.values())

    def get_all_tasks_in_stage_on_nodes(self, stage_index: int, nodes: List[str]):
        return [task for task in self.stages[stage_index].tasks.values() if task.node in nodes]

    def get_all_nodes_in_stage(self, stage_index: int) -> List[str]:
        return [nodename for nodename in self.stages[stage_index].nodes]

    # wazne
    def calculate_per_workload_wstats_per_stage(self, workloads: Iterable[str], stage_index: int,
                                                filter_nodes: List[str]) -> Dict[str, WStat]:
        """
        Calculate WStat for all workloads in list for stage (stage_index).
        Takes data from all nodes.
        """
        workloads_wstats: Dict[str, WStat] = {}
        for workload in workloads:
            # filter tasks of a given workload
            tasks = [task for task in self.stages[stage_index].tasks.values() if
                     task.workload_name == workload]
            # filter out tasks which were run on >>filter_nodes<<
            tasks = [task for task in tasks if task.node not in filter_nodes]

            # avg but from 12 sec for a single task
            throughputs_list = [task.get_throughput('avg') for task in tasks if
                                task.get_throughput('avg') is not None]
            latencies_list = [task.get_latency('avg') for task in tasks if
                              task.get_latency('avg') is not None]

            if len(throughputs_list) == 0:
                exception_value = float('inf')
                t_max, t_min, t_avg, t_stdev = [exception_value] * 4
                l_max, l_min, l_avg, l_stdev = [exception_value] * 4
            elif len(throughputs_list) == 1:
                t_max, t_min, t_avg, t_stdev = [throughputs_list[0], throughputs_list[0],
                                                throughputs_list[0], 0]
                l_max, l_min, l_avg, l_stdev = [throughputs_list[0], throughputs_list[0],
                                                throughputs_list[0], 0]
            else:
                t_max, t_min, t_avg, t_stdev = max(throughputs_list), min(throughputs_list), \
                                               statistics.mean(throughputs_list), statistics.stdev(
                    throughputs_list)
                l_max, l_min, l_avg, l_stdev = \
                    max(latencies_list), min(latencies_list),\
                    statistics.mean(latencies_list), statistics.stdev(latencies_list)

            workloads_wstats[workload] = WStat(latency=Stat(l_avg, l_min, l_max, l_stdev),
                                               throughput=Stat(t_avg, t_min, t_max, t_stdev),
                                               count=len(tasks), name=workload)
        return workloads_wstats

    def get_stages_count(self):
        return self.stages_count

    def aep_report(self, experiment_meta: ExperimentMeta, experiment_index: int):
        """
        Compare results from AEP to DRAM:
        1) list all workloads which are run on AEP (Task.workload.name) in stage 3 (or 2)
          a) for all this workloads read performance on DRAM in stage 1
        2) for assertion and consistency we could also check how to compare results in all stages
        3) compare results which we got AEP vs DRAM separately for stage 2 and 3
          a) for each workload:
        """
        # baseline results in stage0 on DRAM
        for i in range(len(self.stages)):
            check = self.get_all_tasks_count_in_stage(0)
            assert check > 5

        workloads_wstats: List[Dict[str, WStat]] = []
        tasks_summaries__per_stage: List[List[Dict]] = []
        node_summaries__per_stage: List[List[Dict]] = []
        workloads_baseline: Dict[str, WStat] = None

        aep_nodes = ClusterInfoLoader.get_instance().get_aep_nodes()

        for stage_index in range(0, self.get_stages_count()):
            workloads_wstat = self.calculate_per_workload_wstats_per_stage(
                workloads=self.get_all_workloads_in_stage(stage_index),
                stage_index=stage_index,
                filter_nodes=aep_nodes)

            workloads_wstats.append(workloads_wstat)

        # Only take nodes node10*
        # @TODO replace with more generic solution, like param in MetaExperiment
        nodes_to_filter = [node for node in
                           self.get_all_nodes_in_stage(experiment_meta.experiment_baseline_index)
                           if node in aep_nodes or not node.startswith('node10')]

        workloads_baseline = self.calculate_per_workload_wstats_per_stage(
            workloads=self.get_all_workloads_in_stage(experiment_meta.experiment_baseline_index),
            stage_index=experiment_meta.experiment_baseline_index,
            filter_nodes=nodes_to_filter)

        for stage_index in range(0, self.get_stages_count()):
            tasks = self.get_all_tasks_in_stage_on_nodes(stage_index=stage_index,
                                                         nodes=self.get_all_nodes_in_stage(
                                                             stage_index))
            # ---
            tasks_summaries = calculate_task_summaries(tasks, workloads_baseline)
            tasks_summaries__per_stage.append(tasks_summaries)
            # ---
            nodes_capacities = ClusterInfoLoader.get_instance().get_nodes()
            nodes_summaries = [self.stages[stage_index].nodes[node].to_dict(nodes_capacities) for
                               node in self.get_all_nodes_in_stage(stage_index)]
            nodes_summaries = [s for s in nodes_summaries if list(s.keys())]
            node_summaries__per_stage.append(nodes_summaries)

        # Transform to DataFrames keeping the same names
        workloads_wstats: List[pd.DataFrame] = [WStat.to_dataframe(el.values()) for el in
                                                workloads_wstats]
        tasks_summaries__per_stage: List[pd.DataFrame] = [pd.DataFrame(el) for el in
                                                          tasks_summaries__per_stage]
        node_summaries__per_stage: List[pd.DataFrame] = [pd.DataFrame(el) for el in
                                                         node_summaries__per_stage]

        tasks_summaries__per_stage: List[pd.DataFrame] = [el.sort_values(by='node') for el in
                                                          tasks_summaries__per_stage]

        exporter = TxtStagesExporter(
            events_data=self.events_data,
            experiment_meta=experiment_meta,
            experiment_index=experiment_index,
            # ---
            export_file_path=os.path.join(experiment_meta.data_path, 'runner_analyzer',
                                          'results.txt'),
            utilization_file_path=os.path.join(experiment_meta.data_path,
                                               'chosen_workloads_utilization.{}.txt'.format(
                                                   experiment_index)),
            # ---
            workloads_summaries=workloads_wstats,
            tasks_summaries=tasks_summaries__per_stage,
            node_summaries=node_summaries__per_stage)

        if experiment_meta.experiment_type == ExperimentType.ThreeStageStandardRun:
            exporter.export_to_txt()
            exporter.export_to_xls()
            exporter.export_to_csv()
        elif experiment_meta.experiment_type == ExperimentType.SingleWorkloadsRun:
            exporter.export_to_txt_single()
        elif experiment_meta.experiment_type == ExperimentType.SteppingSingleWorkloadsRun:
            exporter.export_to_txt_stepping_single()
        else:
            raise Exception('Unsupported experiment type!')

    def analyze_hmem_experiment(self, experiment_meta: ExperimentMeta, experiment_index: int):
        workloads_summaries: List[Dict[str, WStat]] = []
        tasks_summaries__per_stage: List[List[Dict]] = []

        # workload
        for stage_index in range(0, self.get_stages_count()):
            workloads = self.get_all_workloads_in_stage(stage_index)
            workloads_stat = self.calculate_per_workload_wstats_per_stage(
                workloads=workloads,
                stage_index=stage_index)
            workloads_summaries.append(workloads_stat)

        # baseline workload
        workloads = self.get_all_workloads_in_stage(experiment_meta.experiment_baseline_index)
        workloads_baseline = self.calculate_per_workload_wstats_per_stage(
            workloads=workloads,
            stage_index=experiment_meta.experiment_baseline_index)

        # tasks
        for stage_index in range(0, self.get_stages_count()):
            tasks = self.get_all_tasks_in_stage_on_nodes(
                stage_index=stage_index, nodes=self.get_all_nodes_in_stage(stage_index))

            tasks_summaries = calculate_task_summaries(tasks, workloads_baseline)
            tasks_summaries__per_stage.append(tasks_summaries)

        # Transform to DataFrames keeping the same names
        tasks_summaries__per_stage: List[pd.DataFrame] = [pd.DataFrame(el) for el in
                                                          tasks_summaries__per_stage]


def load_events_file(filename):
    # Each python structure in separate file.
    with open(filename) as fref:
        il = 0
        workloads_ = []
        events_ = []
        for line in fref:
            if il % 2 == 0:
                workloads = eval(line)
                if type(workloads) == dict:
                    workloads_.append(workloads)
                else:
                    break
            if il % 2 == 1:
                events = eval(line)
                if type(events) == list:
                    events_.append(events)
                else:
                    break
            il += 1
    assert len(workloads_) == len(events_), 'Wrong content of event file'
    return [(workloads, events) for workloads, events in zip(workloads_, events_)]


def analyze_3stage_experiment(experiment_meta: ExperimentMeta):
    logging.debug('Started work on {}'.format(experiment_meta.data_path))
    events_file = os.path.join(experiment_meta.data_path, 'events.txt')
    report_root_dir = os.path.join(experiment_meta.data_path, 'runner_analyzer')

    # Loads data from event file created in runner stage.
    for i, (workloads, events) in enumerate(load_events_file(events_file)):
        stages_analyzer = StagesAnalyzer(events, workloads)
        if i == 0:
            stages_analyzer.delete_report_files(report_root_dir)

        try:
            stages_analyzer.aep_report(experiment_meta, experiment_index=i)
        except Exception:
            logging.error(
                "Skipping the whole 3stage subexperiment number {} due to exception!".format(i))
            continue


def read_experiment_data(file: str):
    with open(file, 'r') as experiment_data_file:
        json_data = json.load(experiment_data_file)
    return json_data


def main():
    results_dir = '../hmem_experiments/results'
    latex_file = ExperimentResults('Experiment-results')

    analyzer_queries = AnalyzerQueries('http://100.64.176.200:30900')

    for file in os.listdir(results_dir):
        experiment_data = read_experiment_data(os.path.join(results_dir, file))
        t_start = experiment_data["experiment"]["start"]
        t_end = experiment_data["experiment"]["end"]
        description = experiment_data["experiment"]["description"]
        experiment_name = experiment_data["meta"]["name"]
        experiment_type = experiment_data['meta']['params']['type']
        task_counts = experiment_data['meta']['params']['workloads_count']
        tasks: Dict[str, Task] = analyzer_queries.query_tasks_list(t_end)
        analyzer_queries.query_task_performance_metrics(
            t_end, tasks, window_length=int(t_end - t_start))
        latex_file.discover_experiment_data(experiment_name, experiment_type,
                                            tasks, task_counts, description)
    latex_file.generate_pdf()


if __name__ == "__main__":
    main()
