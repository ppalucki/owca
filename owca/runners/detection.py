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
import logging
import time
from typing import Dict

from owca import nodes, storage, detectors, profiling
from owca.detectors import convert_anomalies_to_metrics, \
    update_anomalies_metrics_with_task_information
from owca.metrics import Metric, MetricType
from owca.runners.measurement import MeasurementRunner
from owca.storage import MetricPackage

log = logging.getLogger(__name__)


class AnomalyStatistics:

    def __init__(self):
        self._anomaly_last_occurrence = None
        self._anomaly_counter = 0

    def get_metrics(self, anomalies, detect_duration=None):
        """Extra external plugin anomaly statistics."""
        if len(anomalies):
            self._anomaly_last_occurrence = time.time()
            self._anomaly_counter += len(anomalies)

        statistics_metrics = [
            Metric(name='anomaly_count', type=MetricType.COUNTER, value=self._anomaly_counter),
        ]
        if self._anomaly_last_occurrence:
            statistics_metrics.extend([
                Metric(name='anomaly_last_occurrence', type=MetricType.COUNTER,
                       value=self._anomaly_last_occurrence),
            ])
        if detect_duration is not None:
            statistics_metrics.extend([
                Metric(name='detect_duration', type=MetricType.GAUGE, value=detect_duration)
            ])
        return statistics_metrics


class DetectionRunner(MeasurementRunner):
    """Watch over tasks running on this cluster on this _node, collect observation
    and report externally (using storage) detected anomalies.
    """

    def __init__(
            self,
            node: nodes.Node,
            detector: detectors.AnomalyDetector,
            metrics_storage: storage.Storage,
            anomalies_storage: storage.Storage,
            action_delay: float = 0.,  # [s]
            rdt_enabled: bool = True,
            extra_labels: Dict[str, str] = None,
            ignore_privileges_check: bool = False
    ):
        super().__init__(node, metrics_storage,
                         action_delay, rdt_enabled,
                         extra_labels, ignore_privileges_check)
        self._detector = detector

        # Anomaly.
        self._anomalies_storage = anomalies_storage
        self._anomalies_statistics = AnomalyStatistics()

    def _run_body(self, containers, platform, tasks_measurements,
                  tasks_resources, tasks_labels, common_labels):
        """Detector callback body."""

        detect_start = time.time()
        anomalies, extra_metrics = self._detector.detect(
            platform, tasks_measurements, tasks_resources, tasks_labels)
        detect_duration = time.time() - detect_start
        profiling.register_duration('detect', detect_duration)
        log.debug('Anomalies detected (in %.2fs): %d', detect_duration, len(anomalies))

        # Prepare anomaly metrics
        anomaly_metrics = convert_anomalies_to_metrics(anomalies, tasks_labels)
        update_anomalies_metrics_with_task_information(anomaly_metrics, tasks_labels)

        # Prepare and send all output (anomalies) metrics.
        anomalies_package = MetricPackage(self._anomalies_storage)
        anomalies_package.add_metrics(
            anomaly_metrics,
            extra_metrics,
            self._anomalies_statistics.get_metrics(anomalies)
        )
        anomalies_package.send(common_labels)
