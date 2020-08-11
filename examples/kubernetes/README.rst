**This software is pre-production and should not be deployed to production servers.**

================================
Examples of Kubernetes manifests
================================

This folder contains:

- `monitoring <monitoring>`_ manifests to deploy full monitoring stack including WCA integrated with node_exporter, Prometheus, Grafana and Fluentd,
- `workloads <workloads>`_ manifests to run evaluation workloads on Kubernetes to validated WCA is working correctly,


Deploying monitoring requires to label all the nodes with monitoring label and the following labels:

- ``wca`` to run only wca monitoring container,

- ``cadvisor`` to run only cAdvisor monitoring container,

- ``wca_cadvisor`` to run both on the same node.

it is possible to run them both because wca is using port 9100 to expose metrics for Prometheus, and cAdvisor is using 9101
