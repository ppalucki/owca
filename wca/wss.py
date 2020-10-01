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

        self.overhead_seconds = 0
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
        self.started_cycle = time.time()
        self.started_total = self.started_cycle

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

        max_decrease_divider = 50  # 2%, sometimes referenced for some unknown reason goes down
        decision = ''
        if curr_referenced_delta >= 0 or \
                abs(curr_referenced_delta) < curr_referenced / max_decrease_divider:

            # in case there was less than 2% decrease:
            if curr_referenced_delta < 0:
                curr_referenced_delta = 0

            if curr_referenced_delta < membw_threshold_bytes:
                if self.stable_cycles_counter == 0:
                    self.first_stable_referenced = curr_referenced
                    decision += ' remember %dMB' % (
                        self.first_stable_referenced/MB)
                self.stable_cycles_counter += 1
                decision += ' inc stable (%.2f<%.2f)' % (
                    curr_referenced_delta/MB, membw_threshold_bytes/MB)
            else:
                self.stable_cycles_counter = 0
                decision += ' reset (%.2f<%.2f)' % (
                    curr_referenced_delta/MB, membw_threshold_bytes/MB)

        else:
            self.stable_cycles_counter = 0
            decision += ' reset (refer_delta(%.2fMB)<0)' % (curr_referenced_delta/MB)

        log.debug(
            '[%s] %4ds '
            'REFER: delta=%dMB|rate=%.2fMBs '
            'MEMBW: delta=%dMB|rate=%.2fMBs|threshold=(%d%%)%.2fMB%s '
            '-> stable_counter=%d',
            pids_s, time.time() - self.started_cycle,
            curr_referenced_delta/MB, curr_referenced_delta/self.interval/MB,
            curr_membw_delta/MB, curr_membw_delta/self.interval/MB,
            int(self.wss_membw_threshold * 100), membw_threshold_bytes/MB,
            decision,
            self.stable_cycles_counter)

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
        pids_s = ','.join(map(str, pids)) if len(pids) < 5 else '%s,...(%s)' % (pids[0], len(pids))
        rstart = time.time()
        curr_referenced = self._get_referenced(pids)
        rduration = time.time() - rstart
        self.overhead_seconds += rduration
        measurements[MetricName.TASK_WSS_REFERENCED_BYTES] = curr_referenced
        measurements[MetricName.TASK_WSS_MEASURE_OVERHEAD_SECONDS] = self.overhead_seconds

        overhead_ratio = (self.overhead_seconds / (time.time() - self.started_total))
        log.debug(
                '[%s] %4ds cycle=%d curr_refer=%dMB (took %.2fs, overhead=%.2fs(%.2f%%))',
                pids_s, time.time() - self.started_cycle, self.cycle,
                curr_referenced/MB, rduration, self.overhead_seconds,
                overhead_ratio * 100)

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
                log.warning('task_mem_bandwidth_bytes metric is missing! '
                            '(please enable RDT and MBW!) '
                            ' task_working_set_size_bytes metric will not be measured!')
                return measurements

            # Stability check of stable_cycles_counter and generate task_working_set_size_bytes.
            if self.wss_stable_cycles != 0 and \
                    self.stable_cycles_counter == abs(self.wss_stable_cycles):

                # Calculate average of referenced bytes in stable period.
                self.last_stable_wss = (self.first_stable_referenced + curr_referenced) / 2

                log.debug('[%s] WSS is stable = (%.2f+%.2f)/2 = %.2f MB ',
                          pids_s, self.first_stable_referenced/MB, curr_referenced/MB,
                          self.last_stable_wss/MB)

                # Additionaly if cycling reseting is disabled, then
                # we should reset referenced bytes when stable.
                # And restart stability check.
                if self.wss_reset_cycles == 0 and self.wss_stable_cycles > 0:
                    should_reset = True
                    log.debug('[%s] Referenced bytes STABLE reseting...', pids_s)

                # move stable counter above a limit to catch stable just once,
                # case above (reset) will reset it anyway
                self.stable_cycles_counter += 1

            # If we have any stable working set size
            if self.last_stable_wss is not None:
                measurements[MetricName.TASK_WORKING_SET_SIZE_BYTES] = self.last_stable_wss

        # Cyclic reset interval based on wss_reset_cycles
        if (self.wss_reset_cycles is not None and self.wss_reset_cycles > 0
                and self.cycle % self.wss_reset_cycles == 0):
            log.debug('[%s] Referenced bytes CYCLIC reseting...', pids_s)
            should_reset = True

        if should_reset:
            log.log(TRACE, '[%s] Resetting referenced bytes for %s pids ...', pids_s, len(pids))
            rstart = time.time()
            self._clear_refs(pids)
            rduration = time.time() - rstart
            log.debug('[%s] Reset referenced bytes for %s pids done in %0.2fs',
                      pids_s, len(pids), rduration)
            self.overhead_seconds += rduration

            # Restart stablity check
            self.stable_cycles_counter = 0
            self.prev_referenced = None
            self.started_cycle = time.time()

        return measurements
