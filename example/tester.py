import argparse
import yaml
import os


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


def _get_cgroup_path(task):
    cpu_path = '/sys/fs/cgroup/cpu/{}/tasks'.format(task)
    perf_path = '/sys/fs/cgroup/perf_event/{}/tasks/'.format(task)

    return cpu_path, perf_path


def _create_cgroup(task):
    cpu_path, perf_path = _get_cgroup_path(task)

    os.makedirs(cpu_path.format(task))
    os.makedirs(perf_path.format(task))


def _delete_cgroup(task):
    cpu_path, perf_path = _get_cgroup_path(task)
    command = 'find {0} -depth -type d -print -exec rmdir {{}} \\;'

    os.system(command.format(cpu_path))
    os.system(command.format(perf_path))


def _handle_test_case(case, prev_tasks, tasks_file_path, allocations_file_path):
    pids = []
    tasks = []

    if len(prev_tasks):
        pass
    else:
        for task in case['tasks']:
            _create_cgroup(task)
            _delete_cgroup(task)
            prev_tasks.add(task)
            tasks.append(
                    {'name': '{}_name'.format(task),
                        'task_id': task,
                        'cgroup_path': '/{}'.format(task)
                        })
        with open(tasks_file_path, 'w') as f:
            f.write(yaml.dump(tasks))


def main():
    tester_config = _get_arguments()
    config = _parse_config(tester_config)

    tasks_file_path = config['tasks_filename']
    allocations_file_path = config['allocations_filename']
    check_sleep = config['check_sleep']
    test_sleep = config['test_sleep']

    prev_tasks = set()

    for case in config['tests']:
        _handle_test_case(config['tests'][case], prev_tasks, tasks_file_path, allocations_file_path)


if __name__ == '__main__':
    main()
