=================
Development guide
=================

**This software is pre-production and should not be deployed to production servers.**

.. contents:: Table of Contents

Please follow rules from `contributing guide <contributing.rst>`_ .

Preparing developer environment
-------------------------------

1. Install `epel-release` repository and basic developer tools:

.. code-block:: shell

    yum install make git which

Note: that on production system, you should use Python 3.6 as describe `here <install.rst>`_.

2. Install Python 3.6:

.. code-block:: shell

    yum install python3

Getting source code and preparing python virtualenv
---------------------------------------------------

1. Clone WCA repository:

.. code-block:: shell

    git clone https://github.com/intel/workload-collocation-agent

2. Further commands should be run from wca root directory:

.. code-block:: shell

    cd workload-collocation-agent

3. Prepare virtual environment for WCA:

.. code-block:: shell

    make venv

5. Start using newly created virtualenv:

.. code-block:: shell

    source env/bin/activate

If you need to deactivate virtual environment simply use command:

.. code-block:: shell

    deactivate

Running unit tests
------------------

Those command should be run from `virtual environment`:

.. code-block:: shell

    make unit

Code style check and building PEX files
---------------------------------------

You can use make to check code style, or build packages:

.. code-block:: shell

    make flake8
    make wca_package

Running locally (for development purposes)
------------------------------------------

You can run without building a distribution like this(venv must exist prior to running following commands):


.. code-block:: shell
    
    source env/bin/activate
    sudo env PYTHONPATH=. `which python` wca/main.py --root -c $PWD/configs/extra/static_measurements.yaml


Using example allocator:


.. code-block:: shell

    source env/bin/activate
    sudo env PYTHONPATH=. `which python` wca/main.py --root -c configs/extra/static_allocator.yaml

Fast distribution rebuild
-------------------------

When rebuilding you can use existing PEX build cache, to speedup building process (cache TTL set to 7 days):

.. code-block:: shell

    PEX_OPTIONS='--no-index --cache-ttl=604800' make wca_package

Running PEX in debug mode
-------------------------

It will try to find an ipdb or use internal built-in pdb module before running main() function to enter debug mode.

.. code-block:: shell

    PEX_MODULE=wca.main:debug ./dist/wca.pex
