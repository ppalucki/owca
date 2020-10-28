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

import enum
import re

from wca.metrics import METRICS_METADATA, MetricGranularity, MetricName
from wca.components import REGISTERED_COMPONENTS
from wca.perf import PerfCgroupDerivedMetricsGenerator
from wca.kubernetes import CgroupDriverType
from wca.perf_uncore import UncoreDerivedMetricsGenerator

API_PATH = 'docs/api.rst'
API_INTRO = """
==============================
Workload Collocation Agent API
==============================

**This software is pre-production and should not be deployed to production servers.**

.. contents:: Table of Contents


"""


class MissingDocstring(Exception):
    pass


SKIPPED_COMPONENTS = [PerfCgroupDerivedMetricsGenerator,
                      UncoreDerivedMetricsGenerator,
                      CgroupDriverType]


def prepare_api_docs():
    docs = ''
    for component in REGISTERED_COMPONENTS:
        if component in SKIPPED_COMPONENTS:
            continue
        docs += generate_title(component.__name__) + '\n'

        try:
            docstring = str(component.__doc__)
            if not docstring.startswith('rst'):
                # docs += '.. code-block:: ' + '\n'
                pass
            else:
                docstring = docstring[3:]
        except TypeError:
            continue  # TODO: Remove after complete doc strings for all components.
            raise MissingDocstring(component.__name__)

        lines = docstring.splitlines(True)
        lines = [remove_trailing_whitespaces(line) for line in lines]
        if len(lines) == 1:
            docs += '\n\t' + docstring
        else:
            docs += ''.join(lines)
        docs += '\n\n'

    return docs


def prepare_csv_table(data, header=True, csv_header=False):
    if header:
        table = '.. csv-table::\n'
        table += '\t:header: "Name", "Help", "Enabled", "Unit", "Type", "Source", "Levels/Labels"\n'
        table += '\t:widths: 5, 5, 5, 5, 5, 5, 5 \n\n\t'
    elif csv_header:
        table = '"Name", "Help", "Enabled", "Unit", "Type", "Source", "Levels/Labels"\n'
    else:
        table = ''

    if header:
        pref = '\t'
    else:
        pref = ''

    table += ('\n%s' % (pref)).join(
            ['"{}", "{}", "{}", "{}",  "{}", "{}", "{}"'.format(*row) for row in data])

    return table


def generate_title(title):
    return title + '\n' + ''.join(['=' for _ in range(len(title))])


def generate_subtitle(subtitle):
    return subtitle + '\n' + ''.join(['-' for _ in range(len(subtitle))])


METRICS_DOC_PATH = 'docs/metrics.rst'
METRICS_CSV_PATH = 'docs/metrics.csv'

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

Check out `metrics sources documentation <metrics_sources.rst>`_ for more details how metrics 
are measured and about labels/levels.

For searchable list of metrics `metrics as csv file <metrics.csv>`_ .

Legend	
======

- **Name**: is the name of metric that will be exported to Prometheus by using Prometheus 
  exposition format but also the name of the key in ``Measurements`` dict-like 
  type used in ``Detector`` and ``Allocator`` plugins,	
- **Help**: information what metric represents and some 
  details how metric was collected and known problems or limitations,	
- **Unit**: unit of the metric (usually seconds or bytes),	
- **Type**: only possible types are `gauge` and `counter` as described 
  in `Prometheus metric types <https://prometheus.io/docs/concepts/metric_types/>`_.	
- **Source**: short description about mechanics that was used to collect metric,	
  for more detailed information check out `Metric sources documenation <metrics_sources.rst>`_.	
- **Enabled** - column describes if metric is enabled by default and 
  how to enable (option in ``MeasurementRunner`` responsible for configuring it. 
  Please refer to `metrics sources documentation <metrics_sources.rst>`_ for more details.)	
- **Levels/Labels** - some metrics have additional dimensions (more granularity than just ``Task`` 
  or ``Platform``) e.g. ``task_mem_numa_pages`` can be collected per NUMA node - in this case	
  this metrics have attached additional label like ``numa_node=0`` which creates new series in	
  Prometheus nomenclature and represents more granular information about source of metric. 
  When used in python API in ``Detector`` or ``Allocator`` classes this will be 
  represented by nested dicts where each level have keys corresponding to "level" (order is important).	
  For example doubly nested perf uncore metrics like: ``platform_cas_count_reads`` 
  have two levels: `socket` and `pmu_type` (which physically represents memory controller) 
  will be encoded as::	

    platform_cas_count_reads{socket=0, pmu_type=17} 12345	

  and represented in Python API as::	

    measurements = {'platform_cas_count_reads': {0: {17: 12345}}}	
"""


def generate_docs(csv=False):

    task_data = []

    platform_data = []

    internal_data = []

    for metric in MetricName.__members__.values():

        metadata = METRICS_METADATA.get(metric)
        if not metadata:
            print('Warning no metadata for metric! %s' % metric)
            continue

        if metadata.levels:
            levels = ', '.join(metadata.levels)
        else:
            levels = ''

        def value_or_str(v):
            if isinstance(v, enum.Enum):
                return str(v.value)
            else:
                return str(v)

        data = (
            metric,
            metadata.help,
            metadata.enabled,
            value_or_str(metadata.unit),
            value_or_str(metadata.type),
            metadata.source,
            levels
        )

        if '"' in metadata.help or '"' in metadata.enabled or '"' in metadata.source:
            raise Exception('help or enabled or source fields cannot contain " '
                            'character! metric=%s' % metric)

        if metadata.granularity == MetricGranularity.TASK:
            task_data.append(data)
        elif metadata.granularity == MetricGranularity.PLATFORM:
            platform_data.append(data)
        elif metadata.granularity == MetricGranularity.INTERNAL:
            internal_data.append(data)

    tasks = generate_title("Task's metrics") + '\n\n' if not csv else ''
    tasks += prepare_csv_table(task_data, header=not csv, csv_header=csv) + '\n\n'

    platforms = generate_title("Platform's metrics") + '\n\n' if not csv else ''
    platforms += prepare_csv_table(platform_data, header=not csv) + '\n\n'

    internal = generate_title("Internal metrics") + '\n\n' if not csv else ''
    internal += prepare_csv_table(internal_data, header=not csv) + '\n\n'

    return tasks + '\n\n' + platforms + '\n\n' + internal


def remove_trailing_whitespaces(line):
    # s = re.search(r'[ \t]+(.*)', line)
    s = re.search(r'    (.*)', line)
    if s:
        return s.group(1) + '\n'
    return line


if __name__ == '__main__':
    with open(METRICS_DOC_PATH, 'w') as f:
        f.write(INTRO)
        f.write(METRICS_SOURCES)
        f.write(generate_docs())
    with open(METRICS_CSV_PATH, 'w') as f:
        f.write(generate_docs(csv=True))
    with open(API_PATH, 'w') as f:
        f.write(API_INTRO)
        f.write(prepare_api_docs())
