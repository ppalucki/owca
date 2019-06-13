=============
Extending WCA
=============


Introduction
------------

WCA project contains simple built-in dependency injection framework. It allows 
to extend existing or add new functionality. To provide new functionality, operator of WCA, has to provide
new component defined as python class. This class has to be registered during itart time from
command line and then configured using the configuration file.

Actually all provided features are based on internal components and use the same mechanism for
initialization.

From high-level standpoint, main entry point to application is only responsible for
instantiation of python classes defined in yaml configuration, parse and prepare logging infrastructure
and then call generic `run` method on already created `Runner` class. `Runner` class is a main
vehicle integrating all other objects together.

In this document when referring to `component` it means a simple python class that was registered and
by this allowed to be used in configuration file.


For example, let's start w`MeasurementRunner` is a simple loop
using `Node` class as interface to discover locally running tasks, collect metrics for those tasks
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
  for metrics related od detected anomalies. It also requires component for

It is important to note, that configuration based objects are static singletons available
throughout whole application life.




Step by step instruction to provide external storage class
-----------------------------------------------------------

Different runners have 


