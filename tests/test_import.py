"""Smoke tests – verify the package and its submodules can be imported.

feelpp and python_magnetcooling are mocked by conftest.py so these tests
run without the Feel++ Debian packages being present.
"""

import importlib


def _import(module: str):
    """Helper: import *module* and return it (fails the test on ImportError)."""
    return importlib.import_module(module)


def test_package_imports():
    mod = _import("python_magnetworkflows")
    assert hasattr(mod, "__version__")


def test_args_imports():
    _import("python_magnetworkflows.args")


def test_params_imports():
    _import("python_magnetworkflows.params")


def test_real_methods_imports():
    _import("python_magnetworkflows.real_methods")


def test_error_imports():
    _import("python_magnetworkflows.error")


def test_solver_imports():
    _import("python_magnetworkflows.solver")


def test_oneconfig_imports():
    _import("python_magnetworkflows.oneconfig")


def test_commissioning_imports():
    _import("python_magnetworkflows.commissioning")


def test_run_imports():
    _import("python_magnetworkflows.run")


def test_cli_imports():
    _import("python_magnetworkflows.cli")
