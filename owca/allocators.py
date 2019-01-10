# Copyright (c) 2018 Intel Corporation
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
from abc import ABC, abstractmethod
from enum import Enum
from typing import List, Dict, Union, Tuple, Optional
import logging

from owca.metrics import Metric, MetricType
from owca.mesos import TaskId
from owca.platforms import Platform
from owca.detectors import TasksMeasurements, TasksResources, TasksLabels, Anomaly

from dataclasses import dataclass

log = logging.getLogger(__name__)


class AllocationType(str, Enum):

    QUOTA = 'cpu_quota'
    SHARES = 'cpu_shares'
    RDT = 'rdt'


@dataclass
class RDTAllocation:
    # defaults to TaskId from TasksAllocations
    name: str = None
    # CAT: optional - when no provided doesn't change the existing allocation
    l3: str = None
    # MBM: optional - when no provided doesn't change the existing allocation
    mb: str = None

    def generate_metrics(self) -> List[Metric]:
        """Encode RDT Allocation as metrics.
        Number of cache ways will be encoded as int,
        mb is treated as percentage.
        """
        # Empty object generate no metric.
        if not self.l3 and not self.mb:
            return []

        group_name = self.name or ''

        metrics = []
        if self.l3:
            domains = _parse_schemata_file_domains(self.l3)
            for domain_id, raw_value in domains.items():
                value = _count_enabled_bits(raw_value)
                metrics.append(
                    Metric(
                        name='allocation', value=value, type=MetricType.GAUGE,
                        labels=dict(allocation_type='rdt_l3',
                                    group_name=group_name, domain_id=domain_id)
                    )
                )

        if self.mb:
            domains = _parse_schemata_file_domains(self.mb)
            for domain_id, raw_value in domains.items():
                # NOTE: raw_value is treated as int, ignoring unit used (MB or %)
                value = int(raw_value)
                metrics.append(
                    Metric(
                       name='allocation', value=value, type=MetricType.GAUGE,
                       labels=dict(allocation_type='rdt_mb',
                                   group_name=group_name, domain_id=domain_id)
                    )
                )

        return metrics


TaskAllocations = Dict[AllocationType, Union[float, RDTAllocation]]
TasksAllocations = Dict[TaskId, TaskAllocations]


@dataclass
class AllocationConfiguration:

    # Default value for cpu.cpu_period [ms] (used as denominator).
    cpu_quota_period: int = 1000

    # Number of minimum shares, when ``cpu_shares`` allocation is set to 0.0.
    cpu_shares_min: int = 2
    # Number of shares to set, when ``cpu_shares`` allocation is set to 1.0.
    cpu_shares_max: int = 10000

    # Default Allocation for default root group
    default_rdt_allocation: RDTAllocation = None


class Allocator(ABC):

    @abstractmethod
    def allocate(
            self,
            platform: Platform,
            tasks_measurements: TasksMeasurements,
            tasks_resources: TasksResources,
            tasks_labels: TasksLabels,
            tasks_allocations: TasksAllocations,
    ) -> (TasksAllocations, List[Anomaly], List[Metric]):
        ...


class NOPAllocator(Allocator):

    def allocate(self, platform, tasks_measurements, tasks_resources,
                 tasks_labels, tasks_allocations):
        return [], [], []


# -----------------------------------------------------------------------
# private logic to handle allocations
# -----------------------------------------------------------------------

def convert_tasks_allocations_to_metrics(tasks_allocations: TasksAllocations) -> List[Metric]:
    """Takes allocations on input and convert them to something that can be
    stored persistently as metrics adding help/type fields and labels.

    Simple allocations become simple metric like this:
    - Metric(name='allocation', type='cpu_shares', value=0.2, labels=(task_id='some_task_id'))
    Encoding RDTAllocation object is delegated to RDTAllocation class.
    """
    metrics = []
    for task_id, task_allocations in tasks_allocations.items():
        task_allocations: TaskAllocations
        for allocation_type, allocation_value in task_allocations.items():
            if allocation_type == AllocationType.RDT:
                # Nested encoding of RDT allocations.
                rdt_allocation_metrics = allocation_value.generate_metrics()
                for rdt_allocation_metric in rdt_allocation_metrics:
                    rdt_allocation_metric.labels.update(task_id=task_id)
                metrics.extend(rdt_allocation_metrics)
            else:
                # Simple encoding
                metrics.append(
                    Metric(name='allocation', value=allocation_value, type=MetricType.GAUGE,
                           labels=dict(allocation_type=allocation_type, task_id=task_id)
                           )
                )

    return metrics


def _merge_rdt_allocation(old_rdt_allocation: Optional[RDTAllocation],
                          new_rdt_allocation: RDTAllocation)\
        -> Tuple[RDTAllocation, RDTAllocation]:
    """Merge two RDTAllocation objects (old and new) and return sum of the alloctions
    (all_rdt_allaction) and allocations that need to be applied now (resulting_rdt_alloaction)."""
    # new name, then new allocation will be used (overwrite) but no merge
    if old_rdt_allocation is None or old_rdt_allocation.name != new_rdt_allocation.name:
        return new_rdt_allocation, new_rdt_allocation
    else:
        all_rdt_allocation = RDTAllocation(
            name=old_rdt_allocation.name,
            l3=new_rdt_allocation.l3 or old_rdt_allocation.l3,
            mb=new_rdt_allocation.mb or old_rdt_allocation.mb,
        )
        resulting_rdt_allocation = RDTAllocation(
            name=new_rdt_allocation.name,
        )
        if old_rdt_allocation.l3 != new_rdt_allocation.l3:
            resulting_rdt_allocation.l3 = new_rdt_allocation.l3
        if old_rdt_allocation.mb != new_rdt_allocation.mb:
            resulting_rdt_allocation.mb = new_rdt_allocation.mb
        return all_rdt_allocation, resulting_rdt_allocation


def _calculate_task_allocations(
        old_task_allocations: TaskAllocations,
        new_task_allocations: TaskAllocations)\
        -> Tuple[TaskAllocations, TaskAllocations]:
    """Return allocations difference on single task level.
    all - are the sum of existing and new
    resulting - are just new allocaitons
    """
    all_task_allocations: TaskAllocations = dict(old_task_allocations)
    resulting_task_allocations: TaskAllocations = {}

    for allocation_type, value in new_task_allocations.items():
        # treat rdt diffrently
        if allocation_type == AllocationType.RDT:
            old_rdt_allocation = old_task_allocations.get(AllocationType.RDT)
            all_rdt_allocation, resulting_rdt_allocation = \
                _merge_rdt_allocation(old_rdt_allocation, value)
            all_task_allocations[AllocationType.RDT] = all_rdt_allocation
            resulting_task_allocations[AllocationType.RDT] = resulting_rdt_allocation
        else:
            if allocation_type not in all_task_allocations or \
                    all_task_allocations[allocation_type] != value:
                all_task_allocations[allocation_type] = value
                resulting_task_allocations[allocation_type] = value

    return all_task_allocations, resulting_task_allocations


def _calculate_tasks_allocations(
        old_tasks_allocations: TasksAllocations, new_tasks_allocations: TasksAllocations) \
        -> Tuple[TasksAllocations, TasksAllocations]:
    """Return all_allocations that are the effect on applied new_allocations on
    old_allocations, additionally returning allocations that need to be applied just now.
    """
    all_tasks_allocations: TasksAllocations = {}
    resulting_tasks_allocations: TasksAllocations = {}

    # check and merge & overwrite with old allocations
    for task_id, old_task_allocations in old_tasks_allocations.items():
        if task_id in new_tasks_allocations:
            new_task_allocations = new_tasks_allocations[task_id]
            all_task_allocations, resulting_task_allocations = _calculate_task_allocations(
                old_task_allocations, new_task_allocations)
            all_tasks_allocations[task_id] = all_task_allocations
            resulting_tasks_allocations[task_id] = resulting_task_allocations
        else:
            all_tasks_allocations[task_id] = old_task_allocations

    # if there are any new_allocations on task level that yet not exists in old_allocations
    # then just add them to both list
    only_new_tasks_ids = set(new_tasks_allocations) - set(old_tasks_allocations)
    for only_new_task_id in only_new_tasks_ids:
        task_allocations = new_tasks_allocations[only_new_task_id]
        all_tasks_allocations[only_new_task_id] = task_allocations
        resulting_tasks_allocations[only_new_task_id] = task_allocations

    return all_tasks_allocations, resulting_tasks_allocations


def _parse_schemata_file_domains(line: str) -> Dict[str, str]:
    """Parse RDTAllocation.l3 and RDTAllocation.mb strings based on
    https://elixir.bootlin.com/linux/latest/source/arch/x86/kernel/cpu/intel_rdt_ctrlmondata.c#lL206
    and return dict mapping and domain id to its configuration (value).
    Resource type (e.g. mb, l3) is dropped.

    Eg.
    mb:1=20;2=50 returns {'1':'20', '2':'50'}
    mb:xxx=20mbs;2=50b returns {'1':'20mbs', '2':'50b'}
    raises ValueError exception for inproper format or conflicting domains ids.
    """
    RESOURCE_ID_SEPARATOR = ':'
    DOMAIN_ID_SEPARATOR = ';'
    VALUE_SEPARATOR = '='

    domains = {}

    # Ignore emtpy line.
    if not line:
        return {}

    # Drop resource identifier prefix like ("mb:")
    line = line[line.find(RESOURCE_ID_SEPARATOR)+1:]
    # Domains
    domains_with_values = line.split(DOMAIN_ID_SEPARATOR)
    for domain_with_value in domains_with_values:
        if not domain_with_value:
            raise ValueError('domain cannot be empty')
        if VALUE_SEPARATOR not in domain_with_value:
            raise ValueError('Value separator is missing "="!')
        separator_position = domain_with_value.find(VALUE_SEPARATOR)
        domain_id = domain_with_value[:separator_position]
        if not domain_id:
            raise ValueError('domaind_id cannot be empty!')
        value = domain_with_value[separator_position+1:]
        if not value:
            raise ValueError('value cannot be empty!')

        if domain_id in domains:
            raise ValueError('Conflicting domain id found!')

        domains[domain_id] = value

    return domains


def _count_enabled_bits(hexstr: str) -> int:
    """Parse a raw value like f202 to number of bits enabled."""
    if hexstr == '':
        return 0
    value_int = int(hexstr, 16)
    enabled_bits_count = bin(value_int).count('1')
    return enabled_bits_count
