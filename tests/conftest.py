"""
Shared pytest configuration and fixtures for python_magnetworkflows tests.

Two custom markers are registered here (and in pyproject.toml):
- ``feelpp``: test requires the feelpp Debian system package
- ``slow``:   test requires real simulation data and significant runtime

Skip logic for feelpp-dependent test *modules* is handled by
``pytest.importorskip("feelpp.core")`` at the top of each affected file —
this skips the entire module at collection time rather than per-test,
which is the cleanest pattern when the module itself cannot be imported
without feelpp.
"""

import os

import pytest

DATA_DIR_ENV = "MAGNETWORKFLOWS_TEST_DATA"


def pytest_configure(config):
    """Register custom markers so pytest does not warn about unknown marks."""
    config.addinivalue_line(
        "markers",
        "feelpp: mark test as requiring the feelpp Debian system package "
        "(deselect with '-m not feelpp')",
    )
    config.addinivalue_line(
        "markers",
        "slow: mark test as requiring real simulation data and significant runtime "
        "(deselect with '-m not slow')",
    )


@pytest.fixture(scope="session")
def feelpp_test_data():
    """Return the path to a directory containing test simulation inputs.

    Set the environment variable ``MAGNETWORKFLOWS_TEST_DATA`` to a directory
    that mirrors the structure used by the example shell scripts in
    ``examples/``, e.g.::

        HLTEST/mean/HLtest-cfpdes-thmag_hcurl-nonlinear-Axi-sim.cfg
        HLTEST/HLtest-flow_params.json
        M9Bitters_18MW/gradHZ/M9Bitters_18MW-cfpdes-thmag_hcurl-nonlinear-Axi-sim.cfg
        M9Bitters_18MW/M9Bitters_18MW-flow_params.json

    If the variable is unset or the directory does not exist, integration tests
    are automatically skipped.
    """
    data_dir = os.environ.get(DATA_DIR_ENV)
    if not data_dir or not os.path.isdir(data_dir):
        pytest.skip(
            f"Set {DATA_DIR_ENV} to a directory with simulation inputs "
            "to run integration tests (see examples/*.sh for the expected structure)."
        )
    return data_dir
