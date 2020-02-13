# Copyright (c) 2020 Intel Corporation
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

from dataclasses import dataclass, field
from typing import Dict, List, Tuple, Optional, Set
import logging
from collections import Counter

from wca.logger import TRACE
from wca.scheduler.algorithms import Algorithm
from wca.scheduler.types import ExtenderArgs, NodeName, AppName
from wca.scheduler.types import ResourceType as rt


log = logging.getLogger(__name__)

GB = 1000 ** 3
MB = 1000 ** 2

TaskId = str
NodeId = int
Assignments = Dict[TaskId, NodeId]


class Resources:
    def __init__(self, resources, membw_ratio=1):
        """membw_ratio: ratio of MEMBW_READ / MEMBW_WRITE."""
        self.data = resources

    def __repr__(self):
        return str({key: round(val, 2) for key, val in self.data.items()})

    @staticmethod
    def create_empty(dimensions):
        return Resources({d: 0 for d in dimensions})

    def copy(self):
        r = Resources({})
        r.data = self.data.copy()
        return r

    def __bool__(self):
        return all([val > 0 or abs(val) < 0.0001 for val in self.data.values()])

    def __sub__(self, other):
        me = self.copy()
        me.substract(other)
        return me

    def substract(self, b):
        """simply loops over all dimensions and use - operator"""
        assert set(self.data.keys()) == set(b.data.keys())
        for key in self.data.keys():
            self.data[key] -= b.data[key]

    def substract_aep_aware(self, b, membw_read_write_ratio):
        """Mutates self. """
        assert set(self.data.keys()) == set(b.data.keys())
        for key in self.data.keys():
            if key == rt.MEMBW_READ or key == rt.MEMBW_WRITE:
                continue
            self.data[key] -= b.data[key]

        # Special case for MEMBW
        if rt.MEMBW_READ in self.data and rt.MEMBW_WRITE in self.data:
            READ = rt.MEMBW_READ
            WRITE = rt.MEMBW_WRITE
            x = self.data
            y = b.data
            # mirror calculations for WRITE from READ; that are not two seperate dimensions;
            x[READ] = x[READ] - y[READ] - y[WRITE] * membw_read_write_ratio
            x[WRITE] = x[WRITE] - y[WRITE] - y[READ] / membw_read_write_ratio

    def __add__(self, other):
        me = self.copy()
        me.add(other)
        return me

    def add(self, b):
        """simply loops over all dimensions and use + operator"""
        assert set(self.data.keys()) == set(b.data.keys())
        for key in self.data.keys():
            self.data[key] += b.data[key]

    @staticmethod
    def sum(array):
        r = Resources.create_empty(list(array[0].data.keys()))
        for el in array:
            r = r + el
        return r

    def __truediv__(self, other):
        me = self.copy()
        me.divide(other)
        return me

    def divide(self, b):
        assert set(self.data.keys()) == set(b.data.keys())
        for key in self.data.keys():
            self.data[key] /= b.data[key]


class Task:
    def __init__(self, name, requested, assignment=None):
        self.name: str = name
        self.assignment: Node = assignment
        self.requested: Resources = requested
        self.real: Resources = Resources.create_empty(requested.data.keys())
        self.life_time: int = 0

    def remove_dimension(self, resource_type: rt):
        """Post-creation removal of one of the dimensions."""
        for resources_ in (self.requested, self.real):
            del resources_.data[resource_type]

    def add_dimension(self, resource_type: rt, requested_val):
        """Post-creation addition of a dimension."""
        self.requested.data[resource_type] = requested_val
        self.real.data[resource_type] = 0

    CORE_NAME_SEP = '___'

    def get_core_name(self):
        if self.CORE_NAME_SEP in self.name:
            return self.name[:self.name.find(self.CORE_NAME_SEP)]
        return self.name

    def update(self, delta_time):
        """Update state of task when it becomes older by delta_time."""
        self.life_time += delta_time
        # Here simply just if, life_time > 0 assign all requested.
        self.real = self.requested.copy()

    def __repr__(self):
        return "(name: {}, assignment: {}, requested: {}, real: {})".format(
            self.name, 'None' if self.assignment is None else self.assignment.name,
            str(self.requested), str(self.real))

    def copy(self):
        return Task(self.name, self.requested.copy(), None)


class Node:
    """
        initial - all available
        real - free real memory
        unassigned - free/unassigned memory
    """
    def __init__(self, name, available_resources):
        self.name = name
        self.initial = available_resources
        self.free = available_resources.copy()
        self.unassigned = available_resources.copy()

    def __repr__(self):
        return "Node(name: {}, initial: {}, free: {}, unassiged: {})".format(
            self.name, str(self.initial), str(self.free), str(self.unassigned))

    def get_membw_read_write_ratio(self):
        d_ = self.initial.data
        if rt.MEMBW_READ in d_ and rt.MEMBW_WRITE in d_:
            return d_[rt.MEMBW_READ] / d_[rt.MEMBW_WRITE]
        return 1

    # @staticmethod
    # def substract_resources(a: Resources, b: Resources):
    #     """returns c = a - b"""
    #     assert set(a.data.keys()) == set(b.data.keys())
    #     c = a.copy()
    #     for key in self.data.keys():
    #         if key == rt.MEMBW_READ or key == rt.MEMBW_WRITE:
    #             continue
    #         c.data[key] -= b.data[key]
    #     # Special case for MEMBW
    #     if rt.MEMBW_READ in c.data and rt.MEMBW_WRITE in c.data:
    #         READ = rt.MEMBW_READ
    #         WRITE = rt.MEMBW_WRITE
    #         x = c.data
    #         y = b.data
    #         x[READ] = x[READ] - y[READ] - y[WRITE] * membw_read_write_ratio
    #         x[WRITE] = x[WRITE] - y[WRITE] - y[READ] / membw_read_write_ratio
    #     return c

    def validate_assignment(self, tasks, new_task):
        """Check if there is enough resources on the node for a >>new_task<<."""
        tmp_unassigned: Resources = self.initial.copy()
        for task in tasks:
            if task.assignment == self:
                tmp_unassigned.substract_aep_aware(task.requested,
                                                   self.get_membw_read_write_ratio())
        tmp_unassigned.substract_aep_aware(new_task.requested, self.get_membw_read_write_ratio())
        return bool(tmp_unassigned)

    def update(self, tasks):
        """Update usages of resources (recalculate self.free and self.unassigned)"""
        self.free = self.initial.copy()
        self.unassigned = self.initial.copy()
        for task in tasks:
            if task.assignment == self:
                self.free.substract_aep_aware(task.real, self.get_membw_read_write_ratio())
                self.unassigned.substract_aep_aware(task.requested,
                                                    self.get_membw_read_write_ratio())


class AssignmentsCounts:
    def __init__(self, tasks: List[Task], nodes: List[Node]):
        per_node: Dict[NodeName, Counter]
        per_cluster: Counter
        unassigned: Counter

        # represents sum of all other siblings in the tree
        ALL = '__ALL__'

        """Returns tuple from structures 1) 2) 3)"""
        # 1) assignments per node per app
        per_node: Dict[NodeName, Counter[AppName]] = {}
        for node in nodes:
            per_node[node.name] = Counter(Counter({ALL: 0}))
            for task in tasks:
                if task.assignment == node:
                    app_name = task.get_core_name()
                    per_node[node.name].update([app_name])
                    per_node[node.name].update([ALL])
        assert sum([leaf for node_assig in per_node.values()
                    for _, leaf in node_assig.items()]) \
            == len([task for task in tasks if task.assignment is not None]) * 2

        # 2) assignemnts per app (for the whole cluster)
        per_cluster: Counter[AppName] = Counter({ALL: 0})
        # 3) unassigned apps
        unassigned: Counter[AppName] = Counter({ALL: 0})
        for task in tasks:
            app_name = task.get_core_name()
            if task.assignment is not None:
                per_cluster.update([app_name])
                per_cluster.update([ALL])
            else:
                unassigned.update([app_name])
                unassigned.update([ALL])
        assert sum(per_cluster.values()) + sum(unassigned.values()) == len(tasks) * 2

        self.per_node = per_node
        self.per_cluster = per_cluster
        self.unassigned = unassigned

    def to_str(self) -> List[str]:
        pass


@dataclass
class ClusterSimulator:
    tasks: List[Task]
    nodes: List[Node]
    scheduler: Optional[Algorithm]
    allow_rough_assignment: bool = True
    dimensions: Set[rt] = \
        field(default_factory=lambda: {rt.CPU, rt.MEM,
                                       rt.MEMBW_READ, rt.MEMBW_WRITE})

    def __post_init__(self):
        self.time = 0
        all([set(node.initial.data.keys()) == self.dimensions for node in self.nodes])
        all([set(task.requested.data.keys()) == self.dimensions for task in self.tasks])
        self.rough_assignments_per_node: Dict[Node, int] = {node: 0 for node in self.nodes}

    def get_task_by_name(self, task_name: str) -> Optional[Task]:
        filtered = [task for task in self.tasks if task.name == task_name]
        return filtered[0] if filtered else None

    def get_node_by_name(self, node_name: str) -> Optional[Node]:
        filtered = [node for node in self.nodes if node.name == node_name]
        return filtered[0] if filtered else None

    def per_node_resource_usage(self, if_percentage: bool = False):
        """if_percentage: if output in percentage or original resource units"""
        node_resource_usage = {node: Resources.create_empty(self.dimensions) for node in self.nodes}
        for task in self.tasks:
            if task.assignment is None:
                continue
            node_resource_usage[task.assignment] += task.requested

        if if_percentage:
            return {node: node_resource_usage[node]/node.initial
                    for node in node_resource_usage.keys()}
        return node_resource_usage

    # Counter represents Dict[AppName, int]
    def assignments_counts(self) -> AssignmentsCounts:
        return AssignmentsCounts(self.tasks, self.nodes)

    def cluster_resource_usage(self, if_percentage: bool = False):
        node_resource_usage = self.per_node_resource_usage()

        r = Resources.sum([usage for usage in node_resource_usage.values()])
        if if_percentage:
            r = r / Resources.sum([node.initial for node in self.nodes])
        return r

    def reset(self):
        self.tasks = []
        self.time = 0

    def update_tasks_usage(self, delta_time):
        """It may be simulated that task usage changes across its lifetime."""
        for task in self.tasks:
            task.update(delta_time)

    def update_tasks_list(self, changes):
        deleted, created = changes
        self.tasks = [task for task in self.tasks if task not in deleted]
        for new in created:
            new.assignment = None
            self.tasks.append(new)

    def update_nodes_state(self):
        for node in self.nodes:
            node.update(self.tasks)

    def validate_assignment(self, task: Task, assignment: Node) -> bool:
        return assignment.validate_assignment(self.tasks, task)

    def perform_assignments(self, assignments: Dict[TaskId, Node]) -> int:
        assigned_count = 0
        for task in self.tasks:
            if task.name in assignments:
                # taking all dimensions supported by Simulator whether the app fit the node.
                if_app_fit_to_node = self.validate_assignment(task, assignments[task.name])
                if if_app_fit_to_node or self.allow_rough_assignment:
                    task.assignment = assignments[task.name]
                    assigned_count += 1
                    if not if_app_fit_to_node:
                        self.rough_assignments_per_node[task.assignment] += 1
        return assigned_count

    def call_scheduler(self, new_task: Optional[Task]) -> Dict[str, Node]:
        """To map simulator structure into required by scheduler.Algorithm interace.
        Returns task_name -> node_name.
        """

        log.log(TRACE, "Before calling scheduler; new_task={}; nodes={}".format(new_task,
                                                                                self.nodes))

        if new_task is None:
            return {}

        assert self.dimensions.issubset(set(new_task.requested.data.keys())), \
            '{} {}'.format(set(new_task.requested.data.keys()),
                           self.dimensions)

        node_names = [node.name for node in self.nodes]
        pod = {'metadata': {'labels': {'app': new_task.get_core_name()},
               'name': new_task.name, 'namespace': 'default'}}
        extender_args = ExtenderArgs([], pod, node_names)

        extender_filter_result, extender_filter_metrics = self.scheduler.filter(extender_args)
        filtered_nodes = [node for node in extender_args.NodeNames
                          if node not in extender_filter_result.FailedNodes]
        log.log(TRACE, "Nodes left after filtering: ({})".format(','.join(filtered_nodes)))

        extender_args.NodeNames = filtered_nodes  # to prioritize pass only filtered nodes
        extender_prioritize_result, extender_prioritize_metrics = \
            self.scheduler.prioritize(extender_args)
        priorities_str = ','.join(["{}:{}".format(el.Host, str(el.Score))
                                   for el in extender_prioritize_result])
        log.log(TRACE, "Priorities of nodes: ({})".format(priorities_str))
        if extender_prioritize_result:
            best_node = max(extender_prioritize_result, key=lambda el: el.Score).Host
        else:
            best_node = None
        log.debug("Best node choosen in prioritize step: {}".format(best_node))

        if best_node is None:
            return {}
        return {new_task.name: self.get_node_by_name(best_node)}

    def iterate(self, delta_time: int, changes: Tuple[List[Task], List[Task]]) -> int:
        log.debug("--- Iteration starts ---")
        self.time += delta_time
        self.update_tasks_usage(delta_time)
        self.update_tasks_list(changes)

        # Update state after deleting tasks.
        self.update_nodes_state()

        assignments = self.call_scheduler(changes[1][0] if changes[1] else None)
        log.debug("Changes: {}".format(changes))
        log.debug("Assignments performed: {}".format(assignments))
        assigned_count = self.perform_assignments(assignments)

        # Recalculating state after assignments being performed.
        self.update_nodes_state()

        log.debug("Tasks assigned count: {}".format(
            len([task for task in self.tasks if task.assignment is not None])))

        log.debug("--- Iteration ends ---")

        return assigned_count

    def iterate_single_task(self, new_task: Optional[Task]):
        new_tasks = [] if new_task is None else [new_task]
        if new_task is not None:
            assert new_task.name not in set([task.name for task in self.tasks]), \
                'Tasks names must be unique, use sufixes'
            assert new_task not in self.tasks, \
                'Each Task must be seperate object (deep copy)'
        return self.iterate(delta_time=1, changes=([], new_tasks))
