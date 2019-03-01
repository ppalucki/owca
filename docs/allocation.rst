===============================
Allocation algorithm interface
===============================

**This software is pre-production and should not be deployed to production servers.**

Note: **This API is not considered stable, but work in progress** - please see https://github.com/intel/owca/pull/10 for status of implementation.

.. contents:: Table of Contents

Introduction
------------

Resource allocation interface allows to provide control logic based on gathered platform and resources metrics and enforce isolation
on compute resources (cpu, cache and memory).

Configuration 
-------------

Example of minimal configuration to use as ``AllocationRuner`` structure in
configuration file  ``config.yaml``:

.. code:: yaml

    runner: !AllocationRunner
      node: !MesosNode
      action_delay: 1                                  # [s]
      allocator: !ExampleAllocator

Provided  ``AllocationRunner`` class has the following required and optional attributes.

.. code:: python

    @dataclass
    class AllocationRunner:

        # Required
        node: MesosNode
        allocator: Allocator

        # Optional with default values
        action_delay: float = 1.                        # callback function call interval [s]
        # Default static configuration for allocation
        allocations: AllocationConfiguration = AllocationConfiguration()
        metrics_storage: Storage = LogStorage()         # stores internal and input metrics for allocation algorithm
        allocations_storage: Storage = LogStorage()     # stores any allocations issued on tasks
        anomalies_storage: Storage = LogStorage()       # stores any detected anomalies during allocation iteration

``AllocationConfigurations`` structure contains static configuration to perform normalization of specific resource allocations.

.. code-block:: python

    @dataclass
    class AllocationConfiguration:

        # Default value for cpu.cpu_period [us] (used as denominator).
        cpu_quota_period : int = 100000

        # Number of minimum shares, when ``cpu_shares`` allocation is set to 0.0.
        cpu_shares_min: int = 2                   
        # Number of shares to set, when ``cpu_shares`` allocation is set to 1.0.
        cpu_shares_max: int = 10000               

``Allocator`` structure and ``allocate`` resource callback function
--------------------------------------------------------------------
        
``Allocator`` class must implement one function with following signature:

.. code:: python

    class Allocator(ABC):

        def allocate(self,
                platform: Platform,
                tasks_measurements: TasksMeasurements,
                tasks_resources: TasksResources,
                tasks_labels: TasksLabels,
                tasks_allocations: TasksAllocations,             
            ) -> (TasksAllocations, List[Anomaly], List[Metric]):
            ...


Allocation interface reuses existing ``Detector`` input and metric structures. Please refer to `detection document <detection.rst>`_ 
for further reference on ``Platform``, ``TaskResources``, ``TasksMeasurements``, ``Anomaly`` and ``TaskLabels`` structures.

``TasksAllocations`` structure is a mapping from task identifier to allocations and defined as follows:

.. code:: python

    TaskId = str
    TasksAllocations = Dict[TaskId, TaskAllocations]
    TaskAllocations = Dict[AllocationType, Union[float, RDTAllocation]]

    # example
    tasks_allocations = {
        'some-task-id': {
            'cpu_quota': 0.6,
            'cpu_shares': 0.8,
            'rdt': RDTAllocation(name='hp_group', l3='L3:0=fffff;1=fffff', mb='MB:0=20;1=5')
        },
        'other-task-id': {
            'cpu_quota': 0.5,
            'rdt': RDTAllocation(name='hp_group', l3='L3:0=fffff;1=fffff', mb='MB:0=20;1=5')
        }
        'one-another-task-id': {
            'cpu_quota': 0.7,
            'rdt': RDTAllocation(name='be_group', l3='L3:0=000ff;1=000ff', mb='MB:0=1;1=1'),
        }
        'another-task-with-own-rdtgroup': {
            'cpu_quota': 0.7,
            'rdt': RDTAllocation(l3='L3:0=000ff;1=000ff', mb='MB:0=1;1=1'),  # "another-task-with-own-rdtgroup" will be used as `name`
        }
        ...
    }


Please refer to `rdt`_ for definition of ``RDTAllocation``.

This structure is used as an input representing currently enforced configuration and as an output representing desired allocations that will be applied in the current ``AllocationRunner`` iteration.

``allocate`` function  may return ``TaskAllocations`` for some tasks only. Resources allocated to tasks that no returned ``TaskAllocations`` describes will not be affected.

The ``AllocationRunner`` is stateful and relies on operating system to store the state. 

Note that, if ``OWCA`` service is restarted, then already applied allocations will not be reset 
(current state of allocation on system will be read and provided as input).

Supported allocations types
---------------------------

Following built-in allocations types are supported:

- ``cpu_quota`` - CPU Bandwidth Control called quota (normalized)
- ``cpu_shares`` - CPU shares for Linux CFS (normalized)
- ``rdt`` - Intel RDT (raw access)

The built-in allocation types are defined using following ``AllocationType`` enumeration:

.. code-block:: python

    class AllocationType(Enum, str):

        QUOTA = 'cpu_quota'
        SHARES = 'cpu_shares'
        RDT = 'rdt'

cpu_quota
^^^^^^^^^

``cpu_quota`` is normalized in respect to whole system capacity (all logical processor) and will be applied using cgroups cpu subsystem
using CFS bandwidth control.

For example, with default ``cpu_period`` set to **100ms** on machine with **16** logical processor, setting ``cpu_quota`` to **0.25**, means that
hard limit on quarter on the available CPU resources, will effectively translated into **400ms** quota.

Base ``cpu_period`` value is configured in ``AllocationConfiguration`` structure during ``AllocationRunner`` initialization.

Formula for calculating quota for cgroup subsystem:

.. code-block:: python

    effective_cpu_quota = task_cpu_quota_normalized * configured_cpu_period * platform_cpus  

Refer to `Kernel sched-bwc.txt <https://www.kernel.org/doc/Documentation/scheduler/sched-bwc.txt>`_ document for further reference.

cpu_shares
^^^^^^^^^^

``cpu_shares`` value is normalized against all cores available on the platform so:

- **1.0** will be translated into ``AllocationConfiguration.cpu_shares_max``
- **0.0** will be translated into ``AllocationConfiguration.cpu_shares_min``

and values between will be normalized according following formula:

.. code-block:: python

    effective_cpu_shares = task_cpu_shares_normalized * (cpu_shares_max - cpu_shares_min) + cpu_shares_min

Refer to `Kernel sched-design <https://www.kernel.org/doc/Documentation/scheduler/sched-design-CFS.txt>`_ document for further reference.


rdt
^^^

.. code-block:: python

    @dataclass
    class RDTAllocation:
        name: str = None  # defaults to TaskId from TasksAllocations
        mb: str = None  # optional - when no provided doesn't change the existing allocation
        l3: str = None  # optional - when no provided doesn't change the existing allocation

You can use ``RDTAllocation`` structure to configure Intel RDT available resources.

``RDTAllocation`` wraps resctrl ``schemata`` file. Using ``name`` property allows one to specify name for control group to be used
for given task to save limited CLOSids and isolate RDT resources for multiple containers at once.

``name`` field is optional and if not provided, the ``TaskID`` from parent structure will be used.

Allocation of available bandwidth for ``mb`` field is given format:

.. code-block::

    MB:<cache_id0>=bandwidth0;<cache_id1>=bandwidth1

expressed in percentage points as described in `Kernel x86/intel_rdt_ui.txt <https://www.kernel.org/doc/Documentation/x86/intel_rdt_ui.txt>`_.

For example:

.. code-block::

    MB:0=20;1=100

If Software Controller is available and enabled during mount, the format is:

.. code-block::

    MB:<cache_id0>=bw_MBps0;<cache_id1>=bw_MBps1

where bw_MBps0 expresses bandwidth in MBps.


Allocation of cache bit mask for ``l3`` field is given format:

.. code-block::

    L3:<cache_id0>=<cbm>;<cache_id1>=<cbm>;...

For example:

.. code-block::

    L3:0=fffff;1=fffff


Note that the configured values are passed as is to resctrl filesystem without validation and in case of error, warning is logged.

Refer to `Kernel x86/intel_rdt_ui.txt <https://www.kernel.org/doc/Documentation/x86/intel_rdt_ui.txt>`_ document for further reference.


Extended topology information
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Platform object will provide enough information to be able to construct raw configuration for rdt resources, including:

- number of cache ways, number of minimum number of cache ways required to allocate
- number of sockets

based on ``/sys/fs/resctrl/info/`` and ``procfs``

.. code-block:: python

    class Platform:
        ...
        rdt_information: RDTInformation
        ...

   class RDTInformation:
        ...
        rdt_min_cbm_bits: str  # /sys/fs/resctrl/info/L3/min_cbm_bits
        rdt_cbm_mask: str  #  /sys/fs/resctrl/info/L3/cbm_mask
        rdt_min_bandwidth: str  # /sys/fs/resctrl/info/MB/min_bandwidth
        ...

Refer to `Kernel x86/intel_rdt_ui.txt <https://www.kernel.org/doc/Documentation/x86/intel_rdt_ui.txt>`_ document for further reference.

``TaskAllocations`` metrics
----------------------------

Returned ``TaskAllocations`` will be encoded as metrics and logged using ``Storage``.

When stored using ``KafkaStorage`` returned ``TaskAllocations`` will be encoded in ``Prometheus`` exposition format:

.. code-block:: ini

    allocation(task_id='some-task-id', type='llc_cache', ...<other common and task specific labels>) 0.2 1234567890000
    allocation(task_id='some-task-id', type='cpu_quota', ...<other common and task specific labels>) 0.2 1234567890000
