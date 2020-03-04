import itertools
import random
from collections import defaultdict
from typing import List, Dict

from wca.scheduler.cluster_simulator import Task
from wca.scheduler.types import ResourceType as rt


def extend_membw_dimensions_to_write_read(taskset):
    """replace dimensions rt.MEMBW with rt.MEMBW_WRITE and rt.MEMBW_READ"""
    new_taskset = []
    for task in taskset:
        task_ = task.copy()
        membw = task_.requested.data[rt.MEMBW]
        task_.remove_dimension(rt.MEMBW)
        task_.add_dimension(rt.MEMBW_READ, membw)
        task_.add_dimension(rt.MEMBW_WRITE, 0)
        new_taskset.append(task_)
    return new_taskset


def randomly_choose_from_taskset(taskset, size, seed):
    random.seed(seed)
    r = []
    for i in range(size):
        random_idx = random.randint(0, len(taskset) - 1)
        task = taskset[random_idx].copy()
        task.name += Task.CORE_NAME_SEP + str(i)
        r.append(task)
    return r


def randomly_choose_from_taskset_single(taskset, dimensions, name_suffix):
    random_idx = random.randint(0, len(taskset) - 1)
    task = taskset[random_idx].copy()
    task.name += Task.CORE_NAME_SEP + str(name_suffix)

    task_dim = set(task.requested.data.keys())
    dim_to_remove = task_dim.difference(dimensions)
    for dim in dim_to_remove:
        task.remove_dimension(dim)

    return task


class TaskGeneratorRandom:
    """Takes randomly from given task_definitions"""
    def __init__(self, task_definitions, max_items, seed):
        self.max_items = max_items
        self.task_definitions = task_definitions
        random.seed(seed)

    def __call__(self, index: int):
        if index >= self.max_items:
            return None
        return self.rand_from_taskset(str(index))

    def rand_from_taskset(self, name_suffix: str):
        return randomly_choose_from_taskset_single(
                extend_membw_dimensions_to_write_read(self.task_definitions),
                {rt.CPU, rt.MEM, rt.MEMBW_READ, rt.MEMBW_WRITE}, name_suffix)


class TaskGeneratorClasses:
    """Multiple each possible kind of tasks by replicas"""
    def __init__(self, task_definitions: List[Task], counts: Dict[str, int]):
        self.counts = counts
        self.tasks = []
        self.task_definitions = task_definitions

        classes = defaultdict(list)  # task_name: List[Tasks]
        for task_def_name, replicas in counts.items():
            for task_def in task_definitions:
                if task_def.name == task_def_name:
                    for r in range(replicas):
                        task_copy = task_def.copy()
                        task_copy.name += Task.CORE_NAME_SEP + str(r)
                        classes[task_def_name].append(task_copy)

        # merge with zip
        for tasks in itertools.zip_longest(*classes.values()):
            self.tasks.extend(filter(None, tasks))

    def __call__(self, index: int):
        if self.tasks:
            return self.tasks.pop()
        return None

    def __str__(self):
        total_tasks = sum(self.counts.values())
        kinds = ','.join([
            '%s=%s' % (task_def_name, count)
            for task_def_name, count in self.counts.items()])
        return '%d(%s)' % (total_tasks, kinds)


class TaskGeneratorEqual:
    """Multiple each possible kind of tasks by replicas"""
    def __init__(self, task_definitions: List[Task], replicas, alias=None):
        self.replicas = replicas
        self.tasks = []
        self.task_definitions = task_definitions
        self.alias = alias

        for task_def in task_definitions:
            if rt.WSS in task_def.requested.data:
                task_def.remove_dimension(rt.WSS)

        for r in range(replicas):
            for task_def in task_definitions:
                task_copy = task_def.copy()
                task_copy.name += Task.CORE_NAME_SEP + str(r)
                self.tasks.append(task_copy)

    def __call__(self, index: int):
        if self.tasks:
            return self.tasks.pop()
        return None

    def __str__(self):
        if self.alias is not None:
            return self.alias
        total_tasks = len(self.task_definitions) * self.replicas
        kinds = ','.join(['%s=%s' % (task_def.name, self.replicas)
                          for task_def in sorted(self.task_definitions, key=lambda t:t.name)])
        return '%d(%s)' % (total_tasks, kinds)
