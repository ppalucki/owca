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


import errno
import logging
import os

from owca import logger
from owca.allocators import AllocationType, RDTAllocation
from owca.metrics import Measurements, MetricName
from owca.security import SetEffectiveRootUid


RESCTRL_ROOT_NAME = ''
BASE_RESCTRL_PATH = '/sys/fs/resctrl'
MON_GROUPS = 'mon_groups'
TASKS_FILENAME = 'tasks'
SCHEMATA = 'schemata'
INFO = 'info'
MON_DATA = 'mon_data'
MON_L3_00 = 'mon_L3_00'
MBM_TOTAL = 'mbm_total_bytes'
LLC_OCCUPANCY = 'llc_occupancy'
RDT_MB = 'rdt_MB'
RDT_LC = 'rdt_LC'


log = logging.getLogger(__name__)


def get_max_rdt_values(cbm_mask, platform_sockets):

    max_rdt_l3 = []
    max_rdt_mb = []

    for dom_id in range(platform_sockets):
        max_rdt_l3.append('%i=%s' % (dom_id, cbm_mask))
        max_rdt_mb.append('%i=100' % dom_id)

    return 'L3:'+';'.join(max_rdt_l3), 'MB:'+';'.join(max_rdt_mb)


def cleanup_resctrl(root_rdt_l3: str, root_rdt_mb: str):
    """Remove taskless subfolders at resctrl folders to free scarce CLOS and RMID resources. """

    def _remove_folders(initialdir, subfolder):
        for entry in os.listdir(os.path.join(initialdir, subfolder)):
            # Path to folder e.g. mesos-xxx represeting running container.
            directory_path = os.path.join(BASE_RESCTRL_PATH, subfolder, entry)
            # Only examine folders at first level.
            if os.path.isdir(directory_path):
                # Examine tasks file
                resctrl_tasks_path = os.path.join(directory_path, TASKS_FILENAME)
                if not os.path.exists(resctrl_tasks_path):
                    # Skip metadata folders e.g. info.
                    continue
                log.warning('Resctrl: Found ctrl or mon group at %r - recycle CLOS/RMID resource.',
                            directory_path)
                log.log(logger.TRACE, 'resctrl (mon_groups) - cleanup: rmdir(%s)',
                        directory_path)
                os.rmdir(directory_path)

    # Remove all monitoring groups for both CLOS and RMID.
    _remove_folders(BASE_RESCTRL_PATH, MON_GROUPS)
    # Remove all resctrl groups.
    _remove_folders(BASE_RESCTRL_PATH, '')

    # Reinitialize default values for RDT.
    if root_rdt_l3 is not None:
        with open(os.path.join(BASE_RESCTRL_PATH, SCHEMATA), 'bw') as schemata:
            log.log(logger.TRACE, 'resctrl: write(%s): %r', schemata.name, root_rdt_l3)
            try:
                schemata.write(bytes(root_rdt_l3 + '\n', encoding='utf-8'))
                schemata.flush()
            except OSError as e:
                log.error('Cannot set l3 cache allocation: {}'.format(e))

    if root_rdt_mb is not None:
        with open(os.path.join(BASE_RESCTRL_PATH, SCHEMATA), 'bw') as schemata:
            log.log(logger.TRACE, 'resctrl: write(%s): %r', schemata.name, root_rdt_mb)
            try:
                schemata.write(bytes(root_rdt_mb + '\n', encoding='utf-8'))
                schemata.flush()
            except OSError as e:
                log.error('Cannot set rdt memory bandwith allocation: {}'.format(e))


def check_resctrl():
    """
    :return: True if resctrl is mounted and has required file
             False if resctrl is not mounted or required file is missing
    """
    run_anyway_text = 'If you wish to run script anyway,' \
                      'please set rdt_enabled to False in configuration file.'

    resctrl_tasks = os.path.join(BASE_RESCTRL_PATH, TASKS_FILENAME)
    try:
        with open(resctrl_tasks):
            pass
    except IOError as e:
        log.debug('Error: Failed to open %s: %s', resctrl_tasks, e)
        log.critical('Resctrl not mounted. ' + run_anyway_text)
        return False

    mon_data = os.path.join(BASE_RESCTRL_PATH, MON_DATA, MON_L3_00, MBM_TOTAL)
    try:
        with open(mon_data):
            pass
    except IOError as e:
        log.debug('Error: Failed to open %s: %s', mon_data, e)
        log.critical('Resctrl does not support Memory Bandwidth Monitoring.' +
                     run_anyway_text)
        return False

    return True


ResGroupName = str


class ResGroup:

    def __init__(self, name: str, rdt_mb_control_enabled: bool = True):
        self.name: ResGroupName = name
        self.rdt_mb_control_enabled = rdt_mb_control_enabled
        self.fullpath = BASE_RESCTRL_PATH + ("/" + name if name != "" else "")

        if self.name != RESCTRL_ROOT_NAME:
            log.debug('creating restrcl group %r', self.name)
            self._create_controlgroup_directory()

    def __repr__(self):
        return 'ResGroup(name=%r, fullpath=%r)' % (self.name, self.fullpath)

    def _get_mongroup_fullpath(self, mongroup_name) -> str:
        return os.path.join(self.fullpath, MON_GROUPS, mongroup_name)

    def _read_pids_from_tasks_file(self, tasks_filepath):
        with open(tasks_filepath) as ftasks:
            pids = [line.strip() for line in ftasks.readlines() if line != ""]
        log.log(logger.TRACE, 'resctrl: read(%s): found %i pids', tasks_filepath, len(pids))
        return pids

    def _add_pids_to_tasks_file(self, pids, tasks_filepath):
        log.log(logger.TRACE, 'resctrl: write(%s): number_of_pids=%r', tasks_filepath, len(pids))
        with open(tasks_filepath, 'w') as ftasks:
            with SetEffectiveRootUid():
                for pid in pids:
                    try:
                        ftasks.write(pid)
                        ftasks.flush()
                    except ProcessLookupError:
                        log.warning('Could not write pid %s to resctrl (%r). '
                                    'Process probably does not exist. ', pid, tasks_filepath)

    def _create_controlgroup_directory(self):
        """Create control group directory"""
        try:
            log.log(logger.TRACE, 'resctrl: makedirs(%s)', self.fullpath)
            os.makedirs(self.fullpath, exist_ok=True)
        except OSError as e:
            if e.errno == errno.ENOSPC:  # "No space left on device"
                raise Exception("Limit of workloads reached! (Oot of available CLoSes/RMIDs!)")
            raise

    def add_tasks(self, pids, mongroup_name):
        """Adds the pids to the resctrl group and creates mongroup with the pids.
           If the resctrl group does not exists creates it (lazy creation).
           If already the mongroup exists just add the pids (no error will be thrown)."""

        # add pids to /tasks file
        log.debug('add_tasks: %d pids to %r', len(pids), os.path.join(self.fullpath, 'tasks'))
        self._add_pids_to_tasks_file(pids, os.path.join(self.fullpath, 'tasks'))

        # create mongroup and write tasks there
        mongroup_fullpath = self._get_mongroup_fullpath(mongroup_name)
        try:
            log.log(logger.TRACE, 'resctrl: makedirs(%s)', mongroup_fullpath)
            os.makedirs(mongroup_fullpath, exist_ok=True)
        except OSError as e:
            if e.errno == errno.ENOSPC:  # "No space left on device"
                raise Exception("Limit of workloads reached! (Oot of available CLoSes/RMIDs!)")
            raise

        # write the pids to the mongroup
        log.debug('add_tasks: %d pids to %r', len(pids), os.path.join(mongroup_fullpath, 'tasks'))
        self._add_pids_to_tasks_file(pids, os.path.join(mongroup_fullpath, 'tasks'))

    def remove_tasks(self, mongroup_name):
        """Removes the mongroup and all pids inside it from the resctrl group
           (by adding all the pids to the ROOT resctrl group).
           If the mongroup path does not points to existing directory
           just immediatelly returning."""

        mongroup_fullpath = self._get_mongroup_fullpath(mongroup_name)

        if not os.path.isdir(mongroup_fullpath):
            log.debug('Trying to remove {} but the directory does not exist.'
                      .format(mongroup_fullpath))
            return

        # Read tasks that belongs to the mongroup.
        pids = self._read_pids_from_tasks_file(os.path.join(mongroup_fullpath, 'tasks'))

        # Remove the mongroup directory.
        log.log(logger.TRACE, 'resctrl: rmdir(%r)', mongroup_fullpath)
        os.rmdir(mongroup_fullpath)

        # Removes tasks from the group by adding it to the root group.
        self._add_pids_to_tasks_file(pids, os.path.join(BASE_RESCTRL_PATH, 'tasks'))

    def get_measurements(self, mongroup_name) -> Measurements:
        """
        mbm_total: Memory bandwidth - type: counter, unit: [bytes]
        :return: Dictionary containing memory bandwidth
        and cpu usage measurements
        """
        mbm_total = 0
        llc_occupancy = 0

        def _get_event_file(mon_dir, event_name):
            return os.path.join(self.fullpath, MON_GROUPS, mongroup_name,
                                MON_DATA, mon_dir, event_name)

        # mon_dir contains event files for specific socket:
        # llc_occupancy, mbm_total_bytes, mbm_local_bytes
        for mon_dir in os.listdir(os.path.join(self.fullpath, MON_GROUPS, mongroup_name, MON_DATA)):
            with open(_get_event_file(mon_dir, MBM_TOTAL)) as mbm_total_file:
                mbm_total += int(mbm_total_file.read())
            with open(_get_event_file(mon_dir, LLC_OCCUPANCY)) as llc_occupancy_file:
                llc_occupancy += int(llc_occupancy_file.read())

        return {MetricName.MEM_BW: mbm_total, MetricName.LLC_OCCUPANCY: llc_occupancy}

    def get_allocations(self, resgroup_name):
        rdt_allocations = RDTAllocation(name=resgroup_name)
        with open(os.path.join(self.fullpath, SCHEMATA)) as schemata:
            for line in schemata:
                if 'MB' in line:
                    rdt_allocations.mb = line.strip()
                elif 'L3' in line:
                    rdt_allocations.l3 = line.strip()

        return {AllocationType.RDT: rdt_allocations}

    def perform_allocations(self, task_allocations):
        with open(os.path.join(self.fullpath, SCHEMATA), 'bw') as schemata:

            # Cache control: TODO make it optional
            if (AllocationType.RDT in task_allocations and
                    task_allocations[AllocationType.RDT].l3 is not None):
                value = task_allocations[AllocationType.RDT].l3
                log.log(logger.TRACE, 'resctrl: write(%s): %r', schemata.name, value)
                try:
                    schemata.write(bytes(value + '\n', encoding='utf-8'))
                    schemata.flush()
                except OSError as e:
                    log.error('Cannot set l3 cache allocation: {}'.format(e))

            # Optional: Memory BW allocatoin
            if self.rdt_mb_control_enabled:

                if (AllocationType.RDT in task_allocations and
                        task_allocations[AllocationType.RDT].mb is not None):
                    value = task_allocations[AllocationType.RDT].mb
                    log.log(logger.TRACE, 'resctrl: write(%s): %r', schemata.name, value)
                    try:
                        schemata.write(bytes(value + '\n', encoding='utf-8'))
                        schemata.flush()
                    except OSError as e:
                        log.error('Cannot set rdt memory bandwith allocation: {}'.format(e))

    def cleanup(self):
        # Do not try to remove root group.
        if self.name == RESCTRL_ROOT_NAME:
            return
        try:
            log.log(logger.TRACE, 'resctrl: rmdir(%s)', self.fullpath)
            os.rmdir(self.fullpath)
        except FileNotFoundError:
            pass
