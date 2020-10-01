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

log = logging.getLogger(__name__)

MB = 1000000


class WSS:
    def __init__(self, interval: int,
                 get_pids,
                 wss_reset_cycles: int,
                 wss_stable_cycles: int = 0,
                 wss_membw_threshold: Optional[float] = None,
                 ):
        """
        Two metrics are created:
        - TASK_WSS_REFERENCED_BYTES: just raw information read from /proc/{}/smaps
        - TASK_WORKING_SET_SIZE_BYTES: heuristic to calculate working set size,
            depends on threshould_divider wss_stable_cycles and wss_membw_threshold

        For arguments description see: MeasurementRunner class docstring.
        """

        self.get_pids = get_pids

        self.cycle = 0
        self.interval = interval
        self.wss_membw_threshold = wss_membw_threshold

        self.wss_reset_cycles = wss_reset_cycles
        self.wss_stable_cycles = wss_stable_cycles

        # Membw/Referenced delta/rate calculation
        self.prev_referenced = None  # [B]
        self.prev_membw_counter = None  # [B]

        # Internal state, cleared aftre reset.
        self.started = time.time()

        # Used to remember first stable referenced and last measured after reset.
        self.stable_cycles_counter = 0
        self.first_stable_referenced = None
        self.last_stable_wss = None
        log.debug('Enable WSS measurments: interval=%ss '
                  'wss_reset_cycles=%s wss_stable_cycles=%s wss_membw_threshold=%s',
                  interval, wss_reset_cycles, wss_stable_cycles, wss_membw_threshold)


    def _discover_pids(self):
        pids = set(self.get_pids(include_threads=False))
        all_pids = os.listdir('/proc')
        all_pids = set(map(str, filter(lambda x: x.isdecimal(), all_pids)))
        pids = pids & all_pids
        return pids

    def _check_stability(self, curr_membw_counter, curr_referenced, pids_s):
        """Updates stable counter, which tells how many stable cycles in a row there were.
        stable: not changing rapidly in relation to previous values

        curr_membw: [B/s], curr_referenced: [B]
        """

        curr_membw_delta = float(curr_membw_counter - self.prev_membw_counter)
        curr_referenced_delta = float(curr_referenced - self.prev_referenced)

        # eg. 16 GB/s take 1% of it ~ 160 MB/s
        membw_threshold_bytes = float(curr_membw_delta) * self.wss_membw_threshold

        log.debug(
            '[%s] %4ds '
            'REFERENCED: curr=%dMB|delta=%dMB|rate=%.2fMBs '
            'MEMBW: curr=%dMB|delta=%dMB|rate=%.2fMBs|threshold=(%d%%)%.2fMB '
            '-> stable_cycles_counter=%d',
            pids_s, time.time() - self.started,
            curr_referenced/MB, curr_referenced_delta/MB, curr_referenced_delta/self.interval/MB,
            curr_membw_counter/MB, curr_membw_delta/MB, curr_membw_delta/self.interval/MB,
            int(self.wss_membw_threshold * 100), membw_threshold_bytes/MB,
            self.stable_cycles_counter)

        max_decrease_divider = 50  # 2%, sometimes referenced for some unknown reason goes down
        if curr_referenced_delta >= 0 or \
                abs(curr_referenced_delta) < curr_referenced / max_decrease_divider:

            # in case there was less than 2% decrease:
            if curr_referenced_delta < 0:
                curr_referenced_delta = 0

            if curr_referenced_delta < membw_threshold_bytes:
                if self.stable_cycles_counter == 0:
                    self.first_stable_referenced = curr_referenced
                    log.debug('[%s] Store first stable referenced(MB)=%d',
                              pids_s, self.first_stable_referenced/MB)
                self.stable_cycles_counter += 1
                log.debug('[%s] Incrementing stable_cycles_counter+=1 '
                          'curr_referenced_delta < membw_threshold_bytes = True (%.2f<%.2f)',
                          pids_s, curr_referenced_delta/MB, membw_threshold_bytes/MB)
            else:
                self.stable_cycles_counter = 0
                log.debug('[%s] Reset stable_cycles_counter=0 '
                          'curr_referenced_delta < membw_threshold_bytes = False (%.2f<%.2f)',
                          pids_s, curr_referenced_delta/MB, membw_threshold_bytes/MB)
        else:
            self.stable_cycles_counter = 0
            log.warn('[%s] curr_referenced_delta smaller than 0 and '
                     'abs(curr_re...) < curr_referenced/max_decrease_divider; '
                     'resetting stable_cycles_counter', pids_s)

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
        rstart = time.time()
        curr_referenced = self._get_referenced(pids)
        rduration = time.time() - rstart
        measurements[MetricName.TASK_WSS_REFERENCED_BYTES] = curr_referenced

        log.debug(
                '[%s] %4ds cycle=%d, curr_referenced[MB]=%d (took %.2fs)'
                pids_s, time.time() - self.started, self.cycle,
                curr_referenced/MB, rduration)

        should_reset = False
        # Stability reset based on wss_stable_cycles and wss_membw_threshold
        # (only when both values set)
        if self.wss_membw_threshold is not None and self.wss_stable_cycles != 0:
            # Make sure we have RDT/MBW available.
            if rdt_measurements and MetricName.TASK_MEM_BANDWIDTH_BYTES in rdt_measurements:
                curr_membw_counter = rdt_measurements[MetricName.TASK_MEM_BANDWIDTH_BYTES]
                # Check stability only if we have previous MBW/referenced measurements.
                if self.prev_referenced is not None and self.prev_membw_counter is not None:
                    # Check only if in stability period checking...
                    if self.stable_cycles_counter < abs(self.wss_stable_cycles):
                        self._check_stability(curr_membw_counter, curr_referenced, pids_s)
                self.prev_referenced = curr_referenced
                self.prev_membw_counter = curr_membw_counter
            else:
                log.warning('task_mem_bandwidth_bytes is missing (RDT or MBW not available?)!'
                            ' Do not calculate derived task_working_set_size_bytes!')
                return measurements

            # Stability check of stable_cycles_counter and generate task_working_set_size_bytes.
            if self.wss_stable_cycles != 0 and \
                    self.stable_cycles_counter == abs(self.wss_stable_cycles):
                # Additionaly if cycling reseting is disabled, then
                # we should reset referenced bytes when stable.
                # And restart stability check.
                if self.wss_reset_cycles == 0 and self.wss_stable_cycles > 0:
                    should_reset = True
                    self.stable_cycles_counter = 0

                self.last_stable_wss = (self.first_stable_referenced + curr_referenced) / 2

                log.debug('[%s] Calculate last_stable_wss = (%.2f+%.2f)/2 = %.2f MB ',
                          pids_s, self.first_stable_referenced/MB, curr_referenced/MB,
                          self.last_stable_wss/MB)

            # If we have any stable working set size
            if self.last_stable_wss is not None:
                measurements[MetricName.TASK_WORKING_SET_SIZE_BYTES] = self.last_stable_wss

        # Cyclic reset interval based on wss_reset_cycles
        if (self.wss_reset_cycles is not None and self.wss_reset_cycles > 0
                and self.cycle % self.wss_reset_cycles == 0):
            log.debug('[%s] wss: wss_reset_cycles hit - reset the referenced bytes', pids_s)
            should_reset = True

        if should_reset:
            log.debug('[%s] wss: resetting pids ...', pids_s)
            rstart = time.time()
            self._clear_refs(pids)
            log.debug('[%s] wss: resetting pids done in %0.2fs', pids_s, time.time() - rstart)

            # Restart stablity check
            self.stable_cycles_counter = 0
            self.prev_referenced = None
            self.started = time.time()

        return measurements
