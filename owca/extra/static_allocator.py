# Copyright (c) 2019 Intel Corporation
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
import logging
import os
import pprint
import re
from typing import List, Set, Dict

from dataclasses import dataclass

from owca.allocators import Allocator, TasksAllocations, AllocationType, RDTAllocation
from owca.config import load_config
from owca.detectors import TasksMeasurements, TasksResources, TasksLabels, Anomaly
from owca.metrics import Metric
from owca.nodes import TaskId
from owca.platforms import Platform

log = logging.getLogger(__name__)


def merge_rules(existing_tasks_allocations: TasksAllocations,
                new_tasks_allocations: TasksAllocations):
    merged_tasks_allocations = {}
    for task_id, task_allocations in new_tasks_allocations.items():
        merged_tasks_allocations[task_id] = dict(existing_tasks_allocations.get(task_id, {}),
                                                 **task_allocations)
    for task_id, task_allocations in existing_tasks_allocations.items():
        if task_id not in merged_tasks_allocations:
            merged_tasks_allocations[task_id] = dict(task_allocations)
    return merged_tasks_allocations


def _allocate_according_rules(all_tasks_ids: Set[TaskId],
                              tasks_labels: Dict[TaskId, Dict[str, str]], rules):
    tasks_allocations = {}

    # Iterate over rules and apply one by one.
    for rule_idx, rule in enumerate(rules):
        if 'allocations' not in rule:
            log.warning('StaticAllocator(%s): missing "allocations" - ignore!', rule_idx)
            continue

        log.info('StaticAllocator(%s): processing %s rule.', rule_idx,
                 '(%s)' % rule['name'] if 'name' in rule else '')

        new_task_allocations = rule['allocations']
        if not new_task_allocations:
            log.debug('StaticAllocator(%s): allocations are empty - ignore!', rule_idx)
            continue

        if 'rdt' in new_task_allocations:
            new_task_allocations[AllocationType.RDT] = RDTAllocation(
                **new_task_allocations['rdt'])

        # Prepare match_task_ids filter:
        if 'task_id' in rule:
            # by task_id
            task_id = rule['task_id']
            match_task_ids = {task_id}
            log.debug('StaticAllocator(%s): match by task_id=%r', rule_idx, rule['task_id'])

        # Find all tasks that matches.
        elif 'labels' in rule:
            labels = rule['labels']
            # by labels
            match_task_ids = set()
            for task_id, task_labels in tasks_labels.items():
                matching_label_names = set(task_labels) & set(labels)
                for label_name in matching_label_names:
                    if re.match(str(labels[label_name]), task_labels[label_name]):
                        match_task_ids.add(task_id)
                        log.debug('StaticAllocator(%s):  match task %r by label=%s',
                                  rule_idx, task_id, label_name)
        else:
            # match everything
            log.debug('StaticAllocator(%s):  match all tasks', rule_idx)
            match_task_ids = all_tasks_ids

        # for matching tasks calculate and remember target_tasks_allocations
        log.info('StaticAllocator(%s):  applying allocations for %i tasks', rule_idx,
                 len(match_task_ids))

        rule_tasks_allocations = {}

        # Set rules for every matching task.
        for match_task_id in match_task_ids:
            rule_tasks_allocations[match_task_id] = new_task_allocations

        # Merge rules with previous rules.
        tasks_allocations = merge_rules(tasks_allocations, rule_tasks_allocations)
    return tasks_allocations


@dataclass
class StaticAllocator(Allocator):
    """
    Allocator that uses config file to decide how to configure resources for tasks.
    It tries to match task according labels and the apply given allocations.

    Config file contains so-called rules, an objects with two fields:
    - labels
    - allocations

    if there is not labels or any label match to task labels, then allocations are executed.
    If there is multiple matching rules all allocations are merged.
    """

    # File location of yaml config file with rules.
    config: str

    def allocate(
            self,
            platform: Platform,
            tasks_measurements: TasksMeasurements,
            tasks_resources: TasksResources,
            tasks_labels: TasksLabels,
            tasks_allocations: TasksAllocations,
    ) -> (TasksAllocations, List[Anomaly], List[Metric]):
        if not os.path.exists(self.config):
            log.warning('StaticAllocator: cannot find config file %r - ignoring!', self.config)
            return {}, [], []
        else:
            # Merge all tasks ids.
            all_tasks_ids = (set(tasks_labels.keys())
                             | set(tasks_resources.keys()) | set(tasks_allocations.keys()))
            log.info('StaticAllocator: handling allocations for %i tasks. ', len(all_tasks_ids))
            for task_id, labels in tasks_labels.items():
                log.debug('%s', ' '.join('%s=%s' % (k, v) for k, v in sorted(labels.items())))

            # Load configuration.
            rules = load_config(self.config)

            # Parse configuration.
            if type(rules) != list:
                log.warning('StaticAllocator: improper format of config (expected list of rules)')
                return {}, [], []

            tasks_allocations = _allocate_according_rules(all_tasks_ids, tasks_labels, rules)

            log.info('StaticAllocator: final tasks allocations: \n %s',
                     pprint.pformat(tasks_allocations))
            return tasks_allocations, [], []
