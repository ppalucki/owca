import argparse
import logging
import os
import signal
import time
import yaml
import subprocess
from typing import List

from owca.config import register
from attr import dataclass

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


@register
@dataclass
class Tester(Node, Allocator, Storage):
    config: str

    def __post_init__(self):
        #self.config
        self.config_data = load_config(self.config)

        #
        self.metrics = []

    def get_tasks(self) -> List[Task]:

        # jesli to jest second run:



        # bazujesz na wartosci z yamla z danego testcase i pola tasks

        # towrzyorzy co potrzebne w systemie


        return [Task()]

    def allocate(self, platform: Platform, tasks_measurements: TasksMeasurements,
                 tasks_resources: TasksResources, tasks_labels: TasksLabels,
                 tasks_allocations: TasksAllocations) -> (
            TasksAllocations, List[Anomaly], List[Metric]):
        ...
        # tu kod ze static_allocatora parsujacy rule
        # z yamka z allocation_rules

    def store(self, metrics: List[Metric]) -> None:
        self.metrics.extend(metrics)


def _get_arguments():
    parser = argparse.ArgumentParser()

    parser.add_argument(
        '-c', '--config',
        help="Configuration file path for tester.",
        required=False,
        default='example/tester.yml'
    )

    args = parser.parse_args()

    return args.config


def _parse_config(path):
    with open(path, 'r') as f:
        return yaml.load(f)


def _create_dumb_process(task):
    command = ['sleep', 'inf']
    p = subprocess.Popen(command)
    cpu_path, perf_path = _get_cgroup_path(task)
    with open(cpu_path, 'a') as f:
        f.write(str(p.pid))
    with open(perf_path, 'a') as f:
        f.write(str(p.pid))

    return p.pid


def _kill_dumb_process(pid):
    os.kill(pid, signal.SIGKILL)


def _get_cgroup_path(task):
    return CPU_PATH.format(task), PERF_PATH.format(task)


def _create_cgroup(task):
    cpu_path, perf_path = _get_cgroup_path(task)
    try:
        os.makedirs(cpu_path.format(task))
    except FileExistsError:
        print('{} already in cpu cgroup'.format(task))

    try:
        os.makedirs(perf_path.format(task))
    except FileExistsError:
        print('{} already in perf_event cpgroup'.format(task))


def _delete_cgroup(task):
    cpu_path, perf_path = _get_cgroup_path(task)
    command = 'sudo find {0} -depth -type d -print -exec rmdir {{}} \\;'
    import IPython; IPython.embed()
    try:
        os.system(command.format(cpu_path))
    except FileNotFoundError:
        print('{} not found in cpu cgroup'.format(task))

    try:
        os.system(command.format(perf_path))
    except FileNotFoundError:
        print('{} not found in perf_event cgroup'.format(task))


def _handle_test_case(case, prev_tasks, tasks_file_path, allocations_file_path, check_sleep, test_sleep):
    pids = set()

    for task in case['tasks']:
        _create_cgroup(task)
        pid = _create_dumb_process(task)
        pids.add(pid)
        prev_tasks.add(task)
        time.sleep(int(test_sleep))
        _kill_dumb_process(pid)
        pids.remove(pid)
        _delete_cgroup(task)


def main():
    tester_config = _get_arguments()
    config = _parse_config(tester_config)

    tasks_file_path = config['tasks_filename']
    allocations_file_path = config['allocations_filename']
    check_sleep = config['check_sleep']
    test_sleep = config['test_sleep']

    prev_tasks = set()

    for case in config['tests']:
        _handle_test_case(config['tests'][case], prev_tasks, tasks_file_path, allocations_file_path,
                          check_sleep, test_sleep)


if __name__ == '__main__':
    main()
