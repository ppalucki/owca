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
import base64
import copy
from enum import Enum
import jsonpatch
import logging
import time
import threading
from typing import Dict, List, Optional

from dataclasses import asdict
from flask import Flask, request, jsonify

from wca.config import Numeric
from wca.metrics import Metric, MetricType
from wca.scheduler.algorithms import Algorithm, RescheduleResult
from wca.scheduler.data_providers import DataProvider
from wca.scheduler.kubeapi import Kubeapi
from wca.scheduler.metrics import MetricName
from wca.scheduler.types import ExtenderArgs, ExtenderFilterResult, ResourceType

log = logging.getLogger(__name__)

DEFAULT_NAMESPACE = 'default'
DEFAULT_METRIC_LABELS = {}
KUBEAPI_DELETE_POD_QUERY = '/api/v1/namespaces/%s/pods/%s'


class MemoryType(str, Enum):
    DRAM = 'dram'
    HMEM = 'dram,pmem'


class Server:

    def reschedule_once(self):
        # Decide which tasks should be rescheduled.
        reschedule_result: RescheduleResult = self.algorithm.reschedule()

        if len(reschedule_result) > 0:
            log.info('[Rescheduling] %r', reschedule_result)

            # Delete them.
            for task in reschedule_result:
                self.kubeapi.delete(KUBEAPI_DELETE_POD_QUERY % (DEFAULT_NAMESPACE, task))

        return jsonify(True)

    def reschedule_interval(self, interval: Numeric(0, 60)):
        while True:
            self.reschedule()
            time.sleep(interval)

    @staticmethod
    def _create_patch(spec, modified_spec, message='Patching pod'):
        patch = jsonpatch.JsonPatch.from_diff(spec, modified_spec)
        return jsonify(
            {
                "response": {
                    "allowed": True,
                    "status": {"message": message},
                    "patch": base64.b64encode(str(patch).encode()).decode(),
                    "patchtype": "JSONPatch",
                }
            }
        )

    def _get_memory_type(self, wss: str, rss: str):
        rss = float(rss)
        if not rss:
            return MemoryType.HMEM
        ratio = float(wss) / rss * 100
        if ratio > self.dram_only_threshold:
            memory_type = MemoryType.DRAM
        else:
            memory_type = MemoryType.HMEM
        return memory_type

    def _mutate_pod(self):
        annotations_key = "annotations"
        spec = request.json["request"]["object"]
        modified_spec = copy.deepcopy(spec)
        annotations = {}

        log.debug("[_mutate_pod] modified_spec={}".format(modified_spec))
        log.debug("[_mutate_pod] request={}".format(request.json["request"]))

        if request.json["request"]["namespace"] not in self.monitored_namespaces:
            return self._create_patch(spec, modified_spec)

        app_name: str = modified_spec["metadata"]["labels"]["app"]
        requested_resources = self.data_provider.get_apps_requested_resources(
            [ResourceType.WSS, ResourceType.MEM])
        wss: Optional[str] = str(requested_resources[app_name][ResourceType.WSS])
        rss: Optional[str] = str(requested_resources[app_name][ResourceType.MEM])

        if wss is not None:
            if self.if_toptier_limit:
                annotations.update({'toptierlimit.cri-resource-manager.intel.com/pod':
                                    '{}G'.format(wss)})

        if wss is not None and rss is not None:
            memory_type = self._get_memory_type(wss, rss)
            annotations.update({'cri-resource-manager.intel.com/memory-type': memory_type})

            if memory_type == MemoryType.HMEM and self.cold_start_duration is not None:
                annotations.update({'cri-resource-manager.intel.com/cold-start':
                                   {'duration': self.cold_start_duration}})

        if not modified_spec["metadata"].get(annotations_key) and annotations:
            modified_spec["metadata"].update({annotations_key: {}})
        if annotations:
            modified_spec["metadata"][annotations_key].update(annotations)

        return self._create_patch(spec, modified_spec)

    def __init__(self, configuration: Dict[str, str]):
        """
        self.dram_only_threshold - set to 100.0, to not use this functionality, otherwise it can
            be decided that despite having wss/rss < 100% all memory will be allocated on DRAM.
        self.cold_start_duration - whether to start the workload on PMEM memory, if memory type
            for workload is DRAM,PMEM, duration of that period if set
        self.if_toptier_limit - whether to add toptier_limit annotation
        """
        self.app = Flask('k8s scheduler extender')
        self.algorithm: Algorithm = configuration.get('algorithm')
        self.kubeapi: Kubeapi = configuration.get('kubeapi')
        self.data_provider: DataProvider = configuration.get('data_provider')
        self.dram_only_threshold: float = configuration.get('dram_threshold', 100.0)
        self.cold_start_duration: Optional[int] = None
        self.if_toptier_limit: bool = True

        self.monitored_namespaces: List[str] = \
            configuration.get('monitored_namespaces', ['default'])

        reschedule_interval = configuration.get('reschedule_interval')

        if reschedule_interval:
            reschedule_thread = threading.Thread(
                    target=self.reschedule_interval,
                    args=[reschedule_interval])
            reschedule_thread.start()

        @self.app.route('/reschedule')
        def reschedule():
            return self.reschedule_once()

        @self.app.route('/status')
        def status():
            return jsonify(True)

        @self.app.route('/metrics')
        def metrics():
            metrics_registry = self.algorithm.get_metrics_registry()
            if metrics_registry:
                return metrics_registry.prometheus_exposition()
            else:
                return ''

        @self.app.route('/filter', methods=['POST'])
        def filter():
            extender_args = ExtenderArgs(**request.get_json())
            pod_namespace = extender_args.Pod['metadata']['namespace']
            pod_name = extender_args.Pod['metadata']['name']

            log.debug('[Filter] %r ' % extender_args)
            metrics_registry = self.algorithm.get_metrics_registry()

            if DEFAULT_NAMESPACE == pod_namespace:
                log.info('[Filter] Trying to filter nodes for Pod %r' % pod_name)

                result = self.algorithm.filter(extender_args)

                log.info('[Filter] Result: %r' % result)

                if metrics_registry:
                    metrics_registry.add(Metric(
                        name=MetricName.FILTER,
                        value=1,
                        labels=DEFAULT_METRIC_LABELS,
                        type=MetricType.COUNTER))

                return jsonify(asdict(result))
            else:
                log.info('[Filter] Ignoring Pod %r : Different namespace!' %
                         pod_name)

                if metrics_registry:
                    metrics_registry.add(Metric(
                        name=MetricName.POD_IGNORE_FILTER,
                        value=1,
                        labels=DEFAULT_METRIC_LABELS,
                        type=MetricType.COUNTER))

                return jsonify(ExtenderFilterResult(NodeNames=extender_args.NodeNames))

        @self.app.route('/prioritize', methods=['POST'])
        def prioritize():
            extender_args = ExtenderArgs(**request.get_json())
            pod_namespace = extender_args.Pod['metadata']['namespace']
            pod_name = extender_args.Pod['metadata']['name']

            metrics_registry = self.algorithm.get_metrics_registry()
            log.debug('[Prioritize-server] %r ' % extender_args)

            if DEFAULT_NAMESPACE == pod_namespace:
                log.info('[Prioritize-server] Trying to prioritize nodes for Pod %r' % pod_name)

                result = self.algorithm.prioritize(extender_args)

                priorities = [asdict(host)
                              for host in result]

                log.info('[Prioritize-server] Result: %r ' % priorities)

                if metrics_registry:
                    metrics_registry.add(Metric(
                        name=MetricName.PRIORITIZE,
                        value=1,
                        labels=DEFAULT_METRIC_LABELS,
                        type=MetricType.COUNTER))

                return jsonify(priorities)
            else:
                log.info('[Prioritize-server] Ignoring Pod %r : Different namespace!' %
                         pod_name)

                if metrics_registry:
                    metrics_registry.add(Metric(
                        name=MetricName.POD_IGNORE_PRIORITIZE,
                        value=1,
                        labels=DEFAULT_METRIC_LABELS,
                        type=MetricType.COUNTER))

                return jsonify([])

        @self.app.route("/mutate", methods=["POST"])
        def mutate():
            return self._mutate_pod()
