=============
Extending WCA
=============


Introduction
------------

WCA project contains simple built-in dependency injection framework. It allows 
to extend existing or add new functionality. 

This document contains example of adding new ``Storage`` component
to save metrics in external http based service, using ``requests`` and ``json`` library.

Overview
--------

To provide new functionality, operator of WCA, has to: 

- provide new component defined as python class, 
- this python class has to be registered upon starting with extra command line ``--register`` parameter as ``package_name.module_name:class name``) (package name is optional),
- component name is referenced in configuration file (using name of class),
- python module has to accessible by python interperter for import (``PYTHONPATH`` and ``PEX_INHERITPATH`` environment variables)


In this document when referring to `component`, it means a simple python class that was **registered** and by this allowed to be used in configuration file.


Built-in components
-------------------

All WCA features (detection/CMS integration) are based on internal components and use the same mechanism for initialization.

From high-level standpoint, main entry point to application is only responsible for
instantiation of python classes defined in yaml configuration, then parsing and preparing logging infrastructure and then call generic `run` method on already created `Runner` class.  `Runner` class is a main vehicle integrating all other objects together.

For example, ``MeasurementRunner`` is a simple loop
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

should ouput:

.. code-block: shell

    Hello world!








Step by step instruction to provide external storage class
-----------------------------------------------------------

Different runners have 


