=====================================================
Migration to cAdvisor
=====================================================

**This part is currently developed and is missing proper testing and validation**

Kubernetes deployment
=====================

There is a ready to use example of cAdvisor deployment with perf support available `on cAdvisor repo as overlay example <https://github.com/google/cadvisor/tree/master/deploy/kubernetes#cadvisor-with-perf-support-on-kubernetes>`_. It is advised to change the cpu limitations in daemonset definition, as prometheus client, which is serving the stats, tends to generate a lot of CPU load with growth of stats size.

Perf support in cAdvisor
========================

Explanation on how to use perf in cAdvisor is available in its documentation `here <https://github.com/google/cadvisor/blob/master/docs/runtime_options.md#perf-events>`_. Both implementation and documentation are under development, so changes will occur. As of today, official image in google docker registry does not support perfs, so one has to build their own image to use them.


Building cAdvisor with perf
===========================

As specified in `official build instruction <https://github.com/google/cadvisor/blob/master/docs/development/build.md#perf-support>`_, assuming that ones environment is capable of building go packages, the following steps have to be done:

.. code-block:: shell

  # To support perf libpfm is required, to support ipmctl use package manager appropiate for distribution
  # Next 6 lines are for ipmctl dependencies management, consult https://github.com/intel/ipmctl#build for claryfication
  cd /etc/yum.repos.d/
  wget https://copr.fedorainfracloud.org/coprs/jhli/ipmctl/repo/epel-7/jhli-ipmctl-epel-7.repo
  wget https://copr.fedorainfracloud.org/coprs/jhli/safeclib/repo/epel-7/jhli-safeclib-epel-7.repo
  yum install https://dl.fedoraproject.org/pub/epel/epel-release-latest-7.noarch.rpm
  subscription-manager repos --enable "rhel-*-optional-rpms" --enable "rhel-*-extras-rpms"  --enable "rhel-ha-for-rhel-*-server-rpms"
  yum install ndctl ndctl-libs ndctl-devel libsafec rubygem-asciidoctor
  # End of ipmctl lib preparation
  yum install libpfm libpfm-devel libimpctl-devel libimpctl
  git clone https://github.com/google/cadvisor.git
  cd cadvisor
  GO_FLAGS="-tags=libipmctl,libpfm,netgo" make build
  # To test if the binary has compiled properly
  # Assuming that variable CONFIG_DIR is set to point to the directory in which this README is located
  sudo ./cadvisor --perf_events_config=$CONFIG_DIR/perf-prm-skylake.json

Then, to check if cadvisor is responding, from other terminal on the same machine execute

.. code-block:: shell

  curl localhost:8080/metrics

If there is any output it means, that cadvisor succesfuly binded to port 8080. If output contains ``container_perf_events_total`` metric with any event from perf-prm-skylake.json it means that perf support has been compiled correctly. If output contains ``machine_nvm_avg_power_budget_watts`` it means that ipmctl support has been compiled correctly.

If there is a response it means, that cadvisor was succesfuly compiled and is running properly.
The advantage of running cAdvisor as standalone after compiling it with presented steps, is that it the provides additional information about Intel® Optane™ DC Persistent memory. As of today, docker image built with official Dockerfile is not providing such capabilities.

cAdvisor in docker container
============================

**[WIP]**

Go to cAdvisor repo root directory and run

.. code-block:: shell

  docker build -t cadvisor -f deploy/Dockerfile .

This will produce a docker image called cadvisor containing cAdvisor with perf support. Unlike normal binary build, this one does not require configured Golang environment.


Perf stats in cAdvisor output
=============================

Let's take PRM Skylake configuration as an example. One of the metrics is CYCLE_ACTIVITY.STALLS_MEM_ANY. In the metrics endpoint there would be:

.. code-block:: text

  container_perf_events_total{container_label_addonmanager_kubernetes_io_mode="",container_label_annotation_io_kubernetes_container_hash="7ffa3c73",container_label_annotation_io_kubernetes_container_ports="",container_label_annotation_io_kubernetes_container_restartCount="0",container_label_annotation_io_kubernetes_container_terminationMessagePath="/dev/termination-log",container_label_annotation_io_kubernetes_container_terminationMessagePolicy="File",container_label_annotation_io_kubernetes_pod_terminationGracePeriod="30",container_label_annotation_kubectl_kubernetes_io_last_applied_configuration="",container_label_annotation_kubernetes_io_config_hash="",container_label_annotation_kubernetes_io_config_seen="",container_label_annotation_kubernetes_io_config_source="",container_label_annotation_kubespray_etcd_cert_serial="",container_label_annotation_nginx_cfg_checksum="",container_label_annotation_prometheus_io_port="",container_label_annotation_prometheus_io_scrape="",container_label_app="",container_label_controller_revision_hash="",container_label_io_kubernetes_container_logpath="/var/log/pods/jwalecki-testing_grooshka2_4160bda5-0b89-4757-8c4a-8361c551fecb/jestem/0.log",container_label_io_kubernetes_container_name="jestem",container_label_io_kubernetes_docker_type="container",container_label_io_kubernetes_pod_name="grooshka2",container_label_io_kubernetes_pod_namespace="jwalecki-testing",container_label_io_kubernetes_pod_uid="4160bda5-0b89-4757-8c4a-8361c551fecb",container_label_io_kubernetes_sandbox_id="992fb34841d5526c54cf7a3f4212ac3cb87a6024011294320f10819a79f63ee1",container_label_k8s_app="",container_label_maintainer="",container_label_name="",container_label_org_label_schema_build_date="20191001",container_label_org_label_schema_license="GPLv2",container_label_org_label_schema_name="CentOS Base Image",container_label_org_label_schema_schema_version="1.0",container_label_org_label_schema_vendor="CentOS",container_label_pod_template_generation="",container_label_version="",cpu="9",event="CYCLE_ACTIVITY.STALLS_MEM_ANY",id="/kubepods/besteffort/pod4160bda5-0b89-4757-8c4a-8361c551fecb/5c73e5df063e9e3e99e7ae10065e877b3c91a042a41a723b0ee93718525f391a",image="100.64.176.12:80/wca/stress_ng@sha256:beabce374593919201589e34ff8f207c1035cf3b39b5c814218012e35ea0e817",name="k8s_jestem_grooshka2_jwalecki-testing_4160bda5-0b89-4757-8c4a-8361c551fecb_0"} 7.676256951e+09 1593431778632

.. code-block:: text

  container_perf_events_scaling_ratio{container_label_addonmanager_kubernetes_io_mode="",container_label_annotation_io_kubernetes_container_hash="7ffa3c73",container_label_annotation_io_kubernetes_container_ports="",container_label_annotation_io_kubernetes_container_restartCount="0",container_label_annotation_io_kubernetes_container_terminationMessagePath="/dev/termination-log",container_label_annotation_io_kubernetes_container_terminationMessagePolicy="File",container_label_annotation_io_kubernetes_pod_terminationGracePeriod="30",container_label_annotation_kubectl_kubernetes_io_last_applied_configuration="",container_label_annotation_kubernetes_io_config_hash="",container_label_annotation_kubernetes_io_config_seen="",container_label_annotation_kubernetes_io_config_source="",container_label_annotation_kubespray_etcd_cert_serial="",container_label_annotation_nginx_cfg_checksum="",container_label_annotation_prometheus_io_port="",container_label_annotation_prometheus_io_scrape="",container_label_app="",container_label_controller_revision_hash="",container_label_io_kubernetes_container_logpath="/var/log/pods/jwalecki-testing_grooshka2_4160bda5-0b89-4757-8c4a-8361c551fecb/jestem/0.log",container_label_io_kubernetes_container_name="jestem",container_label_io_kubernetes_docker_type="container",container_label_io_kubernetes_pod_name="grooshka2",container_label_io_kubernetes_pod_namespace="jwalecki-testing",container_label_io_kubernetes_pod_uid="4160bda5-0b89-4757-8c4a-8361c551fecb",container_label_io_kubernetes_sandbox_id="992fb34841d5526c54cf7a3f4212ac3cb87a6024011294320f10819a79f63ee1",container_label_k8s_app="",container_label_maintainer="",container_label_name="",container_label_org_label_schema_build_date="20191001",container_label_org_label_schema_license="GPLv2",container_label_org_label_schema_name="CentOS Base Image",container_label_org_label_schema_schema_version="1.0",container_label_org_label_schema_vendor="CentOS",container_label_pod_template_generation="",container_label_version="",cpu="9",event="CYCLE_ACTIVITY.STALLS_MEM_ANY",id="/kubepods/besteffort/pod4160bda5-0b89-4757-8c4a-8361c551fecb/5c73e5df063e9e3e99e7ae10065e877b3c91a042a41a723b0ee93718525f391a",image="100.64.176.12:80/wca/stress_ng@sha256:beabce374593919201589e34ff8f207c1035cf3b39b5c814218012e35ea0e817",name="k8s_jestem_grooshka2_jwalecki-testing_4160bda5-0b89-4757-8c4a-8361c551fecb_0"} 0.3347823902298469 1593440294263



Two types can be distinguished:

- ``container_perf_events_total``, which is the value of the metric

- ``container_perf_events_scaling_ratio``, which is an information on how long in proportion to other active counters, given value had been measured. The requirement to scale the number comes from the fact, that the measurements are by limited number of hardware counters, thus system is multiplexing them and the information on this multiplexing proportion is required to get good estimation of counter accuarcy. The value from ``container_perf_events_total`` is already scaled, so this number only informs about proportion.

All perf metrics will have those two entries. Besides that, all perf metrics are the same entry differing by the tag event, which in this case looks like this: event="CYCLE_ACTIVITY.STALLS_MEM_ANY".

By design cAdvisor is not doing any processing like aggregation, so you will see a lot of entries regarding the same container. Couple of tags useful to sum by in Prometheus are:

- ``container_label_io_kubernetes_container_name``
- ``container_label_io_kubernetes_pod_name``
- ``container_label_io_kubernetes_pod_namespace``
- ``container_label_io_kubernetes_pod_uid``
- ``id`` it identifies the continer by mix of pod id and docker container id
- ``name`` it identifies the container by container name asigned by k8s

As perf is under heavy development, be advised, that more types will soon be added, but they will follow the same rules.


Running cAdvisor in docker
==========================

Assuming that command is executed from this directory(in which ``perf-prm-skylake.json`` is located) and previous step was executed to obtain container image named cadvisor, which contains cAdvisor with perf, a way to run cAdvisor with perf measuremente is

.. code-block:: shell

  sudo docker run \
  --volume=/:/rootfs:ro \
  --volume=/var/run:/var/run:ro \
  --volume=/sys:/sys:ro \
  --volume=/var/lib/docker/:/var/lib/docker:ro \
  --volume=/dev/disk/:/dev/disk:ro \
  --volume=$PWD/perf-prm-skylake.json:/etc/configs/perf/perf-prm-skylake.json \
  --publish=8080:8080 \
  --device=/dev/kmsg \
  --privileged \
  --name=cadvisor \
  cadvisor --perf_events_config=/etc/configs/perf/perf-prm-skylake.json

Important note is that it should be run on Skylake platform, as some of the metrics in mentioned json are only available on Skylake. After this, command:

.. code-block:: shell

  curl localhost:8080/metrics | grep cache-misses

should return some output.


Performance on big systems
==========================

On production like systems, where on a single node a lot of containers are running, cAdvisor, and to be more specific it's part responsible for serving prometheus metrics, may experiance slowness due to data amount. On solution is to assure proper allocation of CPU resources for the pod, other one is to disable metrics that are not required. It is done by adding

.. code-block:: shell

  --disable_metrics=tcp,advtcp,udp,sched,process,hugetlb

to the execution(in case of example of running cAdvisor mentioned in this document it would require simply adding this argument). Value presented here is the default value of the parameter. To get values to disable different metrics, see `list of metrics served by prometheus and their groups <https://github.com/google/cadvisor/blob/master/docs/storage/prometheus.md#prometheus-container-metrics>`_.
