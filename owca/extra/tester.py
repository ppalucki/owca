import abc
import time
import logging
import sys
import os
import subprocess

from dataclasses import dataclass
from typing import List, Dict, Set, Union, Optional

from owca.allocators import Allocator, TasksAllocations
from owca.config import load_config
from owca.detectors import TasksMeasurements, TasksResources, TasksLabels, Anomaly
from owca.metrics import Metric
from owca.nodes import Node, Task
from owca.platforms import Platform
from owca.storage import Storage
from owca.testing import assert_metric

log = logging.getLogger(__name__)

CPU_PATH = '/sys/fs/cgroup/cpu'
PERF_PATH = '/sys/fs/cgroup/perf_event'


@dataclass
class Tester(Node, Allocator, Storage):
    config: str
    command: Optional[str] = None

    def __post_init__(self):
        self.testcases = load_config(self.config)['tests']
        self.testcases_count = len(self.testcases)
        self.current_iteration = 0
        self.processes: Dict[str, subprocess.Popen] = {}
        self.tasks: List[Task] = []

        # To keep between consecutive get_tasks calls.
        self.metrics = []
        self.checks = []

    def get_tasks(self) -> List[Task]:
        self.current_iteration += 1

        # Checks can be done after first test case.
        if self.current_iteration > 1:
            for check_case in self.checks:
                check_case: Check
                try:
                    check_case.check(self.metrics)
                except CheckFailed:
                    # Clean tests processes and cgroups after failure.
                    self._clean_tasks()
                    raise

            self.metrics.clear()

        # Check if all test cases.
        if self.current_iteration > self.testcases_count:
            self._clean_tasks()
            log.info('All tests passed')
            sys.exit(0)
            return

        # Save current test case.
        test_case = self.testcases[self.current_iteration - 1]

        # Save checks from this test case.
        self.checks = test_case['checks']

        # Modify current task list.
        tasks_to_check = test_case['tasks']
        tasks_to_stay = []
        cgroup_to_stay = []

        for task_name in test_case['tasks']:
            for task in self.tasks:
                task: Task
                if task.cgroup_path == task_name:
                    tasks_to_stay.append(task)
                    cgroup_to_stay.append(task_name)
                    tasks_to_check.remove(task_name)

        self._clean_tasks(cgroup_to_stay)

        self.tasks = tasks_to_stay

        for task_name in tasks_to_check:
            name, task_id, cgroup_path = _parse_task_name(task_name)
            subgroups_paths = []
            labels = {}
            resources = {}
            task = Task(name, task_id, cgroup_path, subgroups_paths, labels, resources)
            _create_cgroup(cgroup_path)

            if self.command:
                process = _create_dumb_process(cgroup_path, self.command)
                self.processes[cgroup_path] = process

            self.tasks.append(task)

        return self.tasks

    def allocate(
            self,
            platform: Platform,
            tasks_measurements: TasksMeasurements,
            tasks_resources: TasksResources,
            tasks_labels: TasksLabels,
            tasks_allocations: TasksAllocations,
    ) -> (TasksAllocations, List[Anomaly], List[Metric]):

        allocator = self.testcases[self.current_iteration - 1]['allocator']

        return allocator.allocate(
                platform, tasks_measurements, tasks_resources, tasks_labels, tasks_allocations)

    def store(self, metrics: List[Metric]) -> None:
        self.metrics.extend(metrics)

    def _clean_tasks(self, excepts: Set[str] = []):

        if self.processes:
            new_processes = {}

            # Terminate all tasks.
            for cgroup in self.processes:
                if cgroup not in excepts:
                    self.processes[cgroup].terminate()
                else:
                    new_processes[cgroup] = self.processes[cgroup]

            # Wait for processes termination.
            time.sleep(0.2)

            # Keep running processes.
            self.processes = new_processes

        # Remove cgroups.
        for task in self.tasks:
            if task.cgroup_path not in excepts:
                _delete_cgroup(task.cgroup_path)


def _parse_task_name(task):
    splitted = task.split('/')
    name = splitted[-1]

    return name, name, task


def _create_dumb_process(cgroup_path, command: str):
    splitted_command = command.split()

    p = subprocess.Popen(splitted_command)
    cpu_path, perf_path = _get_cgroup_full_path(cgroup_path)

    with open(os.path.join(cpu_path, 'tasks'), 'a') as f:
        f.write(str(p.pid))
    with open(os.path.join(perf_path, 'tasks'), 'a') as f:
        f.write(str(p.pid))

    return p


def _get_cgroup_full_path(cgroup):
    return os.path.join(CPU_PATH, cgroup[1:]), os.path.join(PERF_PATH, cgroup[1:])


def _create_cgroup(cgroup_path):
    cpu_path, perf_path = _get_cgroup_full_path(cgroup_path)
    try:
        os.makedirs(cpu_path)
    except FileExistsError:
        log.warning('cpu cgroup "{}" already exists'.format(cgroup_path))

    try:
        os.makedirs(perf_path)
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


class CheckFailed(Exception):
    """Used when check fails. """
    pass


class Check(abc.ABC):
    @abc.abstractmethod
    def check(self, metrics):
        pass


@dataclass
class FileCheck(Check):
    path: str
    line: str = None
    subvalue: str = None

    def check(self, metrics):

        if not os.path.isfile(self.path):
            raise CheckFailed('File {} does not exist!'.format(self.path))

        with open(self.path) as f:
            for line in f:
                if self.line:
                    if line.rstrip('\n\r') == self.line:
                        break
                    if self.subvalue in line:
                        break
            else:
                raise CheckFailed(str(self))


@dataclass
class MetricCheck(Check):
    name: str
    labels: Optional[Dict] = None
    value: Optional[Union[float, int]] = None

    def check(self, metrics):
        assert_metric(metrics, self.name, self.labels, self.value)
