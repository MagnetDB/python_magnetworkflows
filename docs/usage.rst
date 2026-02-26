Usage
=====

Command-line interface
-----------------------

The package provides two CLI entry points:

``python_magnetworkflows``
   Main entry point for running a single magnet workflow simulation.

   .. code-block:: bash

      python_magnetworkflows --help

``python_magnetworkflows_run``
   Entry point for running parametric studies over a set of
   configurations.

   .. code-block:: bash

      python_magnetworkflows_run --help

Magnet types
------------

The CLI supports three magnet types via the ``--magnet-type`` option:

* ``INSERT`` – insert-style resistive magnets (helical coils)
* ``BITTERS`` – Bitter-plate magnets
* ``SUPRAS`` – superconducting magnets

Example – single run
---------------------

.. code-block:: bash

   python_magnetworkflows \
       --magnet-type INSERT \
       --config path/to/magnet.json \
       --current 31000

Example – parametric study
---------------------------

.. code-block:: bash

   python_magnetworkflows_run \
       --magnet-type BITTERS \
       --config path/to/bitter.json \
       --currents 10000 20000 30000

See the :doc:`examples <../Examples>` page and the ``examples/``
directory in the repository for more complete shell-script examples.
