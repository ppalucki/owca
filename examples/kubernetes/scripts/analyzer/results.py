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

# https://docs.geoserver.org/latest/en/docguide/installlatex.html
# sudo yum --disablerepo=docker install latexmk texlive-lastpage
# texlive-collection-fontsrecommended texlive-collection-latexrecommended
# texlive-latex-extra
# https://jeltef.github.io/PyLaTeX/current/examples/multirow.html

from typing import List
from pylatex import Document, Section, Subsection, Tabular, VerticalSpace, LineBreak
from pylatex.utils import bold
from datetime import datetime

import metrics
from metrics import Metric
from model import Node

import logging

AVG = 'avg'
Q09 = 'q0.9,'
RATE = 'rate'

NAME = 'name'
UNIT = 'unit'

# METRIC NAMES
AVG_LATENCY = 'avg_latency'
AVG_THROUGHPUT = 'avg_throughput'
Q09_LATENCY = 'q09_latency'
Q09_THROUGHPUT = 'q09_throughput'
MBW_LOCAL = 'mbw_local'
MBW_REMOTE = 'mbw_remote'
NUMA_NODE_0 = 'node0'
NUMA_NODE_1 = 'node1'
NUMA_NODE_2 = 'node2'
NUMA_NODE_3 = 'node3'
NUMA_PAGES = 'numa_pages'


RESULTS_METADATA = {AVG_LATENCY: {NAME: 'Average latency', UNIT: 'ms'},
                    AVG_THROUGHPUT: {NAME: 'Average throughput', UNIT: 'ops'},
                    Q09_LATENCY: {NAME: 'quantile 0.9 latency', UNIT: 'ms'},
                    Q09_THROUGHPUT: {NAME: 'quantile 0.9 throughput', UNIT: 'ops'},
                    NUMA_PAGES: {NAME: 'task numa pages', UNIT: 'GB'},
                    MBW_LOCAL: {NAME: 'memory mbw local', UNIT: 'GB/s'},
                    MBW_REMOTE: {NAME: 'memory mbw remote', UNIT: 'GB/s'}}

MEMORY_SUFFIXES = ['-dram', '-pmem', '-dram-pmem', '-coldstart-toptier', '-toptier', '-coldstart']


class ExperimentResults:
    def __init__(self, name):
        geometry_options = ['a4paper', "margin=0.2in",  "landscape= True"]
        self.doc = Document(name, geometry_options=geometry_options,
                            font_size='small')
        self.sections = {}
        self.results_values = {AVG_LATENCY: {}, AVG_THROUGHPUT: {},
                               Q09_LATENCY: {}, Q09_THROUGHPUT: {},
                               NUMA_NODE_0: {}, NUMA_NODE_1: {},
                               NUMA_NODE_2: {}, NUMA_NODE_3: {}, MBW_LOCAL: {},
                               MBW_REMOTE: {}}
        self.experiment_types = []
        self.name = name

    @staticmethod
    def _get_task_index(task_name):
        index = ''
        for i in range(len(task_name) - 1, 0, -1):
            if task_name[i] == '-':
                break
            else:
                index = task_name[i] + index
        return index

    @staticmethod
    def _strip_memory_suffix(task_name):
        stripped_task_name = task_name
        for memory_suffix in MEMORY_SUFFIXES:
            stripped_task_name = stripped_task_name.replace(memory_suffix, '')
        return stripped_task_name

    def _strip_task_name(self, task_name):
        index = self._get_task_index(task_name)
        stripped_task_name = task_name.replace('default/', '')
        stripped_task_name = stripped_task_name.replace('-{}'.format(index), '')
        return stripped_task_name

    @staticmethod
    def round_metric(metric):
        rounded_metric = round(metric, 3)
        if metric > rounded_metric == 0:
            rounded_metric = '> 0'
        else:
            rounded_metric = format(metric, ",.3f")
        return rounded_metric

    def get_metrics(self, task):
        average_latency = float(task.performance_metrics[Metric.TASK_LATENCY][AVG])
        q09_latency = float(task.performance_metrics[Metric.TASK_LATENCY][Q09])
        if 'pmbench' in task.workload_name:
            average_latency *= 1e6
            q09_latency *= 1e6

        average_latency = self.round_metric(average_latency)
        average_throughput = self.round_metric(
            float(task.performance_metrics[Metric.TASK_THROUGHPUT][AVG]))
        q09_latency = self.round_metric(q09_latency)
        q09_throughput = self.round_metric(
            float(task.performance_metrics[Metric.TASK_THROUGHPUT][Q09]))
        numa_nodes = []
        for i in range(0, 4):
            value = float(task.performance_metrics[Metric.TASK_MEM_NUMA_PAGES][str(i)])\
                    * 4096 / 1e9
            rounded_value = self.round_metric(value)
            numa_nodes.append(rounded_value)

        mbw_local = self.round_metric(
            float(task.performance_metrics[Metric.TASK_MEM_MBW_LOCAL][RATE]) / 1e9)
        mbw_remote = self.round_metric(
            float(task.performance_metrics[Metric.TASK_MEM_MBW_REMOTE][RATE]) / 1e9)

        return average_latency, average_throughput, q09_latency, q09_throughput, \
            numa_nodes, mbw_local, mbw_remote

    @staticmethod
    def create_table():
        name = 'name'
        avg_latency = 'avg latency'
        avg_throughput = 'avg throughput'
        q09_latency = 'q0.9 latency'
        q09_throughput = 'q0.9 throughput'
        mbw_local = 'mbw local'
        mbw_remote = 'mbw remote'
        table = Tabular('|c|c|c|c|c|c|c|c|c|c|c|')
        table.add_hline()
        table.add_row((name, avg_latency, avg_throughput, q09_latency, q09_throughput,
                       NUMA_NODE_0, NUMA_NODE_1, NUMA_NODE_2, NUMA_NODE_3, mbw_local, mbw_remote))
        table.add_hline()
        return table

    @staticmethod
    def create_nodes_table():
        row = ['node', 'socket']
        for metric in metrics.platform_metrics:
            row.append(metrics.MetricLegends[metric]['name'])
        tabular = len(metrics.platform_metrics) + 2
        table = Tabular('|' + 'c|' * tabular)
        table.add_hline()
        table.add_row(row)
        table.add_hline()
        return table

    def discover_experiment_data(self, experiment_name, experiment_type,
                                 tasks, nodes: List[Node], description, start_time):
        if experiment_name not in self.sections.keys():
            self.sections[experiment_name] = Section(experiment_name)
            self.sections[experiment_name].append(description)
            self.sections[experiment_name].append('\nExperiment start time: {}'.format(
                datetime.fromtimestamp(start_time)))
        if experiment_type not in self.experiment_types:
            self.experiment_types.append(experiment_type)
        workloads_results = Subsection('')
        # create table with results
        table = self.create_table()
        for task in tasks:
            average_latency, average_throughput, q09_latency, q09_throughput,\
                numa_nodes, mbw_local, mbw_remote = self.get_metrics(tasks[task])
            table.add_row(
                (tasks[task].name.replace('default/', ''), average_latency,
                 average_throughput, q09_latency, q09_throughput, numa_nodes[0],
                 numa_nodes[1], numa_nodes[2], numa_nodes[3], mbw_local, mbw_remote)
            )
            table.add_hline()

        # create table with node metrics
        node_table = self.create_nodes_table()
        for node in nodes:
            for socket in [0, 1]:
                row = [node.name, socket]
                for metric in metrics.platform_metrics:
                    row.append(
                        self.round_metric(
                            float(node.performance_metrics[socket][metric.name]) /
                            float(metrics.MetricLegends[metric]['helper'])
                        )
                    )
                node_table.add_row(row)
                node_table.add_hline()

        workloads_results.append(table)
        workloads_results.append(VerticalSpace("10pt"))
        workloads_results.append(LineBreak())
        workloads_results.append(node_table)
        self.sections[experiment_name].append(workloads_results)

    def _generate_document(self):
        legend = self.create_unit_legend()
        node_legend = self.create_platform_unit_legend()
        self.doc.append(legend)
        self.doc.append(VerticalSpace("10pt"))
        self.doc.append(LineBreak())
        self.doc.append(node_legend)
        for section in self.sections.values():
            self.doc.append(section)

    def create_unit_legend(self):
        rows = '|c|'
        for _ in RESULTS_METADATA:
            rows += 'c|'
        table = Tabular(rows)
        title_row = [bold('Metric')]
        unit_row = [bold('Unit')]
        for metric in RESULTS_METADATA.keys():
            title_row.append(RESULTS_METADATA[metric][NAME])
            unit_row.append(RESULTS_METADATA[metric][UNIT])
        table.add_hline()
        table.add_row(tuple(title_row))
        table.add_hline()
        table.add_row(tuple(unit_row))
        table.add_hline()
        return table

    @staticmethod
    def create_platform_unit_legend():
        rows = '|c|'
        for _ in metrics.MetricLegends:
            rows += 'c|'
        table = Tabular(rows)
        title_row = [bold('Metric')]
        unit_row = [bold('Unit')]
        for metric in metrics.MetricLegends:
            title_row.append(metrics.MetricLegends[metric]['name'])
            unit_row.append(metrics.MetricLegends[metric]['unit'])
        table.add_hline()
        table.add_row(tuple(title_row))
        table.add_hline()
        table.add_row(tuple(unit_row))
        table.add_hline()
        return table

    def generate_pdf(self):
        self._generate_document()
        self.doc.generate_pdf(clean_tex=True)
        logging.info('Created file: {}'.format(self.name))
