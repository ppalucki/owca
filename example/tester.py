import argparse
import logging
import os
import signal
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


def _create_dumb_process():
    command = ['sleep', 'inf']
    p = subprocess.Popen(command)
    os.system('echo {0}')
    return p.pid


def _get_cgroup_path(task):
    cpu_path = '/sys/fs/cgroup/cpu/{}/tasks'.format(task)
    perf_path = '/sys/fs/cgroup/perf_event/{}/tasks/'.format(task)

    return cpu_path, perf_path


def _create_cgroup(task):
    cpu_path, perf_path = _get_cgroup_path(task)
    try:
        os.makedirs(cpu_path.format(task))
        os.makedirs(perf_path.format(task))
    except FileExistsError:
        print('{} already in cgroup'.format(task))


def _delete_cgroup(task):
    cpu_path, perf_path = _get_cgroup_path(task)
    command = 'sudo find {0} -depth -type d -print -exec rmdir {{}} \\;'

    os.system(command.format(cpu_path))
    os.system(command.format(perf_path))


def _handle_test_case(case, prev_tasks, tasks_file_path, allocations_file_path, check_sleep,
                      test_sleep):
    pids = []
    tasks = []

    if len(prev_tasks):
        pass
    else:
        for task in case['tasks']:
            _create_cgroup(task)
            _delete_cgroup(task)
            pid = _create_dumb_process(task)
            pids.append(pid)
            os.kill(pid, signal.SIGKILL)
            import IPython;
            IPython.embed()
            prev_tasks.add(task)
            tasks.append(
                {'name': '{}_name'.format(task),
                 'task_id': task,
                 'cgroup_path': '/{}'.format(task)
                 })
        with open(tasks_file_path, 'w') as f:
            f.write(yaml.dump(tasks))
        time.sleep(test_sleep)
        time.sleep(check_sleep)


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
