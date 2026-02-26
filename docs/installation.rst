Installation
============

Requirements
------------

* Python >= 3.11
* Feel++ >= 0.102.1 (installed as Debian packages)
* MPI implementation (OpenMPI or MPICH)

Install from source
-------------------

.. code-block:: bash

   git clone https://github.com/MagnetDB/python_magnetworkflows.git
   cd python_magnetworkflows
   git submodule update --init --recursive
   pip install -e .

Install with development extras
--------------------------------

.. code-block:: bash

   pip install -e ".[dev]"

Install documentation dependencies
------------------------------------

.. code-block:: bash

   pip install -e ".[docs]"

Feel++ system packages
-----------------------

Feel++ must be installed separately as Debian packages.
Refer to the `Feel++ documentation <https://docs.feelpp.org>`_ for
installation instructions appropriate for your Linux distribution.
