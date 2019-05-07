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
from owca.config import load_config, Path
from owca.detectors import TasksMeasurements, TasksResources, TasksLabels, Anomaly
from owca.metrics import Metric
from owca.nodes import TaskId
from owca.platforms import Platform
from owca.logger import TRACE

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


def _build_allocations_from_rules(all_tasks_ids: Set[TaskId],
                                  tasks_labels: Dict[TaskId, Dict[str, str]], rules):
    tasks_allocations = {}

    # Iterate over rules and apply one by one.
    for rule_idx, rule in enumerate(rules):
        if 'allocations' not in rule:
            log.warning('StaticAllocator(%s): missing "allocations" - ignore!', rule_idx)
            continue

        log.debug('StaticAllocator(%s): processing %s rule.', rule_idx,
                  '(%s)' % rule['name'] if 'name' in rule else '')

        new_task_allocations = rule['allocations']
        if not new_task_allocations:
            log.log(TRACE, 'StaticAllocator(%s): allocations are empty - ignore!', rule_idx)
            continue

        if 'rdt' in new_task_allocations:
            new_task_allocations[AllocationType.RDT] = RDTAllocation(
                **new_task_allocations['rdt'])

        # Prepare match_task_ids filter:
        if 'task_id' in rule:
            # by task_id
            task_id = rule['task_id']
            match_task_ids = {task_id}
            log.log(TRACE, 'StaticAllocator(%s): match by task_id=%r', rule_idx, rule['task_id'])

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
                        log.log(TRACE, 'StaticAllocator(%s):  match task %r by label=%s',
                                rule_idx, task_id, label_name)
        else:
            # match everything
            log.log(TRACE, 'StaticAllocator(%s):  match all tasks', rule_idx)
            match_task_ids = all_tasks_ids

        # for matching tasks calculate and remember target_tasks_allocations
        log.log(TRACE, 'StaticAllocator(%s):  applying allocations for %i tasks', rule_idx,
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
    Simple allocator based on rules defining relation between task labels
    and allocation definition (set of concrete values).

    The allocator reads allocation rules from a yaml file and directly
    from constructor argument (passed as python dictionary).
    Refer to configs/extra/static_allocator_config.yaml to see sample
    input file for StaticAllocator.

    A rule is an object with three fields:
    - name,
    - labels (optional),
    - allocations.

    First field is just a helper to name a rule.
    Second field contains a dictionary, where each key is a task's label name and
    the value is a regex defining the matching set of label values. If the field
    is not included then all tasks match the rule.
    The third field is a dictionary of allocations which should be applied to
    matching tasks.

    If there are multiple matching rules then the rules' allocations are merged and applied.
    """

    # Direct way to pass rules.
    rules: List[dict] = None

    # Filepath of yaml config file with rules.
    config: Path = None

    def allocate(
            self,
            platform: Platform,
            tasks_measurements: TasksMeasurements,
            tasks_resources: TasksResources,
            tasks_labels: TasksLabels,
            tasks_allocations: TasksAllocations,
    ) -> (TasksAllocations, List[Anomaly], List[Metric]):

        rules = []
        if self.rules:
            rules.extend(self.rules)

        if self.config:
            if not os.path.exists(self.config):
                log.warning('StaticAllocator: cannot find config file %r - ignoring!', self.config)
            else:
                rules.extend(load_config(self.config))

        if len(rules) == 0:
            log.warning('StaticAllocator: no rules were provided!')
            return {}, [], []

        # Merge all tasks ids.
        all_tasks_ids = (set(tasks_labels.keys()) | set(tasks_resources.keys()) |
                         set(tasks_allocations.keys()))
        log.log(TRACE,
                'StaticAllocator: handling allocations for %i tasks. ', len(all_tasks_ids))
        for task_id, labels in tasks_labels.items():
            log.log(TRACE, '%s', ' '.join('%s=%s' % (k, v) for k, v in sorted(labels.items())))

        tasks_allocations = _build_allocations_from_rules(all_tasks_ids, tasks_labels, rules)

        log.debug('StaticAllocator: final tasks allocations: \n %s',
                  pprint.pformat(tasks_allocations))
        return tasks_allocations, [], []
