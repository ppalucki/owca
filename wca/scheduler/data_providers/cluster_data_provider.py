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
import logging
import pathlib
import requests
import os

from collections import defaultdict
from dataclasses import dataclass, field
from urllib.parse import urljoin
from typing import Iterable, Dict, Optional, List, Tuple

from wca.config import Numeric, Str, Path
from wca.kubernetes import SERVICE_TOKEN_FILENAME, SERVICE_CERT_FILENAME
from wca.resources import _MEMORY_UNITS
from wca.scheduler.data_providers import DataProvider
from wca.scheduler.types import Resources, ResourceType, NodeName, AppName
from wca.security import SSL, HTTPSAdapter

log = logging.getLogger(__name__)

QUERY_PATH = "/api/v1/query"
URL_TPL = '{prometheus_ip}{path}?query={name}'


class PrometheusDataProviderException(Exception):
    pass


@dataclass
class Queries:
    NODES_PMM_MEMORY_MODE: str = 'sum(platform_mem_mode_size_bytes) by (nodename) != 0'
    MEMBW_CAPACITY_READ: str = 'sum(platform_nvdimm_read_bandwidth_bytes_per_second) by (nodename)'
    MEMBW_CAPACITY_WRITE: str =\
        'sum(platform_nvdimm_write_bandwidth_bytes_per_second) by (nodename)'

    NODE_CAPACITY_MEM_WSS: str =\
        'sum(platform_dimm_total_size_bytes{dimm_type="ram"}) by (nodename)'
    NODE_CAPACITY_DRAM_MEMBW: str = 'platform_dimm_speed_bytes_per_second'

    APP_REQUESTED_RESOURCES_QUERY_MAP: Dict[ResourceType, str] = field(default_factory=lambda: {
            ResourceType.CPU: 'max(max_over_time(task_requested_cpus[3h])) by (app)',
            ResourceType.MEM: 'max(max_over_time(task_requested_mem_bytes[3h])) by (app)',
            ResourceType.MEMBW_READ:
            'max(max_over_time(task_membw_reads_bytes_per_second[3h])) by (app)',
            ResourceType.MEMBW_WRITE:
            'max(max_over_time(task_membw_writes_bytes_per_second[3h])) by (app)',
            ResourceType.WSS: 'max(max_over_time(task_wss_referenced_bytes[3h])) by (app)',
    })


@dataclass
class Prometheus:
    host: str
    port: int
    timeout: Optional[Numeric(1, 60)] = 1.0
    ssl: Optional[SSL] = None
    queries: Optional[Queries] = Queries()
    time: Optional[str] = None

    def do_query(self, query: str):
        url = URL_TPL.format(
                prometheus_ip='{}:{}'.format(self.host, str(self.port)),
                path=QUERY_PATH,
                name=query)

        if self.time:
            url += '&time={}'.format(self.time)

        try:
            if self.ssl:
                s = requests.Session()
                s.mount(self.ip, HTTPSAdapter())
                response = s.get(
                        url,
                        timeout=self.timeout,
                        verify=self.ssl.server_verify,
                        cert=self.ssl.get_client_certs())
            else:
                response = requests.get(url, timeout=self.timeout)
                response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise PrometheusDataProviderException(e)

        return response.json()['data']['result']


@dataclass
class Kubeapi:
    host: Str = None
    port: Str = None  # Because !Env is String and another type cast might be problematic

    client_token_path: Optional[Path(absolute=True, mode=os.R_OK)] = SERVICE_TOKEN_FILENAME
    server_cert_ca_path: Optional[Path(absolute=True, mode=os.R_OK)] = SERVICE_CERT_FILENAME

    timeout: Numeric(1, 60) = 5  # [s]
    monitored_namespaces: List[Str] = field(default_factory=lambda: ["default"])

    def __post_init__(self):
        self.endpoint = "https://{}:{}".format(self.host, self.port)

        log.debug("Created kubeapi endpoint %s", self.endpoint)

        with pathlib.Path(self.client_token_path).open() as f:
            self.service_token = f.read()

    def request_kubeapi(self, target):

        full_url = urljoin(
                self.endpoint,
                target)

        r = requests.get(
                full_url,
                headers={
                    "Authorization": "Bearer {}".format(self.service_token),
                    },
                timeout=self.timeout,
                verify=self.server_cert_ca_path)

        if not r.ok:
            log.error('An unexpected error occurred for target "%s": %i %s - %s',
                      target, r.status_code, r.reason, r.raw)
        r.raise_for_status()

        return r.json()


def _convert_k8s_memory_capacity(memory: str) -> float:
    """ return as GB """
    # TODO: Consider if K8s return memory only in 'Ki' unit.
    assert memory.endswith('Ki')
    return int((float(int(memory[:-2]) * _MEMORY_UNITS['Ki'])) / 1e9)


class MissingBasicResources(Exception):
    pass


class GatheringWSSwithoutMemoryBandwidth(Exception):
    pass


@dataclass
class ClusterDataProvider(DataProvider):
    kubeapi: Kubeapi
    prometheus: Prometheus

    def get_nodes_capacities(self, resources: Iterable[ResourceType]) -> Dict[NodeName, Resources]:
        # Check if basic resources are needed. If not, something is wrong.
        if ResourceType.CPU not in resources or ResourceType.MEM not in resources:
            raise MissingBasicResources

        # CPU and Memory capacity source.
        kubeapi_nodes_data = list(self.kubeapi.request_kubeapi('/api/v1/nodes')['items'])

        # Get nodes names and basic resources.
        node_capacities = {
                node['metadata']['name']: {
                    ResourceType.CPU: float(node['status']['capacity']['cpu']),
                    ResourceType.MEM: _convert_k8s_memory_capacity(
                        node['status']['capacity']['memory']),
                    }
                for node in kubeapi_nodes_data
        }

        if ResourceType.MEMBW_READ in resources and ResourceType.MEMBW_WRITE in resources:

            def fill_nodes_capacity_from_query(
                    nodes: List[NodeName], resources: List[ResourceType], query: str):
                query_result = self.prometheus.do_query(query)
                for row in query_result:
                    node = row['metric']['nodename']
                    if node in nodes:
                        value = float(row['value'][1])
                        for resource in resources:
                            node_capacities[node][resource] = int(value)
                    else:
                        continue

            # Check which nodes have PMem (Memory Mode).
            query_result = self.prometheus.do_query(self.prometheus.queries.NODES_PMM_MEMORY_MODE)
            nodes_with_pmm = []
            for row in query_result:
                nodes_with_pmm.append(row['metric']['nodename'])

            # Every other node should be DRAM only.
            nodes_with_dram = list(node_capacities.keys() - nodes_with_pmm)

            # Read Memory Bandwidth from PMem nodes.
            if len(nodes_with_pmm) > 0:
                fill_nodes_capacity_from_query(
                        nodes_with_pmm, [ResourceType.MEMBW_READ],
                        self.prometheus.queries.MEMBW_CAPACITY_READ)

                fill_nodes_capacity_from_query(
                        nodes_with_pmm, [ResourceType.MEMBW_WRITE],
                        self.prometheus.queries.MEMBW_CAPACITY_WRITE)

                if ResourceType.WSS in resources:
                    fill_nodes_capacity_from_query(
                            nodes_with_pmm, [ResourceType.WSS],
                            self.prometheus.queries.NODE_CAPACITY_MEM_WSS)

            # Read Memory Bandwidth from PMem nodes.
            if len(nodes_with_dram) > 0:
                fill_nodes_capacity_from_query(
                        nodes_with_dram,
                        [ResourceType.MEMBW_READ, ResourceType.MEMBW_WRITE],
                        self.prometheus.queries.NODE_CAPACITY_DRAM_MEMBW)

                if ResourceType.WSS in resources:
                    for node in nodes_with_dram:
                        node_capacities[node][ResourceType.WSS] =\
                                node_capacities[node][ResourceType.MEM]

        elif ResourceType.WSS in resources:
            raise GatheringWSSwithoutMemoryBandwidth(
                    'Cannot calculate WSS without MEMBW READS and WRITES!')

        log.debug('Node capacities: %r' % node_capacities)

        return node_capacities

    def get_apps_counts(self) \
            -> Tuple[Dict[NodeName, Dict[AppName, int]], Dict[AppName, int]]:

        unassigned_apps = defaultdict(int)

        nodes_data = list(self.kubeapi.request_kubeapi('/api/v1/nodes')['items'])
        node_names = [node['metadata']['name']for node in nodes_data]

        assigned_apps = {}
        for node_name in node_names:
            assigned_apps[node_name] = defaultdict(int)

        for namespace in self.kubeapi.monitored_namespaces:
            pods_data = list(self.kubeapi.request_kubeapi(
                '/api/v1/namespaces/{}/pods'.format(namespace))['items'])

            for pod in pods_data:
                name = pod['metadata']['name']
                app = pod['metadata']['labels'].get('app')

                if not app:
                    log.warning('Unknown app label for pod %r' % name)
                    continue

                node = pod['spec'].get('nodeName')
                host_ip = pod['status'].get('hostIP')

                # Check if Pod is assigned.
                if not (node and host_ip):
                    unassigned_apps[app] += 1
                else:
                    assigned_apps[node][app] += 1

        # remove default dicts
        assigned_apps = {k: dict(v) for k, v in assigned_apps.items()}
        log.debug('Assigned apps: %r' % assigned_apps)
        log.debug('Unassigned apps: %r' % unassigned_apps)

        return assigned_apps, dict(unassigned_apps)

    def get_apps_requested_resources(self, resources: Iterable[ResourceType]) \
            -> Dict[AppName, Resources]:

        app_requested_resources = defaultdict(lambda: defaultdict(float))

        for resource in resources:
            query_result = self.prometheus.do_query(
                    self.prometheus.queries.APP_REQUESTED_RESOURCES_QUERY_MAP[resource])
            for result in query_result:
                app = result['metric'].get('app')
                value = float(result['value'][1])
                if app:
                    app_requested_resources[app][resource] = int(value)

        app_requested_resources = {k: dict(v) for k, v in app_requested_resources.items()}
        log.debug('Resources requested by apps: %r' % app_requested_resources)

        return app_requested_resources
