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

import time
import logging
import os

from wca.metrics import Measurements, MetricName

log = logging.getLogger(__name__)

MB = 1000000


class WSS:
    def __init__(self, cycle_duration_s, get_pids, dummy_reset_interval=-1,
                 stable_cycles_goal=30, threshold_divider=100):
        """
        Two metrics are created:
        - TASK_WSS_REFERENCED_BYTES: just raw information read from /proc/{}/smaps,
            reset can be controlled by dummy_reset_interval and stable_cycles_goal
        - TASK_WORKING_SET_SIZE_BYTES: heuristic to calculate working set size,
            depends on threshould_divider and stable_cycles_counter

        @Args:
        cycle_duration_s     -> duration of single cycle in seconds
        dummy_reset_interval -> despite everything just reset referenced
            each >>dummy_reset_interval<< cycle, set to >>-1<< to disable, by default turned off.
        stable_cycles_goal   -> how many stable measurements of >>referenced<< must happen
            before setting TASK_WORKING_SET_SIZE_BYTES
        """

        self.get_pids = get_pids

        self.cycle = 0
        self.started = time.time()
        self.cycle_duration_s = cycle_duration_s
        self.threshold_divider = threshold_divider

        self.dummy_reset_interval = dummy_reset_interval if dummy_reset_interval != -1 else None
        self.stable_cycles_goal = stable_cycles_goal
        self.stable_cycles_counter = 0

        self.prev_referenced = None  # [B]
        self.prev_membw = None  # [B/s]

        self.membw_counter_prev = None  # [B]

        # Keep last value of metric TASK_WORKING_SET_SIZE_BYTES
        self.last_stable__task_working_set_size_bytes = None  # [B]

    def _discover_pids(self):
        pids = set(self.get_pids(include_threads=False))
        all_pids = os.listdir('/proc')
        all_pids = set(map(str, filter(lambda x: x.isdecimal(), all_pids)))
        pids = pids & all_pids
        return pids

    def _update_stable_counter(self, curr_membw, curr_referenced):
        """Updates stable counter, which tells how many stable cycles in a row there were.
        stable: not changing rapidly in relation to previous values

        curr_membw: [B/s], curr_referenced: [B]
        """

        log.debug(
            '[%3.0fs] curr_referenced[MB]=%d '
            'stable_cycles_counter=%d',
            time.time() - self.started, curr_referenced/MB, self.stable_cycles_counter)

        if self.prev_referenced is not None and self.prev_membw is not None:
            curr_referenced_delta = \
                float(curr_referenced - self.prev_referenced) / self.cycle_duration_s
            curr_membw_delta = float(curr_membw - self.prev_membw) / self.cycle_duration_s

            membw_threshold = curr_membw_delta / self.threshold_divider
            referenced_threshold = curr_referenced / self.threshold_divider

            log.debug(
                '[%3.0fs] '
                'REFERENCED[MB]: curr=%d/delta=%d/threshold=%d | '
                'MEMBW[MB/s]: curr=%d/delta=%d/threshold=%d '
                '-> stable_cycles_counter=%d',
                time.time() - self.started,
                curr_referenced/MB, curr_referenced_delta/MB, referenced_threshold/MB,
                curr_membw/MB, curr_membw_delta/MB, membw_threshold/MB,
                self.stable_cycles_counter)

            max_decrease_divider = 50  # Sometimes referenced for some unknown reason goes down.
            if curr_referenced_delta >= 0 or \
                    abs(curr_referenced_delta) < curr_referenced / max_decrease_divider:
                if curr_referenced_delta < membw_threshold \
                        or curr_referenced_delta < referenced_threshold:
                    self.stable_cycles_counter += 1
                    log.debug('Incrementing stable_cycles_counter+=1')
                else:
                    self.stable_cycles_counter = 0
                    log.debug('one of thresholds (membw, wss) was exceeded;'
                              'resettings stable_cycles_counter')
            else:
                self.stable_cycles_counter = 0
                log.debug('curr_referenced_delta smaller than 0 and '
                          'abs(curr_re...) < curr_referenced/max_decrease_divider; '
                          'resetting stable_cycles_counter')
                log.debug('curr_referenced=%d, prev_referenced=%d, curr_membw_delta=%d',
                          curr_referenced, self.prev_referenced, curr_referenced_delta)
        else:
            log.debug('previous value of membw or referenced not available -'
                      ' resetting stable_cycles_counter')

        self.prev_membw = curr_membw
        self.prev_referenced = curr_referenced

    @staticmethod
    def _get_referenced(pids):
        """Returns referenced pages in [Bytes]"""
        if pids:
            dbg = {}
            for pid in pids:
                referenced = 0
                try:
                    with open('/proc/{}/smaps'.format(pid)) as f:
                        for line in f.readlines():
                            if 'Referenced' in line:
                                referenced += int(line.split('Referenced:')[1].split()[0])
                except (ProcessLookupError, FileNotFoundError):
                    print('WARN: process lookup error:', pid)
                    pass
                dbg[pid] = referenced

            return int(sum(dbg.values()) * 1000)  # Scale to Bytes (read as KB)
        return 0

    @staticmethod
    def _clear_refs(pids):
        for pid in pids:
            try:
                with open('/proc/{}/clear_refs'.format(pid), 'w') as f:
                    f.write('1\n')
            except FileNotFoundError:
                log.warning('pid does not exist for clearing refs - ignoring!')
                pass

    def get_measurements(self, rdt_measurements) -> Measurements:
        measurements = {}
        self.cycle += 1
        pids = self._discover_pids()
        log.debug('calculating wss for pids %s cycle=%d stable_cycles_counter=%d',
                  pids, self.cycle, self.stable_cycles_counter)
        referenced = self._get_referenced(pids)
        measurements[MetricName.TASK_WSS_REFERENCED_BYTES] = referenced

        if rdt_measurements and MetricName.TASK_MEM_BANDWIDTH_BYTES in rdt_measurements:
            membw_counter = rdt_measurements[MetricName.TASK_MEM_BANDWIDTH_BYTES]

            if self.membw_counter_prev is not None:
                curr_membw = (membw_counter - self.membw_counter_prev) / self.cycle_duration_s
                self.membw_counter_prev = membw_counter
                self._update_stable_counter(curr_membw, referenced)
            else:
                self.membw_counter_prev = membw_counter
                log.warning('task_mem_bandwidth_bytes (one time)! Not measuring WSS!')
                return {}
        else:
            log.warning('task_mem_bandwidth_bytes missing! Not measuring WSS!')
            return {}

        if self.stable_cycles_goal != 0 and self.stable_cycles_counter == self.stable_cycles_goal:
            log.debug('setting new last_stable__task_working_set_size_bytes=%r',
                      self.last_stable__task_working_set_size_bytes)
            self.stable_cycles_counter = 0
            should_reset = True
            measurements[MetricName.TASK_WORKING_SET_SIZE_BYTES] = referenced
            self.last_stable__task_working_set_size_bytes = referenced
        else:
            should_reset = False
            if self.last_stable__task_working_set_size_bytes:
                measurements[MetricName.TASK_WORKING_SET_SIZE_BYTES] = \
                    self.last_stable__task_working_set_size_bytes
            else:
                measurements[MetricName.TASK_WORKING_SET_SIZE_BYTES] = 0

        if (self.dummy_reset_interval is not None and self.cycle % self.dummy_reset_interval == 0)\
                or should_reset:
            log.debug('[%3.0fs] wss: resetting pids: %s ...' %
                      (time.time() - self.started, ','.join(map(str, pids))))
            rstart = time.time()
            self._clear_refs(pids)
            log.debug('[%3.0fs] wss: resetting pids done in %0.2fs' %
                      (time.time() - self.started, time.time() - rstart))
            self.stable_cycles_counter = 0

        return measurements
