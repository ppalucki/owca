import logging
import os
import signal
import subprocess

from dataclasses import dataclass
from typing import List
from owca.allocators import Allocator, TasksAllocations
from owca.config import load_config
from owca.detectors import TasksMeasurements, TasksResources, TasksLabels, Anomaly
from owca.metrics import Metric
from owca.nodes import Node, Task
from owca.platforms import Platform
from owca.storage import Storage

log = logging.getLogger(__name__)

CPU_PATH = '/sys/fs/cgroup/cpu/{}/tasks'
PERF_PATH = '/sys/fs/cgroup/perf_event/{}/tasks'


@dataclass
class Tester(Node, Allocator, Storage):
    config: str

    def __post_init__(self):
        self.config_data = load_config(self.config)
        self.test_number = 0
        self.metrics = []
        self.pids = []
        self.tasks = List[Task]

    def get_tasks(self) -> List[Task]:
        test_case = self.config_data['tests'][self.test_number]

        if self.test_number > 0:
            # delete processes before
            # delete cgroups
            for check in test_case['checks']:
                # do checks
                pass

            for pid in self.pids:
                _kill_dumb_process(pid)

            for task in self.tasks:
                _delete_cgroup(task.cgroup_path)

            pass

        for task_name in test_case['tasks']:
            name, task_id, cgroup_path = _parse_task_name(task_name)
            task = Task(name=name, task_id=task_id, cgroup_path=cgroup_path)

            _create_cgroup(cgroup_path)

            pid = _create_dumb_process(cgroup_path)
            self.pids.append(pid)

            self.tasks.append(task)

        return self.tasks

    def allocate(self, platform: Platform, tasks_measurements: TasksMeasurements,
                 tasks_resources: TasksResources, tasks_labels: TasksLabels,
                 tasks_allocations: TasksAllocations) -> (
            TasksAllocations, List[Anomaly], List[Metric]):
        pass
        # tu kod ze static_allocatora parsujacy rule
        # z yamka z allocation_rules

    def store(self, metrics: List[Metric]) -> None:
        self.metrics.extend(metrics)


def _parse_task_name(task):
    name = task.split('/')[-1]
    return name, name, task


def _create_dumb_process(task):
    command = ['sleep', 'inf']
    p = subprocess.Popen(command)
    cpu_path, perf_path = _get_cgroup_full_path(task)
    with open(cpu_path, 'a') as f:
        f.write(str(p.pid))
    with open(perf_path, 'a') as f:
        f.write(str(p.pid))

    return p.pid


def _kill_dumb_process(pid):
    os.kill(pid, signal.SIGKILL)


def _get_cgroup_full_path(cgroup):
    return CPU_PATH.format(cgroup), PERF_PATH.format(cgroup)


def _create_cgroup(cgroup_path):
    cpu_path, perf_path = _get_cgroup_full_path(cgroup_path)

    try:
        os.makedirs(cpu_path.format(cgroup_path))
    except FileExistsError:
        log.warning('cpu cgroup "{}" already exists'.format(cgroup_path))

    try:
        os.makedirs(perf_path.format(cgroup_path))
    except FileExistsError:
        log.warning('perf_event cgroup "{}" already exists'.format(cgroup_path))


# TODO: Refactor
def _delete_cgroup(cgroup_path):
    cpu_path, perf_path = _get_cgroup_full_path(cgroup_path)
    command = 'sudo find {0} -depth -type d -print -exec rmdir {{}} \\;'

    try:
        os.system(command.format(cpu_path))
    except FileNotFoundError:
        log.warning('cpu cgroup "{}" not found'.format(cgroup_path))

    try:
        os.system(command.format(perf_path))
    except FileNotFoundError:
        log.warning('perf_event cgroup "{}" not found'.format(cgroup_path))
