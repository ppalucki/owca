=================
Development guide
=================

**This software is pre-production and should not be deployed to production servers.**

.. contents:: Table of Contents

Please follow rules from `contributing guide <contributing.rst>`.

Preparing developer environment
-------------------------------

1. Install `epel-release` repository:

.. code-block:: shell

    yum install epel-release

Note: that on production system, you should use Python 3.6 as describe `here <install.rst>`.

2. Install Python 3.6:

.. code-block:: shell

    yum install python36

Getting source code and preparing python virtualenv
---------------------------------------------------

OWCA uses `pipenv <https://pipenv.readthedocs.io/en/latest/>`_ to create python virtualenv with all tools required to run, validate and build the project.

1. Install pip using 3.6 Python interpreter (available in ``epel`` release and "Software Collections" python collections:

.. code-block:: shell

    python -m ensurepip

2. Install pipenv in user mode:

.. code-block:: shell

    pip install --user pipenv

See `pragmatic installation of pipenv`_ for more details on installing pipenv.

.. _`pragmatic installation of pipenv`: https://docs.pipenv.org/install/#pragmatic-installation-of-pipenv

3. Clone OWCA repository:

.. code-block:: shell

    git clone https://github.com/intel/owca

4. Further commands should be run from owca root directory:

.. code-block:: shell

    cd owca

5. Prepare virtual environment for OWCA:

.. code-block:: shell

    pipenv install --dev

6. Start using newly created virtualenv:

.. code-block:: shell

    pipenv shell

Tip, you can use virtualenv created by pipenv in your favorite IDE. Use `
pipenv --where` to find location of python virutalenv and interpreter.

Running unit tests
------------------

Those command should be run from `virtual environment` created by pipenv:

.. code-block:: shell

    make unit

Code style check and building PEX files
---------------------------------------

You can use make to check code style, or build packages:

.. code-block:: shell

    make flake8
    make owca_package
    make wrapper_package

Running locally (for development purposes)
------------------------------------------

You can run without building a distribution like this: 

.. code-block:: shell
    
    python3.6 -mpipenv shell
    sudo env PYTHONPATH=. `which python` owca/main.py --root -c configs/extra/static_measurements.yaml


Using example allocator:


.. code-block:: shell

    python3.6 -mpipenv shell
    sudo env PYTHONPATH=. `which python` owca/main.py --root -c configs/extra/static_allocator.yaml

Fast distribution rebuild
-------------------------

When rebuilding you can use existing PEX build cache, to speedup building process (cache TTL set to 7 days):

.. code-block:: shell

    PEX_OPTIONS='--no-index --cache-ttl=604800' make owca_package

Running PEX in debug mode
-------------------------

It will try to find an ipdb or use internal built-in pdb module before running main() function to enter debug mode.

.. code-block:: shell

    PEX_MODULE=owca.main:debug ./dist/owca.pex
