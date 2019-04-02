=============
Mesos support
=============

**This software is pre-production and should not be deployed to production servers.**

.. contents:: Table of Contents

Mesos supported features
========================

- Monitoring
- Allocation:

Supported Mesos agent configuration
===================================

- version > 1.2.x
- ``containerizers=mesos`` - `Mesos containerizer <http://mesos.apache.org/documentation/latest/containerizers/#Mesos>`_ - to enable PID based cgroup discovery,
- ``isolations=cgroups/cpu,cgroups/perf_event`` - to enable CPU shares management and perf_event monitoring,
- ``perf_events=cycles`` and ``perf_events=360days`` - to enable perf_event cgroup management without actual counter collection,


Following exact configuration was verified to work with provided workloads:

- Mesos version == 1.2.6
- ``isolation=filesystem/linux,docker/volume,docker/runtime,cgroups/cpu,cgroups/perf_event``
- ``cgroups_enable_cfs=true``
- ``hostname_lookup=false``
- ``image_providers=docker``
- ``attributes/own_ip=HOST_IP``
- Docker registry V2


