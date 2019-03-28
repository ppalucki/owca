import abc
import time
import logging
import sys
import os
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

CPU_PATH = '/sys/fs/cgroup/cpu{}'
PERF_PATH = '/sys/fs/cgroup/perf_event{}'


@dataclass
class Tester(Node, Allocator, Storage):
    config: str

    def __post_init__(self):
        self.config_data = load_config(self.config)
        self.test_current = 1
        self.test_number = len(self.config_data['tests'])
        self.metrics = []
        self.processes: List[subprocess.Popen] = []
        self.tasks = []

    def get_tasks(self) -> List[Task]:

        # Check if all test cases.
        if self.test_current > self.test_number:
            self._clean_processes()
            time.sleep(0.1)
            self._clean_cgroups()
            log.info('All tests passed')
            sys.exit(0)

        # Save current test case.
        test_case = self.config_data['tests'][self.test_current - 1]

        # Checks can be done after first test case.
        if self.test_current > 1:
            for check in test_case['checks']:
                pass

            self._clean_processes()
            time.sleep(0.1)
            self._clean_cgroups()

        self.tasks = []

        for task_name in test_case['tasks']:
            name, task_id, cgroup_path = _parse_task_name(task_name)
            labels = dict()
            resources = dict()
            task = Task(name, task_id, cgroup_path, labels, resources)

            _create_cgroup(cgroup_path)

            process = _create_dumb_process(cgroup_path)
            self.processes.append(process)

            self.tasks.append(task)

        self.test_current += 1

        return self.tasks

    def allocate(self, platform: Platform, tasks_measurements: TasksMeasurements,
                 tasks_resources: TasksResources, tasks_labels: TasksLabels,
                 tasks_allocations: TasksAllocations) -> (

            TasksAllocations, List[Anomaly], List[Metric]):
        return {}, list(), list()
        # tu kod ze static_allocatora parsujacy rule
        # z yamka z allocation_rules

    def store(self, metrics: List[Metric]) -> None:
        self.metrics.extend(metrics)

    def _clean_processes(self):
        for process in self.processes:
            process.terminate()
        self.processes.clear()

    def _clean_cgroups(self):
        for task in self.tasks:
            _delete_cgroup(task.cgroup_path)


def _parse_task_name(task):
    splitted = task.split('/')
    name = splitted[-1]

    if len(splitted) > 1:
        return name, name, task

    return name, name, '/{}'.format(task)


def _create_dumb_process(cgroup_path):
    command = ['sleep', 'inf']
    p = subprocess.Popen(command)
    cpu_path, perf_path = _get_cgroup_full_path(cgroup_path)

    with open('{}/tasks'.format(cpu_path), 'a') as f:
        f.write(str(p.pid))
    with open('{}/tasks'.format(perf_path), 'a') as f:
        f.write(str(p.pid))

    return p


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


def _delete_cgroup(cgroup_path):
    cpu_path, perf_path = _get_cgroup_full_path(cgroup_path)

    try:
        os.rmdir(cpu_path)
    except FileNotFoundError:
        log.warning('cpu cgroup "{}" not found'.format(cgroup_path))

    try:
        os.rmdir(perf_path)
    except FileNotFoundError:
        log.warning('perf_event cgroup "{}" not found'.format(cgroup_path))


class Check(abc.ABC):
    @abc.abstractmethod
    def check(self):
        pass
