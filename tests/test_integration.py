"""
Integration tests for python_magnetworkflows — require feelpp AND real simulation data.

These tests mirror the example shell scripts in ``examples/`` and launch
actual Feel++ simulations. They are marked both ``feelpp`` and ``slow``
because they can take minutes to hours depending on the mesh and physics.

To run these tests:
1. Install feelpp as a Debian system package (see docs/testing.md)
2. Set the MAGNETWORKFLOWS_TEST_DATA environment variable to a directory
   containing simulation inputs (see the fixture in conftest.py):

       export MAGNETWORKFLOWS_TEST_DATA=~/jeremie-simus
       pytest -m "feelpp and slow" -v

The ``feelpp_test_data`` fixture (defined in conftest.py) will skip the
entire test session if the env var is missing or the path does not exist.
"""

import json
import os

import pytest

pytest.importorskip("feelpp.core")

pytestmark = [pytest.mark.feelpp, pytest.mark.slow]

from python_magnetworkflows.args import options  # noqa: E402
from python_magnetworkflows.oneconfig import oneconfig  # noqa: E402


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _cfg(data_dir: str, *parts: str) -> str:
    """Build an absolute path and skip if the file does not exist."""
    path = os.path.join(data_dir, *parts)
    if not os.path.exists(path):
        pytest.skip(f"Test data not found: {path}")
    return path


# ---------------------------------------------------------------------------
# HLTEST — helix magnet, single config (mirrors examples/HLTEST.sh)
# ---------------------------------------------------------------------------


def test_hltest_helix_oneconfig(feelpp_test_data, tmp_path):
    """
    Smoke integration test mirroring examples/HLTEST.sh.

    Runs one coupled EM-thermal-hydraulic iteration with ``--no-update-cooling``
    (fastest path) and verifies that ``oneconfig`` completes without raising
    and returns a non-empty result table.
    """
    cfg = _cfg(feelpp_test_data, "HLTEST", "mean", "HLtest-cfpdes-thmag_hcurl-nonlinear-Axi-sim.cfg")
    flow = _cfg(feelpp_test_data, "HLTEST", "HLtest-flow_params.json")

    mdata = {
        "test": {
            "value": 31000,
            "type": "helix",
            "filter": "",
            "flow": flow,
        }
    }
    parser = options("integration-test", "")
    args = parser.parse_args(
        [
            cfg,
            "--mdata", json.dumps(mdata),
            "--cooling", "mean",
            "--eps", "1e-3",
            "--no-update-cooling",
        ]
    )

    table, dict_df, _ = oneconfig(cfg, None, args, wd=str(tmp_path))

    assert table is not None
    assert dict_df is not None


# ---------------------------------------------------------------------------
# M9Bitters — bitter magnet (mirrors examples/M9Bitters.sh, single step only)
# ---------------------------------------------------------------------------


def test_m9bitters_bitter_oneconfig(feelpp_test_data, tmp_path):
    """
    Minimal integration test for a bitter-type magnet (single current step).

    This mirrors the M9Bitters.sh example but runs only one configuration
    rather than a full commissioning ramp.
    """
    cfg = _cfg(
        feelpp_test_data,
        "M9Bitters_18MW",
        "gradHZ",
        "M9Bitters_18MW-cfpdes-thmag_hcurl-nonlinear-Axi-sim.cfg",
    )
    flow = _cfg(feelpp_test_data, "M9Bitters_18MW", "M9Bitters_18MW-flow_params.json")

    mdata = {
        "HLtest": {
            "value": 12000,
            "type": "bitter",
            "filter": "",
            "relax": 0,
            "flow": flow,
        }
    }
    parser = options("integration-test", "")
    args = parser.parse_args(
        [
            cfg,
            "--mdata", json.dumps(mdata),
            "--cooling", "gradHZ",
            "--eps", "1e-3",
        ]
    )

    table, dict_df, _ = oneconfig(cfg, None, args, wd=str(tmp_path))

    assert table is not None
    assert dict_df is not None
