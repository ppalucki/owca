# Copyright (c) 2018 Intel Corporation
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

import logging
import re
import subprocess
import threading
import time
from typing import List, Dict

from dataclasses import dataclass

from wca.config import Str, ValidationError
from wca.logger import TRACE
from wca.metrics import Metric

GROUP_LABEL_RE_PREFIX = 'LABEL_'
GROUP_METRIC_RE_PREFIX = 'METRIC_'

log = logging.getLogger(__name__)


@dataclass
class External:
    """rst

    External is an abstraction to provide source for generating metrics from "external" source.
    It runs "args" as subprocess, connects to its stdout output and parser every line using
    regexp. Each parsed line can generated many labeled metrics.
    Regexp uses groups to find metric value and extend metric to name with suffix and metric label
    "LABEL_" to extract label names and values.

    E.g. let's assume simple line from application output:

    ``qps read 123``

    and we want to extract: ``qps`` as suffix, ``read`` as label and ``123`` as value,
    then regexp should look like this:

    ``(\\S+) (?P<LABEL_operation) (?P<METRIC_qps>)``

    When configured as ``metric_base_name: foo``, will generate metric

    ``Metric(name='foo_qps', labels={'operation':'read', value=132)``

    or

    ``foo_qps{operation="load"} 132.0``


    - ``args``: **List[Str]**

        Arguments to start external process, that output will be read to parse by regexp.

    - ``regexp``: **Str**

        Regexp to parse output from external process.
        Has to contain "METRIC_" prefixed group to indicate location of value and suffix
        that will be added to metric_base_name.
        May contain "LABEL_" prefixed group to indicate location of value of label.

    - ``labels``: **Dict[Str, Str]**

        Base labels to be added to every generated metric.

    - ``restart_delay``: **int** = 60

        Number of seconds to wait between restarting process in case of failure.

    Please check ``configs/extra/external_measurements.yaml`` for more examples.
    """

    args: List[Str]
    regexp: Str
    metric_base_name: Str
    labels: Dict[Str, Str]
    restart_delay: int = 60  # seconds

    def __post_init__(self):
        # parse regexp
        try:
            self._regexp = re.compile(self.regexp)
        except re.error as e:
            raise ValidationError('broken regexp: %s' % e)

        valid_prefix = all(
            (k.startswith(GROUP_LABEL_RE_PREFIX) or k.startswith(GROUP_METRIC_RE_PREFIX))
            for k in self._regexp.groupindex.keys())
        if not valid_prefix:
            raise ValidationError('all External regexp groups should start with %s or %s prefix' %
                                  (GROUP_METRIC_RE_PREFIX, GROUP_METRIC_RE_PREFIX))

        with_metric_perfix = len(
            [k for k in self._regexp.groupindex.keys() if k.startswith(GROUP_METRIC_RE_PREFIX)])
        if with_metric_perfix < 1:
            raise ValidationError('External regexp requires at least on group with %s prefix' %
                                  GROUP_METRIC_RE_PREFIX)

    def start(self):
        self._thread = threading.Thread(target=self.measure, daemon=False)
        self._process = None
        self._metrics = []
        self._thread.start()

    def measure(self):
        while True:
            process_name = ' '.join(self.args)
            log.debug('starting process: %r', process_name)
            self._process = subprocess.Popen(
                self.args, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            alive = True
            while alive:
                if self._process.poll() is not None:
                    log.debug('process %r is dead: rc=%r stderr=%r', process_name,
                              self._process.returncode, self._process.stderr.read())
                    alive = False
                    # reset metrics
                    self._metrics = []
                    continue

                line = self._process.stdout.readline().decode('utf8')
                log.log(TRACE, 'found process=%r line: %r', process_name, line)
                match = self._regexp.match(line)
                if not match:
                    continue

                # Generate many metrics based on regexp results.
                labels = dict(self.labels)
                values = {}
                found = match.groupdict()
                for key_found, value_found in found.items():
                    if key_found.startswith(GROUP_LABEL_RE_PREFIX):
                        label_name = key_found.lstrip(GROUP_LABEL_RE_PREFIX)
                        label_value = str(value_found)
                        labels[label_name] = label_value

                    if key_found.startswith(GROUP_METRIC_RE_PREFIX):
                        metric_suffix = key_found.lstrip(GROUP_METRIC_RE_PREFIX)
                        metric_value = float(value_found)
                        values[metric_suffix] = metric_value

                log.log(TRACE, 'process=%r labels=%r values=%r', process_name, labels, values)
                metrics = [
                    Metric(
                        name=self.metric_base_name + metric_suffix,
                        value=metric_value,
                        labels=dict(labels)
                    )
                    for metric_suffix, metric_value in values.items()
                ]
                self._metrics = metrics

            log.debug('waiting %ss to restart process %r', self.restart_delay, process_name)
            time.sleep(self.restart_delay)

    def get_metrics(self) -> List[Metric]:
        return list(self._metrics)


@dataclass
class MultiExternal:
    """rst

    MultiExternal is helper over External object to generate many indentical ``External`` objects
    where values of "args", "labels" and "regexp" or "metric_base_name" will be templated
    by provided ``key`` and its ``values``.

    For example: if ``External(args=['foo','barBAZbar'], ...)`` is wrapped by ``MultiExternal``
    with ``key: 'BAZ'`` and ``values: ['_first_', '_second_']``, then ``MultiExternal`` will create
    and manage two ``External`` objects:

    - ``External(args=['foo','bar_first_bar'], ...)``
    - ``External(args=['foo','bar_second_bar'], ...)``

    Metrics gathered from ``MultiExternal`` is an union of all metrics from all the ``External``
    objects.


    - ``key``: **Str**

        The value of string, to be replaced by ``values`` (e.g. field.replace(key, value))

    - ``values``: **List[Str]**

        Regexp to parse output from external process.
        Has to contain "METRIC_" prefixed group to indicate location of value and suffix
        that will be added to metric_base_name.
        May contains "LABEL_" prefixed group to indicate location of value of label.


    Rest of arguments is described in ``External`` object above.

    Please check ``configs/extra/external_measurements.yaml`` for more examples.
    """

    key: str
    values: List[str]
    # as for single external (the key will be replaced with values)
    args: List[str]
    regexp: str
    metric_base_name: str
    labels: Dict[str, str]
    restart_delay: int = 60  # seconds

    def __post_init__(self):
        self._externals = []
        for value in self.values:
            self._externals.append(
                External(
                    args=[a.replace(self.key, value) for a in self.args],
                    regexp=self.regexp.replace(self.key, value),
                    metric_base_name=self.metric_base_name.replace(self.key, value),
                    labels={l.replace(self.key, value): v.replace(self.key, value)
                            for l, v in self.labels.items()},
                    restart_delay=self.restart_delay
                )
            )

    def start(self):
        for external in self._externals:
            external.start()

    def get_metrics(self):
        metrics = []
        for external in self._externals:
            metrics.extend(external.get_metrics())
        return metrics
