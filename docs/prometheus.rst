=================
Prometheus 
=================

**This software is pre-production and should not be deployed to production servers.**

Intro
========================


Agent by default encodes metrics to `Prometheus text based exposition format <https://github.com/prometheus/docs/blob/master/content/docs/instrumenting/exposition_formats.md>`_.

Thanks to this it is easy to store those this metrics in Prometheus using `LogStorage` component and `node_exporter textfile collector <https://github.com/prometheus/node_exporter#textfile-collector>`_.


Example OWCA config
====================

.. code-block:: yaml

    runner: !MeasurementRunner
      node: !StaticNode
        tasks:
          - task1
      metrics_storage: !LogStorage
        output_filename: 'metrics.prom'
        overwrite: true


and the run like this:

.. code-block:: shell

    sudo ./dist/owca.pex --root -c configs/extra/static_measurements_for_node_exporter.yaml


node_exporter example
=====================

When run node_exporter like this:

.. code-block:: shell
    
    sudo node_exporter --collector.textfile.directory=$PWD


metrics will be available at: http://127.0.0.1:9100/metrics


Example output::

    # HELP owca_tasks Metric read from metrics.prom
    # TYPE owca_tasks gauge
    owca_tasks{cores="4",cpus="8",host="gklab-126-081",owca_version="0.4.dev12+gb86e6ac",sockets="1"} 1
    # HELP owca_up Metric read from metrics.prom
    # TYPE owca_up counter
    owca_up{cores="4",cpus="8",host="gklab-126-081",owca_version="0.4.dev12+gb86e6ac",sockets="1"} 1.555587486599824e+09


You can scrape those metric with Promethues with config like this:

.. code-block:: yaml

    scrape_configs:
      - job_name: local
        scrape_interval: 1s
        static_configs:
          - targets:
            - 127.0.0.1:9100
