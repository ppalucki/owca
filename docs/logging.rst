===========================
WCA logging configuration.
===========================

**This software is pre-production and should not be deployed to production servers.**

Command line ``--log-level`` (or ``-l``) argument configures ``wca`` module only.
It is possible to configure logging level for other modules too. Use following call to set logging level for ``example`` module to ``info`` and for ``prm`` to ``debug``:

.. code-block:: shell

    ./dist/wca.pex -l debug -l example:info -l prm:debug


Configuration file can be used to set logging levels. It is impossible to use configuration file to alter logging level during 
object creation (``__init__`` or ``__post_init__``) and configuration file parsing - use command line if necessary.
Setting logging level for module ``""`` will set the level for all the modules including any third party and standard library modules.
Following snippet shows example logging configuration:

.. code-block:: yaml

    loggers:
        wca: error # Enables checking errors in all modules.
        wca.storage: info  # Enables debugging for specifc wca module.
        example.external_package: debug  # Enables verbose mode for external component.

Configuration set using command line arguments overrides configuration set using files.

Example configuration files that include logging configuration can be found in `configs directory <../configs>`_.

To debug logging configuration set ``WCA_DUMP_LOGGERS`` to "``True``" before running WCA.
The configuration will be dumped to standard output.
