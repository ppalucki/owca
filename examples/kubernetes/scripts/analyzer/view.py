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
from typing import List, Tuple, Optional
import pandas as pd
from dataclasses import dataclass
import logging
from model import ExperimentMeta


@dataclass
class TxtStagesExporter:
    events_data: Tuple[List, List]
    experiment_meta: ExperimentMeta
    experiment_index: int
    export_file_path: str
    utilization_file_path: str

    workloads_summaries: List[pd.DataFrame]
    tasks_summaries: List[pd.DataFrame]
    node_summaries: List[pd.DataFrame]

    def __post_init__(self):
        # @TODO remove
        self.limits = {'L[%]': 150, 'T[%]': 80}

    def export_to_txt_single(self):
        logging.debug("Saving results to {}".format(self.export_file_path))

        runner_analyzer_results_dir = os.path.join(self.experiment_meta.data_path,
                                                   'runner_analyzer')
        if not os.path.isdir(runner_analyzer_results_dir):
            os.mkdir(runner_analyzer_results_dir)

        with open(os.path.join(runner_analyzer_results_dir, 'results.txt'), 'a+') as fref:
            self._fref = fref

            self._seperator()
            self._metadata()
            self._baseline(stage_index=1)
            self._tasks_summaries_in_stage(stage_index=1, title='Task summaries for all tasks')
            self._seperator(ending=True)

            self._fref = None

    def export_to_txt_stepping_single(self):
        logging.debug("Saving results to {}".format(self.export_file_path))

        runner_analyzer_results_dir = os.path.join(self.experiment_meta.data_path,
                                                   'runner_analyzer')
        if not os.path.isdir(runner_analyzer_results_dir):
            os.mkdir(runner_analyzer_results_dir)

        with open(os.path.join(runner_analyzer_results_dir, 'results.txt'), 'a+') as fref:
            self._fref = fref
            self._seperator()
            self._metadata()
            self._seperator(ending=True)
            for stage_index in range(len(self.workloads_summaries)):
                self._seperator()
                self._baseline(title="DRAM workload summary", stage_index=stage_index)
                self._tasks_summaries_in_stage(stage_index=stage_index,
                                               title='Task summaries for PMEM:node101',
                                               filter_nodes=['node101'])
                self._tasks_summaries_in_stage(stage_index=stage_index,
                                               title='Task summaries for DRAM:node103',
                                               filter_nodes=['node103'])
                self._node_summaries_in_stage(stage_index=stage_index,
                                              title='Node summaries for DRAM:node103',
                                              filter_nodes=['node103'])
                self._seperator(ending=True)
            self._fref = None

    def _print_summaries_in_stage(self, df, title):
        self._fref.write('\n{}\n'.format(title))
        self._fref.write(df.to_string())
        self._fref.write('\n')

    def _tasks_summaries_in_stage(self, title: str, stage_index: int,
                                  filter_nodes: Optional[List[str]] = None):
        df = self.tasks_summaries[stage_index]  # df == dataframe
        if filter_nodes is not None:
            df = df[df.node.isin(filter_nodes)]

        self._print_summaries_in_stage(df, title)

    def _node_summaries_in_stage(self, title: str, stage_index: int,
                                 filter_nodes=Optional[List[str]]):
        df = self.node_summaries[stage_index]  # df == dataframe
        if filter_nodes is not None:
            df = df[df.name.isin(filter_nodes)]

        self._print_summaries_in_stage(df, title)

    def multiple_dfs(self, df_list, sheets, file_name, spaces):
        writer = pd.ExcelWriter(file_name, engine='xlsxwriter')
        row = 0
        for dataframe in df_list:
            dataframe.to_excel(writer, sheet_name=sheets, startrow=row, startcol=0)
            row = row + len(dataframe.index) + spaces + 1
        writer.save()

    def export_to_xls(self):
        logging.debug("Saving xls to {} for experiment {}".format(self.export_file_path,
                                                                  self.experiment_index))

        runner_analyzer_results_dir = os.path.join(self.experiment_meta.data_path,
                                                   'runner_analyzer')
        if not os.path.isdir(runner_analyzer_results_dir):
            os.mkdir(runner_analyzer_results_dir)

        with pd.ExcelWriter(os.path.join(runner_analyzer_results_dir,
                                         'tasks_summaries_{}.xlsx'.format(
                                             self.experiment_index))) as writer:
            self.tasks_summaries[0].to_excel(writer, sheet_name='BASELINE')
            self.tasks_summaries[1].to_excel(writer, sheet_name='KUBERNETES_BASELINE')
            self.tasks_summaries[2].to_excel(writer, sheet_name='WCA-SCHEDULER')

        with pd.ExcelWriter(os.path.join(runner_analyzer_results_dir,
                                         'node_summaries_{}.xlsx'.format(
                                             self.experiment_index))) as writer:
            self.node_summaries[0].to_excel(writer, sheet_name='BASELINE')
            self.node_summaries[1].to_excel(writer, sheet_name='KUBERNETES_BASELINE')
            self.node_summaries[2].to_excel(writer, sheet_name='WCA-SCHEDULER')

        with pd.ExcelWriter(os.path.join(runner_analyzer_results_dir,
                                         'workloads_summaries_{}.xlsx'.format(
                                             self.experiment_index))) as writer:
            self.workloads_summaries[0].to_excel(writer, sheet_name='BASELINE')
            self.workloads_summaries[1].to_excel(writer, sheet_name='KUBERNETES_BASELINE')
            self.workloads_summaries[2].to_excel(writer, sheet_name='WCA-SCHEDULER')

    def export_to_csv(self):
        logging.debug("Saving results to {}".format(self.export_file_path))

        runner_analyzer_results_dir = os.path.join(self.experiment_meta.data_path,
                                                   'runner_analyzer')
        if not os.path.isdir(runner_analyzer_results_dir):
            os.mkdir(runner_analyzer_results_dir)

        self.tasks_summaries[0].to_csv(
            os.path.join(runner_analyzer_results_dir,
                         'tasks_summaries_{}_BASELINE.csv'.format(
                             self.experiment_index)))
        self.tasks_summaries[1].to_csv(
            os.path.join(runner_analyzer_results_dir,
                         'tasks_summaries_{}_KUBERNETES_BASELINE.csv'.format(
                             self.experiment_index)))
        self.tasks_summaries[2].to_csv(
            os.path.join(runner_analyzer_results_dir,
                         'tasks_summaries_{}_WCA-SCHEDULER.csv'.format(
                             self.experiment_index)))

        self.node_summaries[0].to_csv(
            os.path.join(runner_analyzer_results_dir,
                         'node_summaries_{}_BASELINE.csv'.format(
                             self.experiment_index)))
        self.node_summaries[1].to_csv(
            os.path.join(runner_analyzer_results_dir,
                         'node_summaries_{}_KUBERNETES_BASELINE.csv'.format(
                             self.experiment_index)))
        self.node_summaries[2].to_csv(
            os.path.join(runner_analyzer_results_dir,
                         'node_summaries_{}_WCA-SCHEDULER.csv'.format(
                             self.experiment_index)))

        self.workloads_summaries[0].to_csv(
            os.path.join(runner_analyzer_results_dir,
                         'workloads_summaries_{}_BASELINE.csv'.format(
                             self.experiment_index)))
        self.workloads_summaries[1].to_csv(
            os.path.join(runner_analyzer_results_dir,
                         'workloads_summaries_{}_KUBERNETES_BASELINE.csv'.format(
                             self.experiment_index)))
        self.workloads_summaries[2].to_csv(
            os.path.join(runner_analyzer_results_dir,
                         'workloads_summaries_{}_WCA-SCHEDULER.csv'.format(
                             self.experiment_index)))

    def export_to_txt(self):
        logging.debug("Saving results to {} for experiment {}".format(self.export_file_path,
                                                                      self.experiment_index))

        runner_analyzer_results_dir = os.path.join(self.experiment_meta.data_path,
                                                   'runner_analyzer')
        if not os.path.isdir(runner_analyzer_results_dir):
            os.mkdir(runner_analyzer_results_dir)

        with open(os.path.join(runner_analyzer_results_dir, 'results.txt'), 'a+') as fref:
            self._fref = fref

            self._seperator()
            self._metadata()
            self._baseline()
            self._aep_tasks()
            self._seperator(ending=True)

            self._fref = None

    def _seperator(self, ending=False):
        self._fref.write('*' * 90 + '\n')
        if ending:
            self._fref.write('\n\n')

    def _metadata(self):
        self._fref.write("Experiment index: {}\n".format(self.experiment_index))
        self._fref.write("Time events from: {} to: {}.\n".format(
            self.events_data[0][0][0].strftime("%d-%b-%Y (%H:%M:%S)"),
            self.events_data[0][-1][0].strftime("%d-%b-%Y (%H:%M:%S)")))

        workloads_list = ["({}, {})".format(workload, count) for workload, count in
                          self.events_data[1].items()]
        workloads_list = sorted(workloads_list)
        self._fref.write(
            "Workloads scheduled: {}\n{}".format(len(workloads_list),
                                                 self.print_n_per_row(n=5, list_=workloads_list)))

        if os.path.isfile(self.utilization_file_path):
            utilization = open(self.utilization_file_path).readlines()[0].rstrip()
            self._fref.write("Utilization of resources: {}\n".format(utilization))
        else:
            self._fref.write("Utilization of resources: unknown\n")

    def _baseline(self, title="BASELINE", stage_index=0):
        self._fref.write("***{}(stage_index={})***\n".format(title, stage_index))
        self._fref.write(str(self.workloads_summaries[stage_index].to_string()))
        self._fref.write('\n\n')
        self._fref.write(str(self.node_summaries[stage_index].to_string()))
        self._fref.write('\n\n')
        self._fref.write(str(self.tasks_summaries[stage_index].to_string()))
        self._fref.write('\n\n')

    def _aep_tasks(self):
        for istage, title in (1, "KUBERNETES BASELINE"), (2, "WCA-SCHEDULER"):
            self._fref.write("\n***{}***\n".format(title))
            self._fref.write(str(self.node_summaries[istage].to_string()))
            self._fref.write('\n\n')
            self._fref.write(str(self.tasks_summaries[istage].to_string()))
            self._fref.write('\n\n')
            # ---
            self._fref.write('Passed {}/{} avg limit >>{}<<\n'.format(
                len([val for val in self.tasks_summaries[istage]['pass_avg'] if val]),
                len(self.tasks_summaries[istage]['pass_avg']), self.limits))
            self._fref.write('Passed {}/{} optimistic limit >>{}<<\n'.format(
                len([val for val in self.tasks_summaries[istage]['pass_nice'] if val]),
                len(self.tasks_summaries[istage]['pass_nice']), self.limits))
            self._fref.write('Passed {}/{} strict limit >>{}<<\n'.format(
                len([val for val in self.tasks_summaries[istage]['pass_strict'] if val]),
                len(self.tasks_summaries[istage]['pass_strict']), self.limits))

    def print_n_per_row(n, list_):
        r = ""
        for i in range(int((len(list_) + 1) / n)):
            k = i * n
            m = k + n if k + n < len(list_) else len(list_)
            r += ", ".join(list_[k:m])
            r += '\n'
        return r
