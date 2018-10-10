import logging
from typing import List

from owca.allocators import Allocator, TasksAllocations, log, AllocationType, RDTAllocation
from owca.detectors import TasksMeasurements, TasksResources, TasksLabels, Anomaly
from owca.metrics import Metric
from owca.platforms import Platform

log = logging.getLogger(__name__)

class TestingAllocator(Allocator):
    def __init__(self):
        self.testing_allocator_mode_index = 0
        self.testing_allocator_modes = ['empty',
                                        'one_group',
                                        'seperate_group',
                                        'all_in_root_group',
                                        'empty']

    def allocate(
            self,
            platform: Platform,
            tasks_measurements: TasksMeasurements,
            tasks_resources: TasksResources,
            tasks_labels: TasksLabels,
            tasks_allocations: TasksAllocations,
    ) -> (TasksAllocations, List[Anomaly], List[Metric]):
        testing_allocator_mode = self.testing_allocator_modes[self.testing_allocator_mode_index]
        log.debug('TestingAllocator mode is {}'.format(testing_allocator_mode))
        self.testing_allocator_mode_index = (self.testing_allocator_mode_index + 1)
        if self.testing_allocator_mode_index == 5:
            exit(1)

        new_tasks_allocations = {}
        if testing_allocator_mode == 'empty':
            return [], [], []
        elif testing_allocator_mode == 'one_group':
            for task_id in tasks_resources:
                new_tasks_allocations[task_id] = {
                    AllocationType.QUOTA: 1000,
                    AllocationType.RDT: RDTAllocation(name='only_group', l3='L3:0=00fff;1=0ffff')
                }
        elif testing_allocator_mode == 'seperate_group':
            for task_id in tasks_resources:
                new_tasks_allocations[task_id] = {
                    AllocationType.QUOTA: 2000,
                    AllocationType.RDT: RDTAllocation()
                }
        elif testing_allocator_mode == 'all_in_root_group':
            for task_id in tasks_resources:
                new_tasks_allocations[task_id] = {
                    AllocationType.QUOTA: 2000,
                    AllocationType.RDT: RDTAllocation(name='')
                }

        return (new_tasks_allocations, [], [])