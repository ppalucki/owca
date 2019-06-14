===============================
SSL (Secure Socket Layer)
===============================

**This software is pre-production and should not be deployed to production servers.**

.. contents:: Table of Contents

Introduction
------------

Secure Socket Layer allows to establish authenticated secure communication with external services like:

- Kubernetes,
- Mesos,
- Zookeeper,
- etcd.

In all these cases ``SSL`` component can be used to configure client side PKI based authentication or 
server certifications validation.

For ``KubernetesNode``, ``MesosNode`` and ``EtcdDatabase`` the ``SSL`` component is just wrapper for
underlying **requests** library parameters: **ssl_verify** and **cert**.

Please go to `requests library documentation`_ for further reference.

.. _`requests library documentation`: https://2.python-requests.org/en/master/user/advanced/#ssl-cert-verification

For ``ZookeeperDatabase``, the ``SSL`` component is just a transport for following parameters for
**KazooClient** class: **use_ssl**, **ca**, **certfile**, **keyfile** and **verify_certs**. 
Please go to `Kazoo client documentation`_ for more information.

.. _`Kazoo client documentation`: https://kazoo.readthedocs.io/en/latest/api/client.html#kazoo.client.KazooClient


Configuration 
-------------

Example of minimal configuration that uses ``SSL``:

.. code:: yaml

    runner: !AllocationRunner
      node: !KubernetesNode
        ssl: !SSL
          server_verify: True
          client_cert_path: "$PATH/apiserver-kubelet-client.crt"
          client_key_path: "$PATH/apiserver-kubelet-client.key"
        kubelet_endpoint: https://127.0.0.1:10250


``SSL`` object has the following properties:

- **server_verify** - enabled by default to check server certificates against trusted local storage CA or given CA storage (if provided as path),
- **client_cert_path** and client_key_path - to enable client certificates based authentication on server side

Note that for ``KubernetesNode``, ``MesosNode`` or ``EtcdDatabase`` it is also required to enable "https" scheme 
explicitly in **endpoint** and **hosts** properties.
