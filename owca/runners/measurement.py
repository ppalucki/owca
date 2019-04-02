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
from owca import resctrl
from owca import security
from owca.allocators import AllocationConfiguration
from owca.containers import ContainerManager, Container
from owca.detectors import TasksMeasurements, TasksResources, TasksLabels
from owca.logger import trace
from owca.mesos import create_metrics, sanitize_mesos_label
from owca.metrics import Metric, MetricType
from owca.nodes import Task
from owca.profiling import profiler
from owca.runners import Runner
from owca.storage import MetricPackage, DEFAULT_STORAGE

log = logging.getLogger(__name__)


class MeasurementRunner(Runner):
    """MeasurementRunner run iterations to collect platform, resource, task measurements
    and store them in metrics_storage component.

    Arguments:
        node: component used for tasks discovery
        metrics_storage: storage to store platform, internal, resource and task metrics
            (defaults to DEFAULT_STORAGE/LogStorage to output for standard error)
        action_delay: iteration duration in seconds (None disables wait and iterations)
            (defaults to 1 second)
        rdt_enabled: enables or disabled support for RDT monitoring
            (defaults to None(auto) based on platform capabilities)
        extra_labels: additional labels attached to every metrics
            (defaults to empty dict)
    """

    def __init__(
            self,
            node: nodes.Node,
            metrics_storage: storage.Storage = DEFAULT_STORAGE,
            action_delay: float = 1.,  # [s]
            rdt_enabled: Optional[bool] = None,  # Defaults(None) - auto configuration.
            extra_labels: Dict[str, str] = None,
            _allocation_configuration: Optional[AllocationConfiguration] = None,
    ):

        self._node = node
        self._metrics_storage = metrics_storage
        self._action_delay = action_delay
        self._rdt_enabled = rdt_enabled
        self._extra_labels = extra_labels or dict()
        self._finish = False  # Guard to stop iterations.
        self._last_iteration = time.time()  # Used internally by wait function.
        self._allocation_configuration = _allocation_configuration

    @profiler.profile_duration(name='sleep')
    def _wait(self):
        """Decides how long one iteration should take.
        Additionally calculate residual time, based on time already taken by iteration.
        """
        now = time.time()
        iteration_duration = now - self._last_iteration
        self._last_iteration = now

        residual_time = max(0., self._action_delay - iteration_duration)
        time.sleep(residual_time)

    def run(self) -> int:
        """Loop that gathers platform and tasks metrics and calls _run_body.
        _run_body is a method to be subclassed.
        """
        if not security.are_privileges_sufficient():
            log.error("Impossible to use perf_event_open/resctrl subsystems. "
                      "You need to: adjust /proc/sys/kernel/perf_event_paranoid (set to -1); "
                      "or has CAP_DAC_OVERRIDE and CAP_SETUID capabilities set."
                      "You can run process as root too.")
            return 1

        # Initialization (auto discovery Intel RDT features).
        rdt_available = resctrl.check_resctrl()
        if self._rdt_enabled is None:
            self._rdt_enabled = rdt_available
            log.info('RDT enabled (auto configuration): %s', self._rdt_enabled)
        elif self._rdt_enabled is True and not rdt_available:
            log.error('RDT explicitly enabled but not available - exiting!')
            return 1

        if self._rdt_enabled:
            # Resctrl is enabled and available, call a placeholder to allow further initialization.
            self._initialize_rdt()

        # Post pone the container manager initialization after rdt checks were performed.
        platform_cpus, _, platform_sockets = platforms.collect_topology_information()
        self._containers_manager = ContainerManager(
            self._rdt_enabled,
            rdt_mb_control_enabled=False,
            platform_cpus=platform_cpus,
            allocation_configuration=self._allocation_configuration,
        )

        while True:
            iteration_start = time.time()

            # Get information about tasks.
            tasks = self._node.get_tasks()
            log.debug('Tasks detected: %d', len(tasks))

            # Keep sync of found tasks and internally managed containers.
            containers = self._containers_manager.sync_containers_state(tasks)

            # Platform information
            platform, platform_metrics, platform_labels = platforms.collect_platform_information(
                self._rdt_enabled)

            # Common labels
            common_labels = dict(platform_labels, **self._extra_labels)

            # Tasks data
            tasks_measurements, tasks_resources, tasks_labels = _prepare_tasks_data(containers)
            tasks_metrics = _build_tasks_metrics(tasks_labels, tasks_measurements)

            self._run_body(containers, platform, tasks_measurements, tasks_resources,
                           tasks_labels, common_labels)

            self._wait()

            iteration_duration = time.time() - iteration_start
            profiling.profiler.register_duration('iteration', iteration_duration)

            # Generic metrics.
            metrics_package = MetricPackage(self._metrics_storage)
            metrics_package.add_metrics(_get_internal_metrics(tasks))
            metrics_package.add_metrics(platform_metrics)
            metrics_package.add_metrics(tasks_metrics)
            metrics_package.add_metrics(profiling.profiler.get_metrics())
            metrics_package.send(common_labels)

            if self._finish:
                break

        # Cleanup phase.
        self._containers_manager.cleanup()
        return 0

    def _run_body(self, containers, platform, tasks_measurements, tasks_resources,
                  tasks_labels, common_labels):
        """No-op implementation of inner loop body"""

    def _initialize_rdt(self):
        """Nothing to configure in RDT to measure resource usage."""


@profiler.profile_duration('prepare_tasks_data')
@trace(log, verbose=False)
def _prepare_tasks_data(containers: Dict[Task, Container]) -> \
        Tuple[TasksMeasurements, TasksResources, TasksLabels]:
    """Prepare all resource usage and resource allocation information and
    creates container-specific labels for all the generated metrics.
    """
    # Prepare empty structures for return all the information.
    tasks_measurements: TasksMeasurements = {}
    tasks_resources: TasksResources = {}
    tasks_labels: TasksLabels = {}

    for task, container in containers.items():
        # Task measurements and measurements based metrics.
        task_measurements = container.get_measurements()
        if not task_measurements:
            log.warning('there is not measurements collected for container %r - ignoring!',
                        container)
            continue

        # Prepare tasks labels based on tasks metadata labels and task id.
        task_labels = {
            sanitize_mesos_label(label_key): label_value
            for label_key, label_value
            in task.labels.items()
        }
        task_labels['task_id'] = task.task_id

        # Aggregate over all tasks.
        tasks_labels[task.task_id] = task_labels
        tasks_measurements[task.task_id] = task_measurements
        tasks_resources[task.task_id] = task.resources

    return tasks_measurements, tasks_resources, tasks_labels


def _build_tasks_metrics(tasks_labels: TasksLabels,
                         tasks_measurements: TasksMeasurements) -> List[Metric]:
    tasks_metrics: List[Metric] = []

    for task_id, task_measurements in tasks_measurements.items():
        task_metrics = create_metrics(task_measurements)
        # Decorate metrics with task specific labels.
        for task_metric in task_metrics:
            task_metric.labels.update(tasks_labels[task_id])
        tasks_metrics += task_metrics
    return tasks_metrics


def _get_internal_metrics(tasks: List[Task]) -> List[Metric]:
    """Internal owca metrics e.g. memory usage, profiling information."""

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

    return metrics
