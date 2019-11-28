# Copyright (c) 2019 Intel Corporation
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

from wca.metrics import METRICS_METADATA, MetricGranurality


def prepare_csv_table(data):
    table = '.. csv-table::\n'
    table += '\t:header: "Name", "Help", "Source", "Levels"\n'
    table += '\t:widths: 5, 5, 5, 5 \n\n\t'

    table += '\n\t'.join(['"{}", "{}", "{}", "{}"'.format(*row) for row in data])

    return table


def generate_title(title):
    return title + '\n' + ''.join(['=' for _ in range(len(title))])


def generate_subtitle(subtitle):
    return subtitle + '\n' + ''.join(['-' for _ in range(len(subtitle))])


METRICS_DOC_PATH = 'docs/metrics.rst'

INTRO = """
================================
Available metrics
================================

**This software is pre-production and should not be deployed to production servers.**

.. contents:: Table of Contents

"""

METRICS_SOURCES = """
Metrics sources
===============

Check out `metrics sources documentation <metrics_sources.rst>`_  to learn how measurement them.

"""


def generate_docs():

    task_data = []

    platform_data = []

    internal_data = []

    for metric, metadata in METRICS_METADATA.items():
        if metadata.levels is not None:
            levels = ' '.join(metadata.levels)
        else:
            levels = ''

        data = (metric + ' [%s] (%s)' %  (str(metadata.unit), str(metadata.type)), 
                metadata.help, metadata.source, levels)

        if metadata.granularity == MetricGranurality.INTERNAL:
            internal_data.append(data)
        if metadata.granularity == MetricGranurality.TASK:
            task_data.append(data)
        elif metadata.granularity == MetricGranurality.PLATFORM:
            platform_data.append(data)
        elif metadata.granularity == MetricGranurality.INTERNAL:
            internal_data.append(data)

    tasks = generate_title("Task's metrics") + '\n\n'
    tasks += prepare_csv_table(task_data) + '\n\n'

    platforms = generate_title("Platform's metrics") + '\n\n'
    platforms += prepare_csv_table(platform_data) + '\n\n'

    internal = generate_title("Internal metrics") + '\n\n'
    internal += prepare_csv_table(internal_data) + '\n\n'

    return tasks + '\n\n' + platforms + '\n\n' + internal


if __name__ == '__main__':
    with open(METRICS_DOC_PATH, 'w') as f:
        f.write(INTRO)
        f.write(METRICS_SOURCES)
        f.write(generate_docs())
