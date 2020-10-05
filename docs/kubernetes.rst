======================
Kubernetes integration
======================

**This software is pre-production and should not be deployed to production servers.**

.. contents:: Table of Contents

Introduction
============

The diagram below puts Kubernetes integration in context of a cluster and monitoring infrastructure:

.. image:: kubernetes_context.png

Kubernetes supported features
=============================

- Monitoring
- Allocation


:Note: In allocation mode, because of Kubernetes internal reconcillation  loop for resource managment (`--sync-frequency <https://kubernetes.io/docs/reference/command-line-tools-reference/kubelet/>`_ defaults to 60s), it is required from Allocator class to repeat desired allocations in every iteration. This will be fixed in future versions.

Kubernetes restrictions
=======================

- Kubernetes version >= 1.13.x,
- cgroup driver: `systemd` or `cgroupfs`.

Possible wca configuration options
==================================
In wca configuration file one can set below listed parameters.
Please refer to `example configuration file for kubernetes <../configs/kubernetes/kubernetes_example_allocator.yaml>`_.


Getting started
===============
Reference configs are in `configuration file for kubernetes <../examples/kubernetes/monitoring>`_.

`How deploy wca solution <../examples/kubernetes/monitoring/wca/README.md>`_
`How deploy cadvisor solution <../examples/kubernetes/monitoring/cadvisor/README.md>`_


Task's metrics labels for Kubernetes
====================================
Task metrics (e.g. cycles, cache_misses_per_kilo_instructions) have labels which are generated in the manner:

- pod's label sanitized (replaced '.' with '_'),
- additional label **task_name** which value is created by joining pod namespace and pod name (e.g. 'default/stress_ng'),
- additional label **task_id** which value is equal to pod identifier.


Task's resources for Kubernetes
===============================
List of available resources:

- disk
- mem
- cpus
- limits_mem
- limits_cpus
- requests_mem
- requests_cpus

Task resources "disk" and "mem" are scalar values expressed in bytes. Fractional "cpus" values correspond to partial shares of a CPU.
They are calculated from containers spec (https://kubernetes.io/docs/concepts/configuration/manage-compute-resources-container/#meaning-of-memory).
``limits_*`` and ``requests_*`` are added according to k8s documentation (https://kubernetes.io/docs/concepts/configuration/manage-compute-resources-container/#resource-requests-and-limits-of-pod-and-container).
