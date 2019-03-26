import argparse
import yaml
import os
import subprocess
import signal
import time


CPU_PATH = '/sys/fs/cgroup/cpu/{}/tasks'
PERF_PATH = '/sys/fs/cgroup/perf_event/{}/tasks'


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
        _handle_test_case(config['tests'][case], prev_tasks, tasks_file_path, allocations_file_path, check_sleep, test_sleep)


if __name__ == '__main__':
    main()
