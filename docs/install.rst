======================================
Building, installing and running OWCA
======================================

**This software is pre-production and should not be deployed to production servers.**

.. contents:: Table of Contents

Building PEX distribution
=========================

Building requirements
---------------------

Please follow the instructions from `development guide <development.rst>`_ to prepare
following items:

- python 3.6
- git
- pip
- pipenv 
- source code of owca

Building executable binary (distribution)
-----------------------------------------

.. code:: shell

   make owca_package

File ``dist/owca.pex`` must be copied to ``/usr/bin/owca.pex``.

Running
========

Runtime requirements
--------------------

- Hardware with `Intel RDT <https://www.intel.pl/content/www/pl/pl/architecture-and-technology/resource-director-technology.html>`_ support.
- Centos 7.5 with at least 3.10.0-862 kernel with support of `resctrl filesystem <https://www.kernel.org/doc/Documentation/x86/intel_rdt_ui.txt>`_.
- Python 3.6.x 

All other the software dependencies are bundled using `PEX <https://github.com/pantsbuild/pex>`_.

Python 3.6 Centos installation (recommended)
--------------------------------------------

The recommended way of installing Python 3.6.x is to use `Software Collections <https://www.softwarecollections.org/en/>`_.
SCL repository is maintained by a CentOS SIG.

Please use `official installation guide <https://www.softwarecollections.org/en/scls/rhscl/rh-python36/>`_ to install Python 3.6 on target hosts.

Then, verify that Python is installed correctly::

    /usr/bin/scl enable rh-python36 'python --version'

Should output::
    
    Python 3.6.3

Alternative options for Python 3.6 installation 
----------------------------------------------

To you simplify python interpreter management (no need to use ``scl`` tool as prefix), 
you can use Intel Distribution for Python according to `yum-based installation guide <https://software.intel.com/en-us/articles/installing-intel-free-libs-and-python-yum-repo>`_.
or use community maintained third-party ``epel`` repository and install ``python36`` package from there::

    yum install epel-release
    yum install python36

CentOS project does not support, nor provide ``epel`` repository.


Running OWCA as non-root user
-----------------------------

OWCA processes should not be run with root privileges. Following privileges are needed to run OWCA as non-root user:

- `CAP_DAC_OVERRIDE capability`_ - to allow non-root user writing to cgroups and resctrlfs kernel filesystems.
- ``/proc/sys/kernel/perf_event_paranoid`` - `content of the file`_ must be set to ``0`` or ``-1`` to allow non-root
  user to collect all the necessary event information.

If it is impossible or undesired to run OWCA with privileges outlined above, then you must add ``-0`` (or its
long form: ``--root``) argument when starting the process)

..  _`CAP_DAC_OVERRIDE capability`: https://github.com/torvalds/linux/blob/6f0d349d922ba44e4348a17a78ea51b7135965b1/include/uapi/linux/capability.h#L119
.. _`content of the file`: https://linux.die.net/man/2/perf_event_open

Running as systemd service
--------------------------

Assumptions:

- ``/var/lib/owca`` directory exists
- ``owca`` user and group already exists
 
Please use following `template <../configs/owca.service>`_ as systemd ``/etc/systemd/system/owca.service`` unit file::

    [Unit]
    Description=Orchestration-aware Workload Collocation Agent

    [Service]
    ExecStart=/usr/bin/scl enable rh-python36 '/usr/bin/owca.pex \
        --config /etc/owca/owca_config.yml \
        --register $EXTRA_COMPONENT \
        --log info'
    User=owca
    Group=owca
    # CAP_DAC_OVERRIDE allows to remove resctrl groups and CAP_SETUID allows to change effective uid to add tasks to the groups
    CapabilityBoundingSet=CAP_DAC_OVERRIDE CAP_SETUID
    AmbientCapabilities=CAP_DAC_OVERRIDE CAP_SETUID
    # We must avoid dropping capabilities after changing effective uid from root to owca
    SecureBits=no-setuid-fixup
    Restart=always
    RestartSec=5
    LimitNOFILE=500000
    WorkingDirectory=/var/lib/owca

    [Install]
    WantedBy=multi-user.target

where:

``$EXTRA_COMPONENT`` should be replaced with name of a class e.g. ``example.external_package:ExampleDetector``.
Class name must comply with `pkg_resources <https://setuptools.readthedocs.io/en/latest/pkg_resources.html#id2>`_ format.
All dependencies of the class must be available in currently used `PYTHONPATH`.

You can use ``example.external_package:ExampleDetector`` that is already bundled within ``dist/owca.pex`` file.

It is recommended to build a pex file with external component and its dependencies bundled. See `prm plugin from platform-resource-manager 
<https://github.com/intel/platform-resource-manager/tree/master/prm>`_ as an example of such an approach.

See an `example configuration file <configs/mesos_kafka_example.yaml>`_ to be used with ``ExampleDetector``:

.. code-block:: yaml

    runner: !DetectionRunner
      rdt_enabled: true
      node: !MesosNode
        ssl_verify: true
        mesos_agent_endpoint: "https://127.0.0.1:5051"
      action_delay: 1.
      metrics_storage: !KafkaStorage
        brokers_ips: ['$KAFKA_BROKER_IP:9092']
        topic: "owca_metrics"
        max_timeout_in_seconds: 5.
      anomalies_storage: !KafkaStorage
        brokers_ips: ['$KAFKA_BROKER_IP:9092']
        topic: "owca_anomalies"
        max_timeout_in_seconds: 5.
      detector: !ExampleDetector
        skew: true
      extra_labels:
        own_ip: "$HOST_IP"  # optional


Apply following changes to the file above:

- ``$KAFKA_BROKER`` must be replaced with IP address of Kafka broker,
- ``$HOST_IP`` may be replaced with host IP address to tag all metrics originating from OWCA process

Following configuration is required in order to use ``MesosNode`` component to discover new tasks:

- `Mesos containerizer <http://mesos.apache.org/documentation/latest/mesos-containerizer/>`_ (``--containerizers=mesos``) must be used.
- Mesos agent must be `configured <http://mesos.apache.org/documentation/latest/configuration/agent/#isolation>`_ to support following `isolators <http://mesos.apache.org/documentation/latest/mesos-containerizer/#isolators>`_ 
   - ``filesystem/linux``,
   - ``docker/volume``,
   - ``docker/runtime``,
   - ``cgroups/cpu``,
   - ``cgroups/perf_event``.
- Mesos agent must expose operator API over `secure socket <http://mesos.apache.org/documentation/latest/ssl/>`_. OWCA TLS can be disabled in configuration by modifying ``mesos_agent_endpoint`` property.
- Mesos agent may be `configured <http://mesos.apache.org/documentation/latest/configuration/agent/#image_providers>`_ to use Docker registry to fetch images. 

