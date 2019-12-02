import logging
from typing import List, Dict

from dataclasses import dataclass

from wca.allocators import Allocator, TasksAllocations, AllocationType
from wca.detectors import Anomaly, TaskData, TasksData
from wca.logger import TRACE
from wca.metrics import Metric, MetricName
from wca.platforms import Platform, encode_listformat, decode_listformat

# from pprint import pprint

log = logging.getLogger(__name__)


@dataclass
class NUMAAllocator(Allocator):
    # minimal value of task_balance so the task is not skipped during rebalancing analysis
    # by default turn off, none of tasks are skipped due to this reason
    loop_min_task_balance: float = 0.0

    # syscall "migrate pages" per process memory migration
    migrate_pages: bool = True
    migrate_pages_min_task_balance: float = 0.95

    # Cgroups based memory migration and pinning
    cgroups_cpus_binding: bool = True
    # Cgroups based memory migration and pinning
    cgroups_memory_binding: bool = False
    # can be used only when cgroups_memory_binding is set to True
    cgroups_memory_migrate: bool = False

    # algos: use candidate
    double_match: bool = False
    candidate: bool = True

    # dry-run (for comparinson only)
    dryrun: bool = False

    def __post_init__(self):
        self._candidates_moves = 0
        self._match_moves = 0
        self._pages_to_move = {}

    def allocate(
            self,
            platform: Platform,
            tasks_data: TasksData
    ) -> (TasksAllocations, List[Anomaly], List[Metric]):
        log.debug('NUMAAllocator v7: dryrun=%s cgroups_memory_binding/migrate=%s/%s'
                  ' migrate_pages=%s double_match/candidate=%s/%s tasks=%s', self.dryrun,
                  self.cgroups_memory_binding, self.cgroups_memory_migrate,
                  self.migrate_pages, self.double_match, self.candidate, len(tasks_data))
        log.log(TRACE, 'Moves match=%s candidates=%s', self._match_moves, self._candidates_moves)
        log.log(TRACE, 'Tasks data %r', tasks_data)
        allocations = {}

        # Total host memory
        total_memory = _platform_total_memory(platform)

        # print("Total memory: %d\n" % total_memory)
        extra_metrics = []
        extra_metrics.extend([
            Metric('numa__task_candidate_moves', value=self._candidates_moves),
            Metric('numa__task_match_moves', value=self._match_moves),
            Metric('numa__task_tasks_count', value=len(tasks_data)),
        ])

        tasks_memory = []
        # Collect tasks sizes and NUMA node usages
        for task, data in tasks_data.items():
            tasks_memory.append(
                (task,
                 _get_task_memory_limit(data.measurements, total_memory,
                                        task, data.resources),
                 _get_numa_node_preferences(data.measurements, platform)))
        tasks_memory = sorted(tasks_memory, reverse=True, key=lambda x: x[1])

        # Current state of the system
        balanced_memory = {x: [] for x in range(platform.numa_nodes)}
        tasks_to_balance = []
        tasks_current_nodes = {}
        # 1. First, get current state of the system
        for task, memory, preferences in tasks_memory:
            current_node = _get_current_node(
                decode_listformat(tasks_data[task].allocations[AllocationType.CPUSET_CPUS]),
                platform.node_cpus)
            log.log(TRACE, "Task: %s Memory: %d Preferences: %s, Current node: %d" % (
                task, memory, preferences, current_node))
            tasks_current_nodes[task] = current_node

            if current_node >= 0:
                # log.debug("task already placed, recording state")
                balanced_memory[current_node].append((task, memory))

                task_balance = preferences[current_node]
                if self.migrate_pages and task_balance < self.migrate_pages_min_task_balance:
                    tasks_to_balance.append(task)

        balance_task = None
        balance_task_node = None
        balance_task_candidate = None
        balance_task_node_candidate = None

        log.log(TRACE, "Current state of the system: %s" % balanced_memory)
        log.log(TRACE, "Current state of the system per node: %s" % {
            node: sum(t[1] for t in tasks) / 2 ** 10 for node, tasks in balanced_memory.items()})
        log.debug("Current task assigments: %s" % {
            node: len(tasks) for node, tasks in balanced_memory.items()})

        for node, tasks_with_memory in balanced_memory.items():
            extra_metrics.extend([
                Metric('numa__balanced_memory_tasks', value=len(tasks_with_memory),
                       labels=dict(numa_node=str(node))),
                Metric('numa__balanced_memory_size', value=sum([m for t, m in tasks_with_memory]),
                       labels=dict(numa_node=str(node)))
            ])

        if self.dryrun:
            return allocations, [], extra_metrics

        # 3. Re-balancing analysis
        log.log(TRACE, 'Starting re-balancing analysis')

        for task, memory, preferences in tasks_memory:
            log.log(TRACE, "Task %r: Memory: %d Preferences: %s" % (task, memory, preferences))
            current_node = _get_current_node(
                decode_listformat(tasks_data[task].allocations[AllocationType.CPUSET_CPUS]),
                platform.node_cpus)
            most_used_node = _get_most_used_node(preferences)
            best_memory_node = _get_best_memory_node(memory, balanced_memory)
            most_free_memory_node = \
                _get_most_free_memory_node(memory,
                                           platform.measurements[
                                               MetricName.PLATFORM_MEM_NUMA_FREE_BYTES])

            data: TaskData = tasks_data[task]

            extra_metrics.extend([
                Metric('numa__task_current_node', value=current_node,
                       labels=data.labels),
                Metric('numa__task_most_used_node', value=most_used_node,
                       labels=data.labels),
                Metric('numa__task_best_memory_node', value=best_memory_node,
                       labels=data.labels),
                Metric('numa__task_best_memory_node_preference', value=preferences[most_used_node],
                       labels=data.labels),
                Metric('numa__task_most_free_memory_mode', value=most_free_memory_node,
                       labels=data.labels)
            ])

            self._pages_to_move.setdefault(task, 0)

            # log.debug("Task current node: %d", current_node)
            if current_node >= 0:
                log.debug("Task %r: already placed on the node %d, taking next",
                          task, current_node)
                # balanced_memory[current_node].append((task, memory))
                continue

            if memory == 0:
                # Handle missing data for "ghost" tasks
                # e.g. cgroup without processes when using StaticNode
                log.warning(
                    'skip allocation for %r task - not enough data - '
                    'maybe there are no processes there!',
                    task)
                continue

            log.log(TRACE, "Analysing task %r: Most used node: %d,"
                           " Best free node: %d, Best memory node: %d" %
                    (task, most_used_node, most_free_memory_node, best_memory_node))

            # if not yet task found for balancing
            if balance_task is None and balance_task_node is None:

                # Give a chance for AutoNUMA to re-balance memory
                if preferences[most_used_node] < self.loop_min_task_balance:
                    log.log(TRACE, "   THRESHOLD: not most of the memory balanced, continue")
                    continue

                if self.double_match and \
                        (most_used_node == best_memory_node
                         or most_used_node == most_free_memory_node):
                    log.log(TRACE, "   OK: found task for balancing: %s", task)
                    balance_task = task
                    balance_task_node = most_used_node
                    # break # commented to give a chance to generate other metrics

                elif self.candidate and balance_task_candidate is None \
                        and balance_task_node_candidate is None:
                    log.log(TRACE, '   CANDIT: not perfect match'
                                   ', but remember as candidate, continue')
                    balance_task_candidate = task
                    balance_task_node_candidate = best_memory_node
                    # balance_task_node_candidate = most_free_memory_node

                else:
                    log.log(TRACE, "   IGNORE: not perfect match"
                                   "and candidate set(disabled), continue")
                # break # commented to give a chance to generate other metrics

            # if most_used_node != most_free_memory_node:
            #     continue

            # pref_nodes = {}
            # for node in preferences:
            #     print(preferences[node])
            #     print(( memory / (sum([k[1] for k in balanced_memory[node]])+memory))/2)
            #     # pref_nodes[node] = max(preferences[node],
            #     #     ( memory / (sum([k[1] for k in balanced_memory[node]])+memory))/2)
            #     pref_nodes[node] = preferences[node]
            #     # pref_nodes[node] = ( memory/(sum([k[1] for k in balanced_memory[node]])+memory))
            # pprint(pref_nodes)
            # best_node = sorted(pref_nodes.items(), reverse=True, key=lambda x: x[1])[0][0]
            # # pprint(best_node)
            # balanced_memory[best_node].append((task, memory))

        # Do not send metrics of not existing tasks.
        old_tasks = [task for task in self._pages_to_move if task not in tasks_data]
        for old_task in old_tasks:
            if old_task in self._pages_to_move:
                del self._pages_to_move[old_task]

        # 3. Perform CPU pinning with optional memory bingind and forced migration.
        if balance_task is None and balance_task_node is None:
            if balance_task_candidate is not None and balance_task_node_candidate is not None:
                log.debug('Task %r: Using candidate rule', balance_task_candidate)
                balance_task = balance_task_candidate
                balance_task_node = balance_task_node_candidate
                self._candidates_moves += 1
        else:
            self._match_moves += 1

        if balance_task is not None and balance_task_node is not None:
            log.debug("Task %r: assiging to node %s." % (balance_task, balance_task_node))
            allocations[balance_task] = {}
            if self.cgroups_cpus_binding:
                allocations[balance_task][AllocationType.CPUSET_CPUS] = \
                    encode_listformat(platform.node_cpus[balance_task_node])

            if self.cgroups_memory_binding:
                allocations[balance_task][
                    AllocationType.CPUSET_MEMS] = encode_listformat({balance_task_node})

                # Instant memory migrate.
                if self.cgroups_memory_migrate:
                    log.debug("Assign task %s to node %s with memory migrate" %
                              (balance_task, balance_task_node))
                    allocations[balance_task][AllocationType.CPUSET_MEMORY_MIGRATE] = 1

            if self.migrate_pages:
                self._pages_to_move[balance_task] += get_pages_to_move(
                    balance_task, tasks_data, balance_task_node, 'assignment')
                allocations.setdefault(balance_task, {})
                allocations[balance_task][AllocationType.MIGRATE_PAGES] = balance_task_node

        # 5. Memory migragtion
        # If nessesary migrate pages to least used node, for task that are still not there.
        least_used_node = sorted(
            platform.measurements[MetricName.PLATFORM_MEM_NUMA_FREE_BYTES].items(), reverse=True,
            key=lambda x: x[1])[0][0]
        log.log(TRACE, 'Least used node: %s', least_used_node)
        log.log(TRACE, 'Tasks to balance: %s', tasks_to_balance)

        if self.migrate_pages:
            for task in tasks_to_balance:
                if tasks_current_nodes[task] == least_used_node:
                    current_node = tasks_current_nodes[task]
                    self._pages_to_move[task] += get_pages_to_move(
                        task, tasks_data, current_node, 'unbalanced')

                    allocations.setdefault(task, {})

                    allocations[task][AllocationType.MIGRATE_PAGES] = current_node
            else:
                log.log(TRACE, 'no more tasks to move memory!')

        for task, page_to_move in self._pages_to_move.items():
            data: TaskData = tasks_data[task]
            extra_metrics.append(
                Metric('numa__task_pages_to_move', value=page_to_move,
                       labels=data.labels)
            )
        total_pages_to_move = sum(p for p in self._pages_to_move.values())
        extra_metrics.append(
            Metric('numa__total_pages_to_move', value=total_pages_to_move)
        )
        log.log(TRACE, 'Pages to move: %r', self._pages_to_move)

        log.log(TRACE, 'Allocations: %r', allocations)
        return allocations, [], extra_metrics


def get_pages_to_move(task, tasks_data, target_node, reason):
    data: TaskData = tasks_data[task]
    pages_to_move = sum(
        v for node, v
        in data.measurements[MetricName.TASK_MEM_NUMA_PAGES].items()
        if node != target_node)
    log.debug('Task: %s Moving %s MB to node %s reason %s', task,
              (pages_to_move * 4096) / 1024 ** 2, target_node, reason)
    return pages_to_move


def _platform_total_memory(platform):
    return sum(platform.measurements[MetricName.PLATFORM_MEM_NUMA_FREE_BYTES].values()) + \
           sum(platform.measurements[MetricName.PLATFORM_MEM_NUMA_USED_BYTES].values())


def _get_task_memory_limit(task_measurements, total, task, task_resources):
    "Returns detected maximum memory for the task"
    if 'mem' in task_resources:
        mems = task_resources['mem']
        log.log(TRACE, 'Task: %s from resources %s %s %s', task, 'is',
                mems, 'bytes')
        return mems

    limits_order = [
        MetricName.TASK_MEM_LIMIT_BYTES,
        MetricName.TASK_MEM_SOFT_LIMIT_BYTES,
        MetricName.TASK_MEM_MAX_USAGE_BYTES,
        MetricName.TASK_MEM_USAGE_BYTES, ]
    for limit in limits_order:
        if limit not in task_measurements:
            continue
        if task_measurements[limit] > total:
            continue
        log.log(TRACE, 'Task: %s from cgroups limit %s %s %s %s', task, limit, 'is',
                task_measurements[limit], 'bytes')
        return task_measurements[limit]
    return 0


def _get_numa_node_preferences(task_measurements, platform: Platform) -> Dict[int, float]:
    ret = {node_id: 0 for node_id in range(0, platform.numa_nodes)}
    if MetricName.TASK_MEM_NUMA_PAGES in task_measurements:
        metrics_val_sum = sum(task_measurements[MetricName.TASK_MEM_NUMA_PAGES].values())
        for node_id, metric_val in task_measurements[MetricName.TASK_MEM_NUMA_PAGES].items():
            ret[int(node_id)] = round(metric_val / max(1, metrics_val_sum), 4)
    else:
        log.warning('{} metric not available'.format(MetricName.TASK_MEM_NUMA_PAGES))
    return ret


def _get_most_used_node(preferences):
    return sorted(preferences.items(), reverse=True, key=lambda x: x[1])[0][0]


def _get_current_node(cpus, nodes):
    for node in nodes:
        if nodes[node] == cpus:
            return node
    return -1


def _get_best_memory_node(memory, balanced_memory):
    """for equal task memory, choose node with less allocated memory by WCA"""
    if memory == 0:
        return balanced_memory[0]

    d = {}
    for node in balanced_memory:
        d[node] = round(memory / (sum([k[1] for k in balanced_memory[node]]) + memory), 4)
    best = sorted(d.items(), reverse=True, key=lambda x: x[1])
    # print('best:')
    # pprint(best)
    return best[0][0]


def _get_most_free_memory_node(memory, node_memory_free):
    d = {}
    for node in node_memory_free:
        d[node] = round(memory / node_memory_free[node], 4)
    # pprint(d)
    free_nodes = sorted(d.items(), key=lambda x: x[1])
    # print('free:')
    # pprint(free_nodes)
    return free_nodes[0][0]
