=============
Extending WCA
=============

**This software is pre-production and should not be deployed to production servers.**

.. contents:: Table of Contents

Introduction
------------

WCA project contains simple built-in dependency injection framework that allows 
to extend existing or add new functionalities. 

This document contains examples:

- simple ``Runner`` that outputs "Hello World!",
- HTTP based ``Storage`` component to save metrics in external http based service, using ``requests`` and ``json`` library.

Overview
--------

To provide new functionality, operator of WCA, has to: 

- provide new component defined as **Python class**,
- this Python class has to be **registered** upon starting with extra command line ``--register`` parameter as ``package_name.module_name:class name``) (package name is optional),
- component name is **referenced** in configuration file (using name of class),
- Python module has to **accessible** by Python interpreter for import (``PYTHONPATH`` and ``PEX_INHERITPATH`` environment variables)

In this document when referring to **component**, it means a simple Python class that was **registered** and by this allowed to be used in configuration file.

Built-in components
-------------------

All WCA features (detection/CMS integration) are based on internal components and use the same mechanism for initialization.

From high-level standpoint, main entry point to application is only responsible for
instantiation of python classes defined in yaml configuration, then parsing and preparing logging infrastructure and then call generic ``run`` method on already created ``Runner`` class. 
``Runner`` class is a main vehicle integrating all other depended objects together.

For example, ``MeasurementRunner`` is a simple loop
that uses `Node` class as interface to discover locally running tasks, collect metrics for those tasks
and then use a `Storage` kind of component to store those metrics.

Using this configuration file config.yaml:

.. code-block:: yaml

    runner: !MeasurementRunner
        node: !MesosNode                # subclass of Node
        metric_storage: !LogStorage     # subclass of Storage
            output_filename: /tmp/logs.txt

effectively means running equivalent of python code:

.. code-block:: python

    runner = MeasurementRunner(
        node = MesosNode()
        metric_storage = LogStorage(
            output_filename = '/tmp/logs.txt'
        )
    )
    runner.run()



Example builtin runners:

- `MeasurementRunner` component requires single `Storage` component as a backend to store all
  generic metrics. Additionally `Node` subclass component is required,
- `DetectionRunner` component requires two `Storage` components. First for generic metrics and second
  for metrics related to detected anomalies. It also requires component for

It is important to note, that configuration based objects are static singletons available
throughout whole application life.

hello world
..................

Let's start with very basic thing and create ``HelloWorldRunner`` that just outputs 'Hello world!' string.

With python module ``hello_world_runner.py`` containing HelloWorldRunner:

.. code-block:: python

    from wca.runners import Runner

    class HelloWorldRunner(Runner):

        def run(self):
            print('Hello world!')


you need to start WCA with following `example config file <configs/hello_world/config.yaml>`_:

.. code-block:: yaml

    runner: !HelloWorldRunner


and then WCA run like this:

.. code-block:: shell

    PYTHONPATH=example PEX_INERHITPATH=1 ./dist/wca.pex -c $PWD/configs/hello_world/config.yaml -r hello_world_runner:HelloWorldRunner

should output:

.. code-block: shell

    Hello world!


Example: Integration with custom monitoring system
--------------------------------------------------

To integrate with custom monitoring system it is enough to provide definition of custom ``Storage`` class.
``Storage`` class is a simple interface that expose just one method ``store`` as defined below:

.. code-block:: python

    class Storage:

        def store(self, metrics: List[Metric]) -> None:
            """store metrics; may throw FailedDeliveryException"""
            ...

where `Metric <../wca/metrics.py#138>`_ is simple class with structure influenced by Prometheus and `OpenMetrics initiative <https://openmetrics.io/>`_ :

.. code-block:: python

    @dataclass
    class Metric:
        name: str
        value: float
        labels: Dict[str, str]
        type: str            # gauge/counter
        help: str


Example of HTTP based ``Storage`` class
........................................

This is simple ``Storage`` class that can be used to post metrics serialized as json to 
external http web service using post method:

.. code-block:: python

    import requests, json
    from dataclasses import dataclass
    from wca.storage import Storage
    import logging

    log = logging.getLogger(__name__)

    @dataclass
    class HTTPStorage(Storage):

        http_endpoint: str = 'http://127.0.0.1:8000'
        
        def store(self, metrics):
            log.info('sending!')
            try:
                requests.post(self.http_endpoint, json={metric.name: metric.value for metric in metrics}, timeout=1)
            except requests.exceptions.ReadTimeout:
                log.warning('timeout!')
                pass


then in can be used with ``MeasurementRunner`` with following configuration file `<../configs/extending/measurement_http_storage.yaml>`_:

.. code-block:: yaml

    runner: !MeasurementRunner
      node: !StaticNode
        tasks: []                   # this disables any tasks metrics
      metrics_storage: !HTTPStorage

To be able to verify that data was posted to http service correctly please start naive service
using ``socat``:

.. code-block:: shell

    socat - tcp4-listen:8000,fork

and then run WCA like this:

.. code-block:: shell

    sudo env PYTHONPATH=example PEX_INERHITPATH=1 ./dist/wca.pex -c $PWD/configs/extending/measurement_http_storage.yaml -r http_storage:HTTPStorage --root --log http_storage:info


Expected output is:

.. code-block:: shell

    # from WCA:
    2019-06-14 21:51:17,859 WARNING  {MainThread} [http_storage] timeout!
    2019-06-14 21:51:17,862 INFO     {MainThread} [http_storage] sending!

    # from socat:
    POST / HTTP/1.1
    Host: 127.0.0.1:8000
    User-Agent: python-requests/2.21.0
    Accept-Encoding: gzip, deflate
    Accept: */*
    Connection: keep-alive
    Content-Length: 240
    Content-Type: application/json

    {"wca_up": 1560541957.1652732, "wca_tasks": 0, "wca_memory_usage_bytes": 50159616, 
    "memory_usage": 1399689216, "cpu_usage_per_cpu": 1205557, 
    "wca_duration_seconds": 1.0013580322265625e-05, 
    "wca_duration_seconds_avg": 1.0013580322265625e-05}


Note:

- `sudo` is required to enable perf and resctrl based metrics,
- `--log` parameter allow to specify log level for custom components






Configuring Runners to use external ``Storage`` component
...........................................................


Depending on `Runner` component, different kinds of metrics are produced and send to different instances
of ``Storage`` components:

1. ``MeasurementRunner`` uses ``Storage`` instance under ``metrics_storage`` property to store:

   - platform level resources usage (CPU/memory usage) metrics,
   - internal WCA metrics: number of monitored tasks, number of errors/warnings, health-checks, WCA memory usage,
   - (per-task) perf system based metrics e.g. instructions, cycles
   - (per-task) Intel RDT based metrics e.g. cache usage, memory bandwidth
   - (per-task) cgroup based metrics e.g. CPU/memory usage 

   Each of those metrics has additional metadata attached (in form of labels) about:
   - platform topology (sockets/cores/cpus),
   - extra labels defined in WCA configuration file (e.g. own_ip),
   - (only per-task metrics) task id and name and metadata acquired from orchestration system (Mesos task/Kubernetes pod labels)

2. ``DetectionRunner`` uses ``Storage`` subclass instances:
    
   in ``metrics_storage`` property:
   - the same metrics as send to ``MeasurmentRunner``.``metrics_storage`` above,

   in ``anomalies_storage`` property:
   - number of anomalies detected by ``Allcocator`` class
   - individual instances of detected anomalies encoded as metrics (more details `here <detecion.rst#representation-of-anomaly-and-metrics-in-persistent-storage>`)

3. ``AllocationRunner`` uses ``Storage`` subclass instances:

   in ``metrics_storage`` property:
   - the same metrics as send to ``MeasurementRunner``.``metrics_storage`` above,

   in ``anomalies_storage`` property:
   - the same metrics as send to ``DetectionRunner``.``anomalies_storage`` above,

   in ``alloation_storage`` property:
   - number of resource allocations performed during last iteration,
   - details about performed allocations like: number of CPU shares or CPU quota or cache allocation,
   - more details `here <docs/allocation.rst#taskallocations-metrics>`



