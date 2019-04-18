=================
Prometheus 
=================

**This software is pre-production and should not be deployed to production servers.**

Intro
========================


The agent by default encodes metrics to `Prometheus text based exposition format <https://github.com/prometheus/docs/blob/master/content/docs/instrumenting/exposition_formats.md>`_.

Thanks to this it is easy to store metrics in Prometheus using `LogStorage` component and `node_exporter textfile collector <https://github.com/prometheus/node_exporter#textfile-collector>`_.


A simple usage scenario
=======================


.. code-block:: yaml
    
    # Content of configs/extra/static_measurements_for_node_exporter.yaml
    runner: !MeasurementRunner
      node: !StaticNode
        tasks:
          - task1
      metrics_storage: !LogStorage
        output_filename: 'metrics.prom'
        overwrite: true


Run owca with below provided command:

.. code-block:: shell

    sudo ./dist/owca.pex --root -c configs/extra/static_measurements_for_node_exporter.yaml


Then run node_exporter:

.. code-block:: shell
    
    sudo node_exporter --collector.textfile.directory=$PWD


The metrics will be available at: http://127.0.0.1:9100/metrics


Example output::

    # HELP owca_tasks Metric read from metrics.prom
    # TYPE owca_tasks gauge
    owca_tasks{cores="4",cpus="8",host="gklab-126-081",owca_version="0.4.dev12+gb86e6ac",sockets="1"} 1
    # HELP owca_up Metric read from metrics.prom
    # TYPE owca_up counter
    owca_up{cores="4",cpus="8",host="gklab-126-081",owca_version="0.4.dev12+gb86e6ac",sockets="1"} 1.555587486599824e+09


You can scrape metrics with Promethues with a configuration file:

.. code-block:: yaml

    scrape_configs:
      - job_name: local
        scrape_interval: 1s
        static_configs:
          - targets:
            - 127.0.0.1:9100
