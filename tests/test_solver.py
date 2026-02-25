"""
Tests for python_magnetworkflows.solver

This entire module is skipped at collection time if feelpp.core is not
importable (system Debian package required). The pytestmark applies the
``feelpp`` marker to every test function for -m filtering.
"""

import json

import pytest

pytest.importorskip("feelpp.core")

pytestmark = pytest.mark.feelpp

from python_magnetworkflows import solver  # noqa: E402


# ---------------------------------------------------------------------------
# Smoke test — verify the module has the expected public API
# ---------------------------------------------------------------------------


def test_solver_module_has_public_api():
    """Confirm solver module imports and exposes its public API."""
    assert callable(solver.init)
    assert callable(solver.solve)
    assert callable(solver.create_field)
    assert callable(solver.init_field)
    assert callable(solver.update)


# ---------------------------------------------------------------------------
# solver.update — pure file I/O, no live feelpp objects needed
# ---------------------------------------------------------------------------


def test_update_replaces_parameters(tmp_path):
    """update() reads a JSON file, replaces the Parameters section, and writes it back."""
    model = {"Parameters": {"U_H1": 1.0, "U_H2": 2.0}, "Models": {"heat": {}}}
    jsonfile = tmp_path / "model.json"
    jsonfile.write_text(json.dumps(model))

    new_params = {"U_H1": 5.0, "U_H2": 7.5}
    solver.update(str(jsonfile), new_params, debug=False)

    written = json.loads(jsonfile.read_text())
    assert written["Parameters"] == new_params


def test_update_preserves_non_parameter_keys(tmp_path):
    """Non-Parameters sections in the JSON are not overwritten."""
    model = {
        "Parameters": {"U_H1": 1.0},
        "Models": {"heat": {}},
        "Meshes": {"cfpdes": {}},
    }
    jsonfile = tmp_path / "model.json"
    jsonfile.write_text(json.dumps(model))

    solver.update(str(jsonfile), {"U_H1": 99.0}, debug=False)

    written = json.loads(jsonfile.read_text())
    assert "Models" in written
    assert "Meshes" in written
    assert written["Models"] == {"heat": {}}
