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
import resource
import time
from typing import Dict, List, Tuple, Optional

from owca import nodes, storage, platforms, profiling
from owca.allocators import AllocationConfiguration
from owca.containers import ContainerManager, Container
from owca.detectors import TasksMeasurements, TasksResources, TasksLabels
from owca.logger import trace
from owca.mesos import create_metrics, sanitize_mesos_label
from owca.metrics import Metric, MetricType
from owca.nodes import Task
from owca.profiling import profile_duration
from owca.resctrl import check_resctrl
from owca.runners import Runner
from owca.security import are_privileges_sufficient
from owca.storage import MetricPackage

log = logging.getLogger(__name__)


class MeasurementRunner(Runner):

    def __init__(
            self,
            node: nodes.Node,
            metrics_storage: storage.Storage,
            action_delay: float = 0.,  # [s]
            rdt_enabled: bool = True,
            extra_labels: Dict[str, str] = None,
            ignore_privileges_check: bool = False,
            allocation_configuration: Optional[AllocationConfiguration] = None,
    ):

        self._node = node
        self._metrics_storage = metrics_storage
        self._action_delay = action_delay
        self._rdt_enabled = rdt_enabled
        self._extra_labels = extra_labels or dict()
        self._ignore_privileges_check = ignore_privileges_check

        platform_cpus, _, platform_sockets = platforms.collect_topology_information()
        self.containers_manager = ContainerManager(
            self._rdt_enabled,
            rdt_mb_control_enabled=False,
            platform_cpus=platform_cpus,
            allocation_configuration=allocation_configuration,
        )

        self._last_iteration = time.time()

    @profile_duration(name='sleep')
    def _wait_or_finish(self):
        """Decides how long one run takes and when to finish."""
        # Iteration_duration.
        now = time.time()
        iteration_duration = now - self._last_iteration
        self._last_iteration = now

        residual_time = max(0., self._action_delay - iteration_duration)
        time.sleep(residual_time)
        return True

    def _get_internal_metrics(self, tasks) -> List[Metric]:
        """Internal owca metrics."""

        # Memory usage.
        memory_usage_rss_self = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
        memory_usage_rss_children = resource.getrusage(resource.RUSAGE_CHILDREN).ru_maxrss
        memory_usage_rss = memory_usage_rss_self + memory_usage_rss_children

        metrics = [
            Metric(name='owca_up', type=MetricType.COUNTER, value=time.time()),
            Metric(name='owca_tasks', type=MetricType.GAUGE, value=len(tasks)),
            Metric(name='owca_memory_usage_bytes', type=MetricType.GAUGE,
                   value=int(memory_usage_rss * 1024)),
        ]

        # Profiling metrics.
        metrics.extend(profiling.get_profiling_metrics())

        return metrics

    @profile_duration(name='iteration')
    def run(self):
        # Initialization.
        if self._rdt_enabled and not check_resctrl():
            return
        elif not self._rdt_enabled:
            log.warning('Rdt disabled. Skipping collecting measurements '
                        'and resctrl synchronization')
        else:
            # Resctrl is enabled and available, call a placholder to allow further initialization.
            self._rdt_initialization()

        if not self._ignore_privileges_check and not are_privileges_sufficient():
            log.critical("Impossible to use perf_event_open. You need to: adjust "
                         "/proc/sys/kernel/perf_event_paranoid; or has CAP_DAC_OVERRIDE capability"
                         " set. You can run process as root too. See man 2 perf_event_open for "
                         "details.")
            return

        while True:
            # Get information about tasks.
            tasks = self._node.get_tasks()

            # Keep sync of found tasks and internally managed containers.
            containers = self.containers_manager.sync_containers_state(tasks)

            # Platform information
            platform, platform_metrics, platform_labels = platforms.collect_platform_information(
                self._rdt_enabled)

            # Common labels
            common_labels = dict(platform_labels, **self._extra_labels)

            # Tasks data
            tasks_metrics, tasks_measurements, tasks_resources, tasks_labels = \
                _prepare_tasks_data(containers)

            internal_metrics = self._get_internal_metrics(tasks)

            metrics_package = MetricPackage(self._metrics_storage)
            metrics_package.add_metrics(internal_metrics)
            metrics_package.add_metrics(platform_metrics)
            metrics_package.add_metrics(tasks_metrics)
            metrics_package.send(common_labels)

            self._run_body(containers, platform, tasks_measurements, tasks_resources,
                           tasks_labels, common_labels)

            if not self._wait_or_finish():
                break

        # Cleanup phase.
        self.containers_manager.cleanup()

    def _run_body(self, containers, platform, tasks_measurements, tasks_resources,
                  tasks_labels, common_labels):
        """No-op implementation of inner loop body"""

    def _rdt_initialization(self):
        """Nothing to do in RDT during detection."""


@profile_duration(name='prepare_task_data')
@trace(log, verbose=False)
def _prepare_tasks_data(containers: Dict[Task, Container]) -> \
        Tuple[List[Metric], TasksMeasurements, TasksResources, TasksLabels]:
    """ Based on containers, prepare all necessary data for allocation and detection logic,
    including, measurements, resources, labels and derived metrics.
    In runner to fulfil common data requirements for Allocator and Detector class.
    """
    # Prepare empty structures for return all the information.
    tasks_measurements: TasksMeasurements = {}
    tasks_resources: TasksResources = {}
    tasks_labels: TasksLabels = {}
    tasks_metrics: List[Metric] = []

    for task, container in containers.items():
        # Task measurements and measurements based metrics.
        task_measurements = container.get_measurements()
        if not task_measurements:
            log.warning('there is not measurements collected for container %r - ignoring!',
                        container)
            continue

        task_metrics = create_metrics(task_measurements)

        # Prepare tasks labels based on tasks metadata labels and task id.
        task_labels = {
            sanitize_mesos_label(label_key): label_value
            for label_key, label_value
            in task.labels.items()
        }
        task_labels['task_id'] = task.task_id

        # Decorate metrics with task specific labels.
        for task_metric in task_metrics:
            task_metric.labels.update(task_labels)

        # Aggregate over all tasks.
        tasks_labels[task.task_id] = task_labels
        tasks_measurements[task.task_id] = task_measurements
        tasks_resources[task.task_id] = task.resources
        tasks_metrics += task_metrics

    return tasks_metrics, tasks_measurements, tasks_resources, tasks_labels
