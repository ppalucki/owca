# Copyright (C) 2020 Intel Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions
# and limitations under the License.
#
#
# SPDX-License-Identifier: Apache-2.0

import os
import requests
from datetime import datetime, timedelta
import csv
from pytest import mark

CADVISOR_TIMESTAMP_FORMAT = "%Y-%m-%dT%H:%M:%S.%f"
EXPECTED_PERF_METRICS = {
    "cycles": "cycles",
    "instructions": "instructions",
    "instructions_retired": "cpu/config=0x5300c0/",
}
EXPECTED_UNCORE_METRICS = {
    "uncore_imc_0/cas_count_write": "uncore_imc_0/config=0xc04/",
    "uncore_imc_0/UNC_M_CAS_COUNT:RD": "uncore_imc_0/cas_count_read/",
}
ERROR_TOLERATION = 0.3


@mark.parametrize("metric", EXPECTED_PERF_METRICS.keys())
def test_core_perf(metric):
    cadvisor_port = os.environ.get("CADVISOR_PORT")
    with open("pmbench_container_id.txt") as f:
        cgroup = f.read().strip("\n")
    with open("perf_ending_timestamp.txt") as f:
        end_timestamp = f.read().strip("\n")
    end_date = datetime.fromtimestamp(int(end_timestamp))
    resp = requests.get(
        f"http://127.0.0.1:{cadvisor_port}/api/v1.3/subcontainers"
    ).json()
    for container in resp:
        if container["name"] == f"/docker/{cgroup}":
            container_stats = container["stats"]
            break
    container_stats.reverse()
    assert container_stats
    for i, stats in enumerate(container_stats):
        cadvisor_date = datetime.strptime(
            stats["timestamp"][:-4], CADVISOR_TIMESTAMP_FORMAT
        )
        # we look for the closest timestamp after timestamp gotten from env
        if cadvisor_date - end_date < timedelta(0):
            selected_stats_index = i
            break
    if (
        abs(
            datetime.strptime(
                container_stats[selected_stats_index]["timestamp"][:-4],
                CADVISOR_TIMESTAMP_FORMAT,
            )
            - end_date
        ).total_seconds()
    ) < (
        abs(
            datetime.strptime(
                container_stats[selected_stats_index - 1]["timestamp"][:-4],
                CADVISOR_TIMESTAMP_FORMAT,
            )
            - end_date
        ).total_seconds()
    ):
        stats = container_stats[selected_stats_index]
    else:
        stats = container_stats[selected_stats_index - 1]
    assert stats
    perf_output = parse_perf_output("core.csv", 8)
    print(perf_output)
    cadvisor_perf_value = sum(
        [float(stat["value"]) for stat in stats["perf_stats"] if stat["name"] == metric]
    )
    perf_value = float(perf_output[EXPECTED_PERF_METRICS[metric]])
    assert (
        perf_value * (1 - ERROR_TOLERATION)
        < cadvisor_perf_value
        < perf_value * (1 + ERROR_TOLERATION)
    )


@mark.parametrize("metric", EXPECTED_UNCORE_METRICS.keys())
def test_uncore_perf(metric):
    cadvisor_port = os.environ.get("CADVISOR_PORT")
    with open("perf_ending_timestamp.txt") as f:
        end_timestamp = f.read().strip("\n")
    end_date = datetime.fromtimestamp(int(end_timestamp))
    resp = requests.get(f"http://127.0.0.1:{cadvisor_port}/api/v1.3/containers").json()
    container_stats = resp["stats"]
    container_stats.reverse()
    assert container_stats
    for i, stats in enumerate(container_stats):
        cadvisor_date = datetime.strptime(
            stats["timestamp"][:-4], CADVISOR_TIMESTAMP_FORMAT
        )
        # we look for the closest timestamp after timestamp gotten from env
        if cadvisor_date - end_date < timedelta(0):
            selected_stats_index = i
            break
    if (
        abs(
            datetime.strptime(
                container_stats[selected_stats_index]["timestamp"][:-4],
                CADVISOR_TIMESTAMP_FORMAT,
            )
            - end_date
        ).total_seconds()
    ) < (
        abs(
            datetime.strptime(
                container_stats[selected_stats_index - 1]["timestamp"][:-4],
                CADVISOR_TIMESTAMP_FORMAT,
            )
            - end_date
        ).total_seconds()
    ):
        stats = container_stats[selected_stats_index]
    else:
        stats = container_stats[selected_stats_index - 1]
    assert stats
    perf_output = parse_perf_output("uncore.csv", 7)
    print(perf_output)
    cadvisor_perf_value = sum(
        [
            float(stat["value"])
            for stat in stats["perf_uncore_stats"]
            if stat["name"] == metric.split("/")[1]
            and stat["pmu"] == metric.split("/")[0]
        ]
    )
    # corner case: perf stat might report value multiplied by 64
    if metric == "uncore_imc_0/UNC_M_CAS_COUNT:RD":
        cadvisor_perf_value *= 64

    perf_value = float(perf_output[EXPECTED_UNCORE_METRICS[metric]])
    print(perf_output)
    assert (
        perf_value * (1 - ERROR_TOLERATION)
        < cadvisor_perf_value
        < perf_value * (1 + ERROR_TOLERATION)
    )


def parse_perf_output(file: str, row_length: int) -> map:
    with open(file) as f:
        reader = csv.reader(f)
        stats = {}
        for row in reader:
            if len(row) != row_length:
                continue
            stats[row[2]] = parse_unit(float(row[0]), row[1])
    return stats


def parse_unit(value, unit):
    if not unit:
        return value
    elif unit == "KiB":
        return value * 1024
    elif unit == "MiB":
        return value * (1024 ** 2)
    elif unit == "GiB":
        return value * (1024 ** 3)
    elif unit == "TiB":
        return value * (1024 ** 4)
    else:
        raise ValueError(f"Unknkow unit {unit}")
