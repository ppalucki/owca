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
# limitations under the License
from wca.scheduler.kubeapi import Kubeapi
from wca.scheduler.server import Server
from wca.scheduler.algorithms.fit import Fit
from wca.scheduler.data_providers.cluster_data_provider import ClusterDataProvider
from wca.prometheus import Prometheus
import base64

from unittest.mock import patch, MagicMock
import jsonpatch


kubeapi = MagicMock(spec=Kubeapi)
data_provider = ClusterDataProvider(prometheus=Prometheus('127.0.0.1', 1234), kubeapi=kubeapi)
algoritm = MagicMock(spec=Fit)
annotating_service = Server(configuration={'data_provider': data_provider,
                                           'algorithm': algoritm,
                                           'kubeapi': kubeapi})


@patch('wca.scheduler.data_providers.cluster_data_provider.'
       'ClusterDataProvider.get_apps_requested_resources',
       return_value={"sysbench-memory-small": {'wss': 2, 'mem': 4}})
def test_mutate(requested_resources):
    request_json = {'request': {
                      'namespace': 'default',
                      'object': {
                         "apiVersion": "v1",
                         "kind": "Pod",
                         "metadata": {
                             "labels": {
                                 "app": "sysbench-memory-small",
                                 "workload": "sysbench-memory"}}}}}
    spec = request_json['request']['object']
    patched_spec = {"apiVersion": "v1",
                    "kind": "Pod",
                    "metadata": {
                        "labels": {
                            "app": "sysbench-memory-small",
                            "workload": "sysbench-memory"},
                        "annotations": {
                            "toptierlimit.cri-resource-manager.intel.com/pod": "{}G".format(2),
                            "cri-resource-manager.intel.com/memory-type": "dram,pmem"}}}
    patch = jsonpatch.JsonPatch.from_diff(spec, patched_spec)
    with annotating_service.app.test_request_context('mocked_request', json=request_json):
        output = annotating_service._mutate_pod()
        assert output.json == {
                "response": {
                    "allowed": True,
                    "status": {"message": 'Patching pod'},
                    "patch": base64.b64encode(str(patch).encode()).decode(),
                    "patchtype": "JSONPatch",
                }
            }
