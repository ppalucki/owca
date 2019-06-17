=============
Extending WCA
=============

**This software is pre-production and should not be deployed to production servers.**

.. contents:: Table of Contents

Introduction
------------

WCA project contains simple built-in dependency injection framework that allows 
to extend existing or add new functionalities. 

This document contains examples of:

- simple ``Runner`` that outputs ``"Hello World!"``,
- HTTP based ``Storage`` component to save metrics in external http based service, using ``requests`` library.

Overview
--------

To provide new functionality using external compoent operator of WCA has to: 

- provide new component defined as **Python class**,
- **register** this Python class upon starting with extra command line ``--register`` parameter as ``package_name.module_name:class_name``) (package name is optional),
- **reference** component name in configuration file (using name of class),
- make Python module **accessible** by Python interpreter for import (``PYTHONPATH`` and ``PEX_INHERITPATH`` environment variables)

In this document when referring to **component**, it means a simple Python class that was **registered** and by this allowed to be used in configuration file.

Built-in components
-------------------

All WCA features (detection/CMS integration) are based on internal components and use the same mechanism for initialization.

From high-level standpoint, main entry point to application is only responsible for
instantiation of python classes defined in yaml configuration, then parsing and preparing logging infrastructure and then call generic ``run`` method on already created ``Runner`` instance. 
``Runner`` class is a main vehicle integrating all other depended objects together.

For example, ``MeasurementRunner`` is implements simple loop
that uses ``Node`` subclass (e.g. ``MesosNode``) instance to discover locally running tasks, then collects metrics for those tasks
and then uses a ``Storage`` subclass to store those metrics somewhere (e.g. ``KafkaStorage`` or ``LogStorage``).

To illustrate that, when someone uses WCA with configuration file like this:

.. code-block:: yaml

    runner: !MeasurementRunner
        node: !MesosNode                # subclass of Node
        metric_storage: !LogStorage     # subclass of Storage
            output_filename: /tmp/logs.txt

it effectively means running equivalent of Python code:

.. code-block:: python

    runner = MeasurementRunner(
        node = MesosNode()
        metric_storage = LogStorage(
            output_filename = '/tmp/logs.txt'
        )
    )
    runner.run()



For example, to provide measure-only mode, anomaly detection mode or resource allocation mode, WCA contains following components:

- ``MeasurementRunner`` that is only responsible for collecting metrics,
- ``DetectionRunner`` that extends ``MeasurementRunner`` to allow anomaly detection and generate additional metrics,
- ``AllocationRunner`` that allows to configure resources based on provided ``Allocator`` component instance,

It is important to note, that configuration based objects (components) are static singletons available
throughout whole application life and only accessible by parent objects.

Hello world ``Runner`` example.
................................

Let's start with very basic thing and create ``HelloWorldRunner`` that just outputs 'Hello world!' string.

With Python module ``hello_world_runner.py`` containing ``HelloWorldRunner`` subclass of ``Runner``:

.. code-block:: python

    from wca.runners import Runner

    class HelloWorldRunner(Runner):

        def run(self):
            print('Hello world!')


you need to start WCA with following `example config file <../configs/extending/hello_world.yaml>`_:

.. code-block:: yaml

    runner: !HelloWorldRunner


and then with WCA started like this 

.. code-block:: shell

    PYTHONPATH=example PEX_INERHITPATH=1 ./dist/wca.pex -c $PWD/configs/extending/hello_world.yaml -r hello_world_runner:HelloWorldRunner

:Tip: You can just copy-paste this command, all required example files are already in project, but you have to build pex file first with ``make``.

should output:

.. code-block:: shell

    Hello world!


Example: Integration with custom monitoring system
--------------------------------------------------

To integrate with custom monitoring system it is enough to provide definition of custom ``Storage`` class.
``Storage`` class is a simple interface that exposes just one method ``store`` as defined below:

.. code-block:: python

    class Storage:

        def store(self, metrics: List[Metric]) -> None:
            """store metrics; may throw FailedDeliveryException"""
            ...

where `Metric <../wca/metrics.py#L138>`_ is simple class with structure influenced by `Prometheus metric model <https://prometheus.io/docs/concepts/data_model/>`_
and `OpenMetrics initiative <https://openmetrics.io/>`_ :

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

(full source code  `here <../example/http_storage.py>`_)

.. code-block:: python

    import requests, json
    from dataclasses import dataclass
    from wca.storage import Storage

    @dataclass
    class HTTPStorage(Storage):

        http_endpoint: str = 'http://127.0.0.1:8000'
        
        def store(self, metrics):
            requests.post(
                self.http_endpoint, 
                json={metric.name: metric.value for metric in metrics}:w
            )


then in can be used with ``MeasurementRunner`` with following `configuration file <../configs/extending/measurement_http_storage.yaml>`_:

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

- **sudo** is required to enable perf and resctrl based metrics,
- **--log** parameter allow to specify log level for custom components


Configuring Runners to use external ``Storage`` component
...........................................................


Depending on ``Runner`` component, different kinds of metrics are produced and send to different instances of ``Storage`` components:

1. ``MeasurementRunner`` uses ``Storage`` instance under ``metrics_storage`` property to store:

   - platform level resources usage (CPU/memory usage) metrics,
   - internal WCA metrics: number of monitored tasks, number of errors/warnings, health-checks, WCA memory usage,
   - (per-task) perf system based metrics e.g. instructions, cycles
   - (per-task) Intel RDT based metrics e.g. cache usage, memory bandwidth
   - (per-task) cgroup based metrics e.g. CPU/memory usage 

   Each of those metrics has additional metadata attached (in form of labels) about:

   - platform topology (sockets/cores/cpus),
   - ``extra labels`` defined in WCA configuration file (e.g. own_ip),
   - labels to identify WCA version ``wca_version`` and host name (``host``) and host CPU model ``cpu_model``,
   - (only for per-task metrics) task id (``task_id``) and metadata acquired from orchestration system (Mesos task or Kubernetes pod labels)

2. ``DetectionRunner`` uses ``Storage`` subclass instances:
    
   in ``metrics_storage`` property:

   - the same metrics as send to ``MeasurmentRunner`` in ``metrics_storage`` above,

   in ``anomalies_storage`` property:

   - number of anomalies detected by ``Allcocator`` class
   - individual instances of detected anomalies encoded as metrics (more details `here <detection.rst#representation-of-anomaly-and-metrics-in-persistent-storage>`_)

3. ``AllocationRunner`` uses ``Storage`` subclass instances:

   in ``metrics_storage`` property:

   - the same metrics as send to ``MeasurementRunner`` in ``metrics_storage`` above,

   in ``anomalies_storage`` property:

   - the same metrics as send to ``DetectionRunner`` in ``anomalies_storage`` above,

   in ``alloation_storage`` property:

   - number of resource allocations performed during last iteration,
   - details about performed allocations like: number of CPU shares or CPU quota or cache allocation,
   - more details `here <docs/allocation.rst#taskallocations-metrics>`_

Note that it is possible by using `YAML anchors and aliases <https://yaml.org/refcard.html>`_ to configure that the same instance of ``Storage`` should be used to store all kinds of metrics:

.. code-block:: yaml

    runner: !AllocationRunner
      metrics_storage: &kafka_storage_instance !KafkaStorage
        topic: all_metrics
        broker_ips: 
        - 127.0.0.1:9092
        - 127.0.0.2:9092
        max_timeout_in_seconds: 5.
      anomalies_storage: *kafka_storage_instance
      allocations_storage: *kafka_storage_instance

This approach can help to save resources (like connections), share state or simplify configuration (no need to repeat the same arguments).
            

Bundling additional dependencies for external component.
--------------------------------------------------------

If component requires some additional dependencies and you do not want dirty
system interpreter library, the best way to bundle new component is to
use `PEX <https://github.com/pantsbuild/pex>`_ file to package all source code including dependencies.

(``requests`` library from previous example was available because it is already required by WCA itself).


.. code-block:: shell

    pex -D example/hello_world_runner_with_dateutil.py  python-dateutil==2.8.0 -o hello_world.pex -v


where ``example/hello_world_runner_with_dateutil.py``:

.. code-block:: python

    from wca.runners import Runner
    from dateutil.utils import today

    class HelloWorldRunner(Runner):

        def run(self):
            print('Hello world! Today is %s' % today())

then it is possible to combine two PEX files into single environment, by using
``PEX_PATH`` environment variable:

.. code-block:: shell

    PEX_PATH=hello_world.pex ./dist/wca.pex -c $PWD/configs/extending/hello_world.yaml -r hello_world_runner_with_dateutil:HelloWorldRunner


outputs:

.. code-block:: shell

    Hello world! Today is 2019-06-14 00:00:00

Note this method works great if there is no conflicting sub dependencies (Diamond dependency problem), because only one version will be available during runtime. 
In such case, you need to consolidate WCA and your component into single project (with common requirments) so that conflicts will be resolved during requirements gathering phase. 
You can check Platform Resource Manager `prm component <https://github.com/intel/platform-resource-manager/tree/master/prm>`_ as an example of such approach.


Officially support extensions points
-------------------------------------

Any children object that is used by any runner, can be replaced with extrnal component, but WCA was designed to be extended, by providing following components:

- ``Node`` class used by all ``Runners`` to perform task discovery,
- ``Storage`` classes used to enable persistance for internal metrics (``*_storage`` properties),
- ``Detector`` class to provide anomaly detection logic,
- ``Allocator`` class to provide anomaly detection and anomaly mittigation logic (by resource allocation),




