from unittest.mock import MagicMock, Mock

import pytest

from tests.testing import create_json_fixture_mock
from wca.scheduler.data_providers.cluster_data_provider import (
        ClusterDataProvider, MissingBasicResources, Kubeapi, Prometheus,
        Queries, GatheringWSSwithoutMemoryBandwidth)
from wca.scheduler.types import ResourceType


def get_mocked_cluster_data_provider():
    mocked_kubeapi = MagicMock(spec=Kubeapi)
    mocked_kubeapi.request_kubeapi.side_effect = request_kubeapi_side_effect
    mocked_kubeapi.monitored_namespaces = ['default']

    mocked_prometheus = Mock(spec=Prometheus)
    mocked_prometheus.do_query.side_effect = do_query_side_effect
    mocked_prometheus.queries = Queries()

    cluster_dp = ClusterDataProvider(kubeapi=mocked_kubeapi, prometheus=mocked_prometheus)

    return cluster_dp


def request_kubeapi_side_effect(*args, **kwargs):
    if args[0] == '/api/v1/nodes':
        return create_json_fixture_mock('kubeapi_nodes').json()
    elif args[0] == '/api/v1/namespaces/default/pods':
        return create_json_fixture_mock('kubeapi_default_ns_pods').json()


def do_query_side_effect(*args, **kwargs):
    if args[0] == Prometheus.queries.NODES_PMM_MEMORY_MODE:
        return create_json_fixture_mock('prometheus_nodes_pmm_memory_mode').json()['data']['result']
    elif args[0] == Prometheus.queries.MEMBW_CAPACITY_READ:
        return create_json_fixture_mock('prometheus_membw_capacity_read').json()['data']['result']
    elif args[0] == Prometheus.queries.MEMBW_CAPACITY_WRITE:
        return create_json_fixture_mock('prometheus_membw_capacity_write').json()['data']['result']
    elif args[0] == Prometheus.queries.NODE_CAPACITY_MEM_WSS:
        return create_json_fixture_mock('prometheus_node_capacity_mem_wss').json()['data']['result']
    elif args[0] == Prometheus.queries.NODE_CAPACITY_DRAM_MEMBW:
        return create_json_fixture_mock(
                'prometheus_node_capacity_dram_membw').json()['data']['result']
    elif args[0] == Prometheus.queries.APP_REQUESTED_RESOURCES_QUERY_MAP[ResourceType.CPU]:
        return create_json_fixture_mock(
                'prometheus_app_requested_cpu').json()['data']['result']
    elif args[0] == Prometheus.queries.APP_REQUESTED_RESOURCES_QUERY_MAP[ResourceType.MEM]:
        return create_json_fixture_mock(
                'prometheus_app_requested_mem').json()['data']['result']
    elif args[0] == Prometheus.queries.APP_REQUESTED_RESOURCES_QUERY_MAP[ResourceType.MEMBW_READ]:
        return create_json_fixture_mock(
                'prometheus_app_requested_membw_read').json()['data']['result']
    elif args[0] == Prometheus.queries.APP_REQUESTED_RESOURCES_QUERY_MAP[ResourceType.MEMBW_WRITE]:
        return create_json_fixture_mock(
                'prometheus_app_requested_membw_write').json()['data']['result']
    elif args[0] == Prometheus.queries.APP_REQUESTED_RESOURCES_QUERY_MAP[ResourceType.WSS]:
        return create_json_fixture_mock(
                'prometheus_app_requested_wss').json()['data']['result']


@pytest.mark.parametrize('resources', [
    [],
    [ResourceType.CPU],
    [ResourceType.MEM],
    [ResourceType.MEMBW_READ, ResourceType.MEMBW_WRITE]])
def test_get_nodes_capacities_raise_exception_no_cpu_or_mem(resources):
    cluster_dp = get_mocked_cluster_data_provider()

    with pytest.raises(MissingBasicResources):
        cluster_dp.get_nodes_capacities(resources)


@pytest.mark.parametrize('resources', [
    [ResourceType.CPU, ResourceType.MEM, ResourceType.WSS],
    [ResourceType.CPU, ResourceType.MEM, ResourceType.WSS, ResourceType.MEMBW_READ],
    [ResourceType.CPU, ResourceType.MEM, ResourceType.WSS, ResourceType.MEMBW_WRITE],
    ])
def test_get_nodes_capacities_raise_exception_wss_without_mb(resources):
    cluster_dp = get_mocked_cluster_data_provider()

    with pytest.raises(GatheringWSSwithoutMemoryBandwidth):
        cluster_dp.get_nodes_capacities(resources)


CLUSTER_CPU_MEM_CAPACITIES = {
        'node200': {'cpu': 48.0, 'mem': 201},
        'node201': {'cpu': 48.0, 'mem': 201},
        'node202': {'cpu': 48.0, 'mem': 201},
        'node203': {'cpu': 48.0, 'mem': 201},
        'node36': {'cpu': 72.0, 'mem': 404},  # k8s master node
        'node37': {'cpu': 40.0, 'mem': 1064},
        'node38': {'cpu': 40.0, 'mem': 404},
        'node39': {'cpu': 40.0, 'mem': 404},
        'node40': {'cpu': 40.0, 'mem': 1065}
}

CLUSTER_MEMBW_CAPACITIES = {
        'node200': {'membw_read': 255999960000, 'membw_write': 255999960000},
        'node201': {'membw_read': 255999960000, 'membw_write': 255999960000},
        'node202': {'membw_read': 255999960000, 'membw_write': 255999960000},
        'node203': {'membw_read': 255999960000, 'membw_write': 255999960000},
        'node37': {'membw_read': 54400000000, 'membw_write': 14800000000},
        'node38': {'membw_read': 255999960000, 'membw_write': 255999960000},
        'node39': {'membw_read': 255999960000, 'membw_write': 255999960000},
        'node40': {'membw_read': 33200000000, 'membw_write': 12000000000}
}

CLUSTER_CAPACITIES = {}

for node in CLUSTER_CPU_MEM_CAPACITIES:
    if node in CLUSTER_MEMBW_CAPACITIES:
        CLUSTER_CAPACITIES[node] = {
                **CLUSTER_CPU_MEM_CAPACITIES[node],
                **CLUSTER_MEMBW_CAPACITIES[node]}
    else:
        CLUSTER_CAPACITIES[node] = CLUSTER_CPU_MEM_CAPACITIES[node]


@pytest.mark.parametrize('resources, nodes_capacities', [
    ([ResourceType.CPU, ResourceType.MEM], CLUSTER_CPU_MEM_CAPACITIES),
    ([ResourceType.CPU, ResourceType.MEM, ResourceType.MEMBW_READ,
        ResourceType.MEMBW_WRITE], CLUSTER_CAPACITIES),
    ])
def test_get_nodes_capacities(resources, nodes_capacities):
    cluster_dp = get_mocked_cluster_data_provider()
    assert nodes_capacities == cluster_dp.get_nodes_capacities(resources)


CLUSTER_APP_COUNT = (
        {'node200': {'memcached-mutilate-big-wss': 1},
         'node201': {'memcached-mutilate-big-wss': 1},
         'node202': {'memcached-mutilate-big-wss': 1},
         'node203': {'memcached-mutilate-big-wss': 1},
         'node36': {},
         'node37': {},
         'node38': {},
         'node39': {'memcached-mutilate-big-wss': 1},
         'node40': {'memcached-mutilate-big-wss': 1}},
        {'memcached-mutilate-big-wss': 2})


@pytest.mark.parametrize('apps_count', [
    (CLUSTER_APP_COUNT),
    ])
def test_get_apps_counts(apps_count):
    cluster_dp = get_mocked_cluster_data_provider()
    assert apps_count == cluster_dp.get_apps_counts()


APP_REQUESTED_CPU_MEM = {
     'memcached-mutilate-big-wss': {'cpu': 10, 'mem': 91000000000},
     'memcached-mutilate-medium': {'cpu': 10, 'mem': 51000000000},
     'redis-memtier-big': {'cpu': 3, 'mem': 70000000000},
     'redis-memtier-big-wss': {'cpu': 3, 'mem': 75000000000},
     'redis-memtier-medium': {'cpu': 3, 'mem': 11000000000},
     'redis-memtier-small': {'cpu': 3, 'mem': 10000000000},
     'specjbb-preset-medium': {'cpu': 9, 'mem': 26000000000},
     'sysbench-memory-big': {'cpu': 4, 'mem': 10000000000},
     'sysbench-memory-medium': {'cpu': 3, 'mem': 4000000000},
     'sysbench-memory-small': {'cpu': 2, 'mem': 2000000000}
}


APP_REQUESTED_MEMBW = {
        'memcached-mutilate-big-wss': {'membw_read': 2622597731,
                                       'membw_write': 2805136872},
        'memcached-mutilate-medium': {'membw_read': 2839845719, 'membw_write': 2634252554},
        'redis-memtier-big': {'membw_read': 1627937868, 'membw_write': 1085064491},
        'redis-memtier-big-wss': {'membw_read': 1980646146, 'membw_write': 3163513620},
        'redis-memtier-medium': {'membw_read': 1591126817, 'membw_write': 1049019197},
        'redis-memtier-small': {'membw_read': 1393914170, 'membw_write': 1039516290},
        'specjbb-preset-medium': {'membw_read': 3411658124, 'membw_write': 1192782848},
        'sysbench-memory-big': {'membw_read': 115604853, 'membw_write': 14738247436},
        'sysbench-memory-medium': {'membw_read': 35819087, 'membw_write': 10940491266},
        'sysbench-memory-small': {'membw_read': 19041364, 'membw_write': 5890534725}
}

APP_REQUESTED_CPU_MEM_MEMBW = {app: {**APP_REQUESTED_CPU_MEM[app], **APP_REQUESTED_MEMBW[app]}
                               for app in APP_REQUESTED_CPU_MEM}

APP_REQUESTED_WSS = {
        'memcached-mutilate-big-wss': {'wss': 10686448000},
        'memcached-mutilate-medium': {'wss': 7230696000},
        'redis-memtier-big': {'wss': 3525264000},
        'redis-memtier-big-wss': {'wss': 4841892000},
        'redis-memtier-medium': {'wss': 2503720000},
        'redis-memtier-small': {'wss': 1967084000},
        'specjbb-preset-medium': {'wss': 12415120000},
        'sysbench-memory-big': {'wss': 8396076000},
        'sysbench-memory-medium': {'wss': 2104676000},
        'sysbench-memory-small': {'wss': 1056096000}
}

APP_REQUESTED_ALL_RESOURCES = {app: {**APP_REQUESTED_CPU_MEM_MEMBW[app], **APP_REQUESTED_WSS[app]}
                               for app in APP_REQUESTED_CPU_MEM}


@pytest.mark.parametrize('resource_types, resources', [
    ([ResourceType.CPU, ResourceType.MEM], APP_REQUESTED_CPU_MEM),
    ([ResourceType.MEMBW_READ, ResourceType.MEMBW_WRITE], APP_REQUESTED_MEMBW),
    ([ResourceType.CPU, ResourceType.MEM, ResourceType.MEMBW_READ, ResourceType.MEMBW_WRITE],
        APP_REQUESTED_CPU_MEM_MEMBW),
    ([ResourceType.WSS], APP_REQUESTED_WSS),
    ([ResourceType.CPU, ResourceType.MEM, ResourceType.MEMBW_READ, ResourceType.MEMBW_WRITE,
      ResourceType.WSS], APP_REQUESTED_ALL_RESOURCES),
    ])
def test_get_apps_requested_resources(resource_types, resources):
    cluster_dp = get_mocked_cluster_data_provider()
    assert resources == cluster_dp.get_apps_requested_resources(resource_types)
