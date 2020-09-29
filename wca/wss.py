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
from typing import Optional

from wca.metrics import Measurements, MetricName
from wca.logger import TRACE

log = logging.getLogger(__name__)

MB = 1000000


class WSS:
    def __init__(self, interval, get_pids,
                 wss_reset_interval=-1,
                 wss_stable_duration=30,
                 wss_mbw_fraction: Optional[float] = None,
                 wss_ref_fraction: Optional[float] = None,
                 ):
        """
        Two metrics are created:
        - TASK_WSS_REFERENCED_BYTES: just raw information read from /proc/{}/smaps,
            reset can be controlled by dummy_reset_interval and stable_cycles_goal
        - TASK_WORKING_SET_SIZE_BYTES: heuristic to calculate working set size,
            depends on threshould_divider and stable_cycles_counter

        @Args:
        interval
            duration of single cycle in seconds
        wss_reset_interval
            despite everything just reset referenced [number of cycles]
        wss_stable_duration
            how many stable measurements of >>referenced<< must happen [number of cycles]
            before setting TASK_WORKING_SET_SIZE_BYTES
        wss_mbw_fraction
            if increase in referenced bytes is below this threshold of membw fraction
            then assume referenced is stable (not increasing enough)
        wss_ref_fraction
            if increase in referenced bytes is below this
            threshold of referenced bytes since reset  fraction
            then assume referenced is stable (not increasing enough)
        """

        self.get_pids = get_pids

        self.cycle = 0
        self.interval = interval
        self.wss_mbw_fraction = wss_mbw_fraction
        self.wss_ref_fraction = wss_ref_fraction

        self.wss_reset_interval = wss_reset_interval if wss_reset_interval != -1 else None

        self.wss_stable_duration = wss_stable_duration  # in cycles

        # Membw calculation
        self.membw_counter_prev = None  # [B]
        self.prev_membw = None  # [B/s]

        # Internal state, cleared aftre reset.
        self.started = time.time()
        self.stable_cycles_counter = 0
        self.prev_referenced = None  # [B]

        # Used to remember first stable referenced
        self.stable_referenced = None

        # Keep last value of metric TASK_WORKING_SET_SIZE_BYTES
        self.last_stable__task_working_set_size_bytes = None  # [B]

    def _discover_pids(self):
        pids = set(self.get_pids(include_threads=False))
        all_pids = os.listdir('/proc')
        all_pids = set(map(str, filter(lambda x: x.isdecimal(), all_pids)))
        pids = pids & all_pids
        return pids

    def _update_stable_counter(self, curr_membw, curr_referenced, pids_s):
        """Updates stable counter, which tells how many stable cycles in a row there were.
        stable: not changing rapidly in relation to previous values

        curr_membw: [B/s], curr_referenced: [B]
        """

        log.log(TRACE,
                '[%s] cycle=%d, curr_referenced[MB]=%d '
                'stable_cycles_counter=%d',
                pids_s, self.cycle, curr_referenced/MB, self.stable_cycles_counter)

        if self.prev_referenced is not None and self.prev_membw is not None:
            curr_referenced_delta = \
                float(curr_referenced - self.prev_referenced) / self.interval
            curr_membw_delta = float(curr_membw - self.prev_membw) / self.interval

            # eg. 16 GB/s take 1% of it ~ 160 MB/s
            membw_threshold = (float(curr_membw) * self.wss_mbw_fraction
                               if self.wss_mbw_fraction is not None else None)
            referenced_threshold = (float(curr_referenced) * self.wss_ref_fraction
                                    if self.wss_ref_fraction is not None else None)

            log.debug(
                '[%s] %4ds '
                'MEMBW[MB/s]: curr=%.2f/delta=%.2f/fraction=%s/threshold=%s | '
                'REFERENCED[MB]: curr=%.2f/delta=%.2f/fraction=%s/threshold=%s '
                '-> stable_cycles_counter=%d',
                pids_s, time.time() - self.started,
                curr_membw/MB, curr_membw_delta/MB, self.wss_mbw_fraction,
                '%.2f' % (membw_threshold/MB) if membw_threshold is not None else 'None',
                curr_referenced/MB, curr_referenced_delta/MB, self.wss_ref_fraction,
                '%.2f' % (referenced_threshold/MB) if referenced_threshold is not None else 'None',
                self.stable_cycles_counter)

            max_decrease_divider = 50  # Sometimes referenced for some unknown reason goes down.
            if curr_referenced_delta >= 0 or \
                    abs(curr_referenced_delta) < curr_referenced / max_decrease_divider:

                # Both conditions are optional
                lower_than_membw = (membw_threshold is not None
                                    and curr_referenced_delta < membw_threshold)
                if lower_than_membw:
                    log.debug('mbw_condition met: referenced_delta < membw_threshold (%.2f<%.2f)',
                              curr_referenced_delta/MB, membw_threshold/MB)

                lower_than_ref = (referenced_threshold is not None
                                  and curr_referenced_delta < referenced_threshold)
                if lower_than_ref:
                    log.debug('ref_condition met: referenced_delta '
                              '< reference_threshold (%.2f<%.2f)',
                              curr_referenced_delta/MB, referenced_threshold/MB)

                if lower_than_membw or lower_than_ref:
                    if self.stable_cycles_counter == 0:
                        self.stable_referenced = curr_referenced
                        log.debug('[%s] Store first stable referenced(MB)=%d',
                                  pids_s, self.stable_referenced/MB)
                    self.stable_cycles_counter += 1
                    log.debug('[%s] Incrementing stable_cycles_counter+=1 '
                              '(lower_than_membw=%s, lower_than_ref=%s)',
                              pids_s, lower_than_membw, lower_than_ref)
                else:
                    self.stable_cycles_counter = 0
                    log.log(TRACE, '[%s] none of thresholds were met (membw, wss)'
                            'reset stable_cycles_counter', pids_s)
            else:
                self.stable_cycles_counter = 0
                log.warn('[%s] curr_referenced_delta smaller than 0 and '
                         'abs(curr_re...) < curr_referenced/max_decrease_divider; '
                         'resetting stable_cycles_counter', pids_s)
        else:
            log.log(TRACE,
                    '[%s] previous value of membw or referenced not available -'
                    ' resetting stable_cycles_counter', pids_s)

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
        pids = list(self._discover_pids())
        pids_s = ','.join(map(str, pids)) if len(pids) < 5 else '%s,...,%s' % (pids[0], pids[-1])
        referenced = self._get_referenced(pids)
        measurements[MetricName.TASK_WSS_REFERENCED_BYTES] = referenced

        # Update measurements (including membw calculation)
        # and if thresholds are met, increament stable counter (stable_cycles_counter).
        if rdt_measurements and MetricName.TASK_MEM_BANDWIDTH_BYTES in rdt_measurements:
            membw_counter = rdt_measurements[MetricName.TASK_MEM_BANDWIDTH_BYTES]

            if self.membw_counter_prev is not None:
                curr_membw = (membw_counter - self.membw_counter_prev) / self.interval
                log.log(TRACE, '[%s] curr_membw=%s (counter=%s prev=%s)', pids_s, curr_membw,
                        membw_counter, self.membw_counter_prev)
                self.membw_counter_prev = membw_counter
                self._update_stable_counter(curr_membw, referenced, pids_s)
            else:
                self.membw_counter_prev = membw_counter
                log.debug('[%s] task_mem_bandwidth_bytes (one time) missing! Not measuring WSS!',
                          pids_s)
                return {}
        else:
            log.warning('task_mem_bandwidth_bytes missing! Not measuring WSS!')
            return {}

        # Stability check of stable_cycles_counter and generate task_working_set_size_bytes.
        if self.wss_stable_duration != 0 and self.stable_cycles_counter == self.wss_stable_duration:
            log.debug('[%s] setting new last_stable__task_working_set_size[MB] =%.2f',
                      pids_s, referenced/MB)
            self.stable_cycles_counter = 0
            should_reset = True
            measurements[MetricName.TASK_WORKING_SET_SIZE_BYTES] = self.stable_referenced
            self.last_stable__task_working_set_size_bytes = self.stable_referenced
        else:
            should_reset = False
            if self.last_stable__task_working_set_size_bytes:
                measurements[MetricName.TASK_WORKING_SET_SIZE_BYTES] = \
                    self.last_stable__task_working_set_size_bytes
            else:
                measurements[MetricName.TASK_WORKING_SET_SIZE_BYTES] = 0

        # Cyclic reset interval
        if (self.wss_reset_interval is not None and self.cycle % self.wss_reset_interval == 0):
            log.debug('[%s] wss: dummy reset interval hit cycle - reset the pids', pids_s)
            should_reset = True

        if should_reset:
            log.debug('[%s] wss: resetting pids ...', pids_s)
            rstart = time.time()
            self._clear_refs(pids)
            log.debug('[%s] wss: resetting pids done in %0.2fs', pids_s, time.time() - rstart)
            self.stable_cycles_counter = 0
            self.prev_referenced = None
            self.started = time.time()

        return measurements
