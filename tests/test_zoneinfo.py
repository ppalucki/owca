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
import re
from unittest.mock import patch

from tests.testing import create_open_mock, relative_module_path
from wca.metrics import MetricName
from wca.zoneinfo import get_zoneinfo_measurements, DEFAULT_REGEXP


@patch('builtins.open', new=create_open_mock({
    "/proc/zoneinfo": open(relative_module_path(__file__, 'fixtures/proc-zoneinfo.txt')).read(),
}))
def test_parse_proc_zoneinfo(*mocks):
    zoneinfo_measurements = get_zoneinfo_measurements(re.compile(DEFAULT_REGEXP))[MetricName.PLATFORM_ZONEINFO]
    assert zoneinfo_measurements == {
 '0': {'DMA': {'high': 6.0,
               'hmem_autonuma_promote_dst': 0.0,
               'hmem_autonuma_promote_src': 0.0,
               'hmem_reclaim_demote_dst': 0.0,
               'hmem_reclaim_demote_src': 0.0,
               'hmem_reclaim_promote_dst': 0.0,
               'hmem_reclaim_promote_src': 0.0,
               'hmem_swapcache_promote_dst': 0.0,
               'hmem_swapcache_promote_src': 0.0,
               'hmem_unknown': 0.0,
               'low': 3.0,
               'managed': 3867.0,
               'min': 0.0,
               'nr_bounce': 0.0,
               'nr_free_cma': 0.0,
               'nr_free_pages': 3867.0,
               'nr_kernel_stack': 0.0,
               'nr_mlock': 0.0,
               'nr_page_table_pages': 0.0,
               'nr_zone_active_anon': 0.0,
               'nr_zone_active_file': 0.0,
               'nr_zone_inactive_anon': 0.0,
               'nr_zone_inactive_file': 0.0,
               'nr_zone_unevictable': 0.0,
               'nr_zone_write_pending': 0.0,
               'nr_zspages': 0.0,
               'numa_foreign': 0.0,
               'numa_hit': 0.0,
               'numa_interleave': 0.0,
               'numa_local': 0.0,
               'numa_miss': 0.0,
               'numa_other': 0.0,
               'present': 3999.0,
               'spanned': 4095.0,
               'toptier': 773.0},
       'DMA32': {'high': 868.0,
                 'hmem_autonuma_promote_dst': 0.0,
                 'hmem_autonuma_promote_src': 0.0,
                 'hmem_reclaim_demote_dst': 0.0,
                 'hmem_reclaim_demote_src': 0.0,
                 'hmem_reclaim_promote_dst': 0.0,
                 'hmem_reclaim_promote_src': 0.0,
                 'hmem_swapcache_promote_dst': 0.0,
                 'hmem_swapcache_promote_src': 0.0,
                 'hmem_unknown': 0.0,
                 'low': 445.0,
                 'managed': 423884.0,
                 'min': 22.0,
                 'nr_bounce': 0.0,
                 'nr_free_cma': 0.0,
                 'nr_free_pages': 423157.0,
                 'nr_kernel_stack': 0.0,
                 'nr_mlock': 0.0,
                 'nr_page_table_pages': 0.0,
                 'nr_zone_active_anon': 0.0,
                 'nr_zone_active_file': 0.0,
                 'nr_zone_inactive_anon': 0.0,
                 'nr_zone_inactive_file': 0.0,
                 'nr_zone_unevictable': 0.0,
                 'nr_zone_write_pending': 0.0,
                 'nr_zspages': 0.0,
                 'numa_foreign': 0.0,
                 'numa_hit': 0.0,
                 'numa_interleave': 0.0,
                 'numa_local': 0.0,
                 'numa_miss': 0.0,
                 'numa_other': 0.0,
                 'present': 441081.0,
                 'spanned': 1044480.0,
                 'toptier': 84776.0},
       'Device': {'high': 0.0,
                  'low': 0.0,
                  'managed': 0.0,
                  'min': 0.0,
                  'present': 0.0,
                  'spanned': 132120576.0,
                  'toptier': 0.0},
       'Movable': {'high': 0.0,
                   'low': 0.0,
                   'managed': 0.0,
                   'min': 0.0,
                   'present': 0.0,
                   'spanned': 0.0,
                   'toptier': 0.0},
       'Normal': {'high': 49232.0,
                  'hmem_autonuma_promote_dst': 0.0,
                  'hmem_autonuma_promote_src': 0.0,
                  'hmem_reclaim_demote_dst': 0.0,
                  'hmem_reclaim_demote_src': 0.0,
                  'hmem_reclaim_promote_dst': 0.0,
                  'hmem_reclaim_promote_src': 0.0,
                  'hmem_swapcache_promote_dst': 0.0,
                  'hmem_swapcache_promote_src': 0.0,
                  'hmem_unknown': 0.0,
                  'low': 25251.0,
                  'managed': 23981257.0,
                  'min': 1270.0,
                  'nr_bounce': 0.0,
                  'nr_free_cma': 0.0,
                  'nr_free_pages': 21182724.0,
                  'nr_kernel_stack': 15848.0,
                  'nr_mlock': 0.0,
                  'nr_page_table_pages': 1398.0,
                  'nr_zone_active_anon': 63788.0,
                  'nr_zone_active_file': 36524.0,
                  'nr_zone_inactive_anon': 8651.0,
                  'nr_zone_inactive_file': 154408.0,
                  'nr_zone_unevictable': 0.0,
                  'nr_zone_write_pending': 23.0,
                  'nr_zspages': 0.0,
                  'numa_foreign': 0.0,
                  'numa_hit': 10292075.0,
                  'numa_interleave': 36453.0,
                  'numa_local': 10282684.0,
                  'numa_miss': 0.0,
                  'numa_other': 9391.0,
                  'present': 24379392.0,
                  'spanned': 24379392.0,
                  'toptier': 4796251.0},
       'per-node-stats': {'nr_accessed': 52673413.0,
                          'nr_active_anon': 63788.0,
                          'nr_active_file': 36524.0,
                          'nr_anon_pages': 69794.0,
                          'nr_anon_transparent_hugepages': 0.0,
                          'nr_dirtied': 101138.0,
                          'nr_dirty': 23.0,
                          'nr_file_hugepages': 0.0,
                          'nr_file_pages': 193171.0,
                          'nr_file_pmdmapped': 0.0,
                          'nr_inactive_anon': 8651.0,
                          'nr_inactive_file': 154408.0,
                          'nr_isolated_anon': 0.0,
                          'nr_isolated_file': 0.0,
                          'nr_kernel_misc_reclaimable': 0.0,
                          'nr_mapped': 49112.0,
                          'nr_promote_fail': 0.0,
                          'nr_promote_isolate_fail': 0.0,
                          'nr_promote_ratelimit': 0.0,
                          'nr_promoted': 0.0,
                          'nr_shmem': 8817.0,
                          'nr_shmem_hugepages': 0.0,
                          'nr_shmem_pmdmapped': 0.0,
                          'nr_slab_reclaimable': 31387.0,
                          'nr_slab_unreclaimable': 93095.0,
                          'nr_unevictable': 0.0,
                          'nr_unstable': 0.0,
                          'nr_vmscan_immediate_reclaim': 0.0,
                          'nr_vmscan_write': 0.0,
                          'nr_writeback': 0.0,
                          'nr_writeback_temp': 0.0,
                          'nr_written': 96446.0,
                          'numa_try_migrate': 0.0,
                          'workingset_activate': 0.0,
                          'workingset_nodereclaim': 0.0,
                          'workingset_nodes': 0.0,
                          'workingset_refault': 0.0,
                          'workingset_restore': 0.0}},
 '1': {'DMA': {'high': 0.0,
               'low': 0.0,
               'managed': 0.0,
               'min': 0.0,
               'present': 0.0,
               'spanned': 0.0,
               'toptier': 0.0},
       'DMA32': {'high': 0.0,
                 'low': 0.0,
                 'managed': 0.0,
                 'min': 0.0,
                 'present': 0.0,
                 'spanned': 0.0,
                 'toptier': 0.0},
       'Device': {'high': 0.0,
                  'low': 0.0,
                  'managed': 0.0,
                  'min': 0.0,
                  'present': 0.0,
                  'spanned': 0.0,
                  'toptier': 0.0},
       'Movable': {'high': 0.0,
                   'low': 0.0,
                   'managed': 0.0,
                   'min': 0.0,
                   'present': 0.0,
                   'spanned': 0.0,
                   'toptier': 0.0},
       'Normal': {'high': 50850.0,
                  'hmem_autonuma_promote_dst': 0.0,
                  'hmem_autonuma_promote_src': 0.0,
                  'hmem_reclaim_demote_dst': 0.0,
                  'hmem_reclaim_demote_src': 0.0,
                  'hmem_reclaim_promote_dst': 0.0,
                  'hmem_reclaim_promote_src': 0.0,
                  'hmem_swapcache_promote_dst': 0.0,
                  'hmem_swapcache_promote_src': 0.0,
                  'hmem_unknown': 0.0,
                  'low': 26081.0,
                  'managed': 24769969.0,
                  'min': 1312.0,
                  'nr_bounce': 0.0,
                  'nr_free_cma': 0.0,
                  'nr_free_pages': 3122809.0,
                  'nr_kernel_stack': 13320.0,
                  'nr_mlock': 0.0,
                  'nr_page_table_pages': 39236.0,
                  'nr_zone_active_anon': 19239370.0,
                  'nr_zone_active_file': 10230.0,
                  'nr_zone_inactive_anon': 4154.0,
                  'nr_zone_inactive_file': 110142.0,
                  'nr_zone_unevictable': 0.0,
                  'nr_zone_write_pending': 1.0,
                  'nr_zspages': 0.0,
                  'numa_foreign': 0.0,
                  'numa_hit': 28865491.0,
                  'numa_interleave': 36459.0,
                  'numa_local': 28792852.0,
                  'numa_miss': 0.0,
                  'numa_other': 72639.0,
                  'present': 25165824.0,
                  'spanned': 25165824.0,
                  'toptier': 4953993.0},
       'per-node-stats': {'nr_accessed': 5245474.0,
                          'nr_active_anon': 19239370.0,
                          'nr_active_file': 10230.0,
                          'nr_anon_pages': 19242205.0,
                          'nr_anon_transparent_hugepages': 0.0,
                          'nr_dirtied': 80350.0,
                          'nr_dirty': 1.0,
                          'nr_file_hugepages': 0.0,
                          'nr_file_pages': 121210.0,
                          'nr_file_pmdmapped': 0.0,
                          'nr_inactive_anon': 4154.0,
                          'nr_inactive_file': 110142.0,
                          'nr_isolated_anon': 0.0,
                          'nr_isolated_file': 0.0,
                          'nr_kernel_misc_reclaimable': 0.0,
                          'nr_mapped': 34312.0,
                          'nr_promote_fail': 0.0,
                          'nr_promote_isolate_fail': 0.0,
                          'nr_promote_ratelimit': 0.0,
                          'nr_promoted': 0.0,
                          'nr_shmem': 4208.0,
                          'nr_shmem_hugepages': 0.0,
                          'nr_shmem_pmdmapped': 0.0,
                          'nr_slab_reclaimable': 22947.0,
                          'nr_slab_unreclaimable': 74730.0,
                          'nr_unevictable': 0.0,
                          'nr_unstable': 0.0,
                          'nr_vmscan_immediate_reclaim': 0.0,
                          'nr_vmscan_write': 0.0,
                          'nr_writeback': 0.0,
                          'nr_writeback_temp': 0.0,
                          'nr_written': 76640.0,
                          'numa_try_migrate': 0.0,
                          'workingset_activate': 0.0,
                          'workingset_nodereclaim': 0.0,
                          'workingset_nodes': 0.0,
                          'workingset_refault': 0.0,
                          'workingset_restore': 0.0}},
 '2': {'DMA': {'high': 0.0,
               'low': 0.0,
               'managed': 0.0,
               'min': 0.0,
               'present': 0.0,
               'spanned': 0.0,
               'toptier': 0.0},
       'DMA32': {'high': 0.0,
                 'low': 0.0,
                 'managed': 0.0,
                 'min': 0.0,
                 'present': 0.0,
                 'spanned': 0.0,
                 'toptier': 0.0},
       'Device': {'high': 0.0,
                  'low': 0.0,
                  'managed': 0.0,
                  'min': 0.0,
                  'present': 0.0,
                  'spanned': 0.0,
                  'toptier': 0.0},
       'Movable': {'high': 0.0,
                   'low': 0.0,
                   'managed': 0.0,
                   'min': 0.0,
                   'present': 0.0,
                   'spanned': 0.0,
                   'toptier': 0.0},
       'Normal': {'high': 266935.0,
                  'hmem_autonuma_promote_dst': 0.0,
                  'hmem_autonuma_promote_src': 0.0,
                  'hmem_reclaim_demote_dst': 0.0,
                  'hmem_reclaim_demote_src': 0.0,
                  'hmem_reclaim_promote_dst': 0.0,
                  'hmem_reclaim_promote_src': 0.0,
                  'hmem_swapcache_promote_dst': 0.0,
                  'hmem_swapcache_promote_src': 0.0,
                  'hmem_unknown': 0.0,
                  'low': 136912.0,
                  'managed': 130023424.0,
                  'min': 6889.0,
                  'nr_bounce': 0.0,
                  'nr_free_cma': 0.0,
                  'nr_free_pages': 130023387.0,
                  'nr_kernel_stack': 0.0,
                  'nr_mlock': 0.0,
                  'nr_page_table_pages': 0.0,
                  'nr_zone_active_anon': 0.0,
                  'nr_zone_active_file': 0.0,
                  'nr_zone_inactive_anon': 0.0,
                  'nr_zone_inactive_file': 0.0,
                  'nr_zone_unevictable': 0.0,
                  'nr_zone_write_pending': 0.0,
                  'nr_zspages': 0.0,
                  'numa_foreign': 0.0,
                  'numa_hit': 16.0,
                  'numa_interleave': 0.0,
                  'numa_local': 0.0,
                  'numa_miss': 0.0,
                  'numa_other': 16.0,
                  'present': 130023424.0,
                  'spanned': 130023424.0,
                  'toptier': 26004684.0},
       'per-node-stats': {'nr_accessed': 0.0,
                          'nr_active_anon': 0.0,
                          'nr_active_file': 0.0,
                          'nr_anon_pages': 0.0,
                          'nr_anon_transparent_hugepages': 0.0,
                          'nr_dirtied': 0.0,
                          'nr_dirty': 0.0,
                          'nr_file_hugepages': 0.0,
                          'nr_file_pages': 0.0,
                          'nr_file_pmdmapped': 0.0,
                          'nr_inactive_anon': 0.0,
                          'nr_inactive_file': 0.0,
                          'nr_isolated_anon': 0.0,
                          'nr_isolated_file': 0.0,
                          'nr_kernel_misc_reclaimable': 0.0,
                          'nr_mapped': 0.0,
                          'nr_promote_fail': 0.0,
                          'nr_promote_isolate_fail': 0.0,
                          'nr_promote_ratelimit': 0.0,
                          'nr_promoted': 0.0,
                          'nr_shmem': 0.0,
                          'nr_shmem_hugepages': 0.0,
                          'nr_shmem_pmdmapped': 0.0,
                          'nr_slab_reclaimable': 0.0,
                          'nr_slab_unreclaimable': 37.0,
                          'nr_unevictable': 0.0,
                          'nr_unstable': 0.0,
                          'nr_vmscan_immediate_reclaim': 0.0,
                          'nr_vmscan_write': 0.0,
                          'nr_writeback': 0.0,
                          'nr_writeback_temp': 0.0,
                          'nr_written': 0.0,
                          'numa_try_migrate': 0.0,
                          'workingset_activate': 0.0,
                          'workingset_nodereclaim': 0.0,
                          'workingset_nodes': 0.0,
                          'workingset_refault': 0.0,
                          'workingset_restore': 0.0}},
 '3': {'DMA': {'high': 0.0,
               'low': 0.0,
               'managed': 0.0,
               'min': 0.0,
               'present': 0.0,
               'spanned': 0.0,
               'toptier': 0.0},
       'DMA32': {'high': 0.0,
                 'low': 0.0,
                 'managed': 0.0,
                 'min': 0.0,
                 'present': 0.0,
                 'spanned': 0.0,
                 'toptier': 0.0},
       'Device': {'high': 0.0,
                  'low': 0.0,
                  'managed': 0.0,
                  'min': 0.0,
                  'present': 0.0,
                  'spanned': 0.0,
                  'toptier': 0.0},
       'Movable': {'high': 0.0,
                   'low': 0.0,
                   'managed': 0.0,
                   'min': 0.0,
                   'present': 0.0,
                   'spanned': 0.0,
                   'toptier': 0.0},
       'Normal': {'high': 266935.0,
                  'hmem_autonuma_promote_dst': 0.0,
                  'hmem_autonuma_promote_src': 0.0,
                  'hmem_reclaim_demote_dst': 0.0,
                  'hmem_reclaim_demote_src': 0.0,
                  'hmem_reclaim_promote_dst': 0.0,
                  'hmem_reclaim_promote_src': 0.0,
                  'hmem_swapcache_promote_dst': 0.0,
                  'hmem_swapcache_promote_src': 0.0,
                  'hmem_unknown': 0.0,
                  'low': 136912.0,
                  'managed': 130023424.0,
                  'min': 6889.0,
                  'nr_bounce': 0.0,
                  'nr_free_cma': 0.0,
                  'nr_free_pages': 130023140.0,
                  'nr_kernel_stack': 0.0,
                  'nr_mlock': 0.0,
                  'nr_page_table_pages': 0.0,
                  'nr_zone_active_anon': 0.0,
                  'nr_zone_active_file': 0.0,
                  'nr_zone_inactive_anon': 0.0,
                  'nr_zone_inactive_file': 0.0,
                  'nr_zone_unevictable': 0.0,
                  'nr_zone_write_pending': 0.0,
                  'nr_zspages': 0.0,
                  'numa_foreign': 0.0,
                  'numa_hit': 102.0,
                  'numa_interleave': 0.0,
                  'numa_local': 0.0,
                  'numa_miss': 0.0,
                  'numa_other': 102.0,
                  'present': 130023424.0,
                  'spanned': 130023424.0,
                  'toptier': 26004684.0},
       'per-node-stats': {'nr_accessed': 0.0,
                          'nr_active_anon': 0.0,
                          'nr_active_file': 0.0,
                          'nr_anon_pages': 0.0,
                          'nr_anon_transparent_hugepages': 0.0,
                          'nr_dirtied': 0.0,
                          'nr_dirty': 0.0,
                          'nr_file_hugepages': 0.0,
                          'nr_file_pages': 0.0,
                          'nr_file_pmdmapped': 0.0,
                          'nr_inactive_anon': 0.0,
                          'nr_inactive_file': 0.0,
                          'nr_isolated_anon': 0.0,
                          'nr_isolated_file': 0.0,
                          'nr_kernel_misc_reclaimable': 0.0,
                          'nr_mapped': 0.0,
                          'nr_promote_fail': 0.0,
                          'nr_promote_isolate_fail': 0.0,
                          'nr_promote_ratelimit': 0.0,
                          'nr_promoted': 0.0,
                          'nr_shmem': 0.0,
                          'nr_shmem_hugepages': 0.0,
                          'nr_shmem_pmdmapped': 0.0,
                          'nr_slab_reclaimable': 0.0,
                          'nr_slab_unreclaimable': 284.0,
                          'nr_unevictable': 0.0,
                          'nr_unstable': 0.0,
                          'nr_vmscan_immediate_reclaim': 0.0,
                          'nr_vmscan_write': 0.0,
                          'nr_writeback': 0.0,
                          'nr_writeback_temp': 0.0,
                          'nr_written': 0.0,
                          'numa_try_migrate': 0.0,
                          'workingset_activate': 0.0,
                          'workingset_nodereclaim': 0.0,
                          'workingset_nodes': 0.0,
                          'workingset_refault': 0.0,
                          'workingset_restore': 0.0}
       }
 }
