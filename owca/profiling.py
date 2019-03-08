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
# Stores information about latest call durations for given function names in seconds.

import time
from typing import List

from owca.metrics import Metric, MetricType

_durations = {}


def profile_duration(function_to_profile=None, name=None):
    """Decorator for profiling execution time."""

    def _profile_duration(function_to_profile):
        def _inner(*args, **kwargs):
            start = time.time()
            rv = function_to_profile(*args, **kwargs)
            duration = time.time() - start
            _durations[name or function_to_profile.__name__] = duration
            return rv

        return _inner

    if function_to_profile is None:
        return _profile_duration

    return _profile_duration(function_to_profile)


def register_duration(function_name: str, duration: float):
    _durations[function_name] = duration


def get_profiling_metrics() -> List[Metric]:
    metrics = []
    for duration_name, duration_value in sorted(_durations.items()):
        metrics.append(
            Metric(name='owca_duration_seconds',
                   type=MetricType.GAUGE, value=duration_value,
                   labels=dict(function=duration_name),
                   ),
        )
    return metrics
