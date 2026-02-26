"""
Tests for python_magnetworkflows.args

All tests in this file are pure Python — no feelpp dependency.
"""

import argparse
import json

import pytest

from python_magnetworkflows.args import options


@pytest.fixture()
def parser():
    return options("Test description", "Test epilog")


# ---------------------------------------------------------------------------
# Basic structure
# ---------------------------------------------------------------------------


def test_options_returns_argument_parser(parser):
    assert isinstance(parser, argparse.ArgumentParser)


def test_cfgfile_positional_required(parser):
    with pytest.raises(SystemExit):
        parser.parse_args([])


def test_cfgfile_is_set(parser):
    args = parser.parse_args(["myfile.cfg"])
    assert args.cfgfile == "myfile.cfg"


# ---------------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------------


def test_default_cooling(parser):
    args = parser.parse_args(["myfile.cfg"])
    assert args.cooling == "mean"


def test_default_heatcorrelation(parser):
    args = parser.parse_args(["myfile.cfg"])
    assert args.heatcorrelation == "Montgomery"


def test_default_friction(parser):
    args = parser.parse_args(["myfile.cfg"])
    assert args.friction == "Constant"


def test_default_eps(parser):
    args = parser.parse_args(["myfile.cfg"])
    assert args.eps == pytest.approx(1.0e-3)


def test_default_heatTol(parser):
    args = parser.parse_args(["myfile.cfg"])
    assert args.heatTol == pytest.approx(1.0e-2)


def test_default_itermax(parser):
    args = parser.parse_args(["myfile.cfg"])
    assert args.itermax == 10


def test_default_update_cooling_true(parser):
    args = parser.parse_args(["myfile.cfg"])
    assert args.update_cooling is True


def test_default_reloadcfg_true(parser):
    args = parser.parse_args(["myfile.cfg"])
    assert args.reloadcfg is True


def test_default_debug_false(parser):
    args = parser.parse_args(["myfile.cfg"])
    assert args.debug is False


def test_default_verbose_false(parser):
    args = parser.parse_args(["myfile.cfg"])
    assert args.verbose is False


def test_default_wd(parser):
    args = parser.parse_args(["myfile.cfg"])
    assert args.wd == "."


# ---------------------------------------------------------------------------
# Flag overrides
# ---------------------------------------------------------------------------


def test_no_update_cooling_flag(parser):
    args = parser.parse_args(["myfile.cfg", "--no-update-cooling"])
    assert args.update_cooling is False


def test_no_reloadcfg_flag(parser):
    args = parser.parse_args(["myfile.cfg", "--no-reloadcfg"])
    assert args.reloadcfg is False


def test_debug_flag(parser):
    args = parser.parse_args(["myfile.cfg", "--debug"])
    assert args.debug is True


def test_verbose_flag(parser):
    args = parser.parse_args(["myfile.cfg", "--verbose"])
    assert args.verbose is True


def test_wd_override(parser):
    args = parser.parse_args(["myfile.cfg", "--wd", "/tmp/work"])
    assert args.wd == "/tmp/work"


# ---------------------------------------------------------------------------
# Type coercion and validation
# ---------------------------------------------------------------------------


def test_eps_type_is_float(parser):
    args = parser.parse_args(["myfile.cfg", "--eps", "1e-5"])
    assert isinstance(args.eps, float)
    assert args.eps == pytest.approx(1e-5)


def test_itermax_type_is_int(parser):
    args = parser.parse_args(["myfile.cfg", "--itermax", "20"])
    assert isinstance(args.itermax, int)
    assert args.itermax == 20


def test_invalid_cooling_choice_raises(parser):
    with pytest.raises(SystemExit):
        parser.parse_args(["myfile.cfg", "--cooling", "invalid"])


def test_valid_cooling_choices(parser):
    for cooling in ["mean", "grad", "meanH", "gradH", "gradHZ", "gradHZH"]:
        args = parser.parse_args(["myfile.cfg", "--cooling", cooling])
        assert args.cooling == cooling


def test_mdata_parses_json(parser):
    mdata_str = '{"test": {"value": 31000, "type": "helix"}}'
    args = parser.parse_args(["myfile.cfg", "--mdata", mdata_str])
    assert args.mdata == json.loads(mdata_str)
