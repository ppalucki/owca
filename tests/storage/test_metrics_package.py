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


from unittest.mock import Mock

from owca.storage import MetricPackage, Storage
from owca.metrics import Metric


def test_metrics_package():
    m1 = Metric(name='average_latency_miliseconds', value=8)
    storage = Mock(spec=Storage)
    mp = MetricPackage(storage)
    mp.add_metrics([m1])
    mp.send(dict(foo='label_val'))
    assert storage.store.call_count == 1
    storage.store.assert_called_once_with(
        [Metric(name='average_latency_miliseconds', value=8,
                labels={'foo': 'label_val'}, type=None, help=None)]
    )
