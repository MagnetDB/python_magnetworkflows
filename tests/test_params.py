"""
Tests for python_magnetworkflows.params

All tests in this file are pure Python — no feelpp dependency.
"""

import pytest
import pandas as pd

from python_magnetworkflows.params import CFGDIR_PLACEHOLDER, getTarget, getparam, resolve_cfgdir_path


# ---------------------------------------------------------------------------
# resolve_cfgdir_path
# ---------------------------------------------------------------------------


def test_resolve_cfgdir_path_replaces_placeholder():
    result = resolve_cfgdir_path("$cfgdir/data/file.csv", "/abs/path")
    assert result == "/abs/path/data/file.csv"


def test_resolve_cfgdir_path_no_placeholder():
    result = resolve_cfgdir_path("/already/absolute.csv", "/basedir")
    assert result == "/already/absolute.csv"


def test_resolve_cfgdir_path_multiple_occurrences():
    # str.replace replaces ALL occurrences
    result = resolve_cfgdir_path("$cfgdir/$cfgdir/file", "/base")
    assert result == "/base//base/file"


def test_resolve_cfgdir_path_empty_path():
    result = resolve_cfgdir_path("", "/base")
    assert result == ""


def test_resolve_cfgdir_path_empty_basedir():
    result = resolve_cfgdir_path("$cfgdir/file.csv", "")
    assert result == "/file.csv"


def test_resolve_cfgdir_placeholder_constant():
    assert CFGDIR_PLACEHOLDER == "$cfgdir"


# ---------------------------------------------------------------------------
# getparam
# ---------------------------------------------------------------------------


def test_getparam_returns_matching_keys():
    params = {"U_H1": 1.0, "U_H2": 2.0, "N_H1": 5}
    result = getparam("U", params, r"U_H\d+")
    assert sorted(result) == ["U_H1", "U_H2"]


def test_getparam_no_match_returns_empty():
    params = {"N_H1": 5, "N_H2": 10}
    result = getparam("U", params, r"U_H\d+")
    assert result == []


def test_getparam_fullmatch_only():
    # fullmatch: "U_H1_extra" must NOT match r"U_H\d+"
    params = {"U_H1": 1.0, "U_H1_extra": 2.0}
    result = getparam("U", params, r"U_H\d+")
    assert result == ["U_H1"]
    assert "U_H1_extra" not in result


def test_getparam_empty_parameters():
    result = getparam("U", {}, r"U_H\d+")
    assert result == []


def test_getparam_returns_list():
    params = {"hw_Channel0": 1234.0}
    result = getparam("hw", params, r"hw_Channel\d+")
    assert isinstance(result, list)
    assert "hw_Channel0" in result


def test_getparam_complex_pattern():
    params = {
        "Tw_Channel0": 300.0,
        "Tw_Channel1": 301.0,
        "dTw_Channel0": 5.0,
        "Other": 99.0,
    }
    result = getparam("Tw", params, r"Tw_Channel\d+")
    assert len(result) == 2
    assert "dTw_Channel0" not in result


# ---------------------------------------------------------------------------
# getTarget
# ---------------------------------------------------------------------------


@pytest.fixture()
def power_csv():
    return pd.DataFrame(
        {
            "Statistics_PowerM_integrate": [100.0, 110.0],
            "Statistics_Power_H1_integrate": [40.0, 45.0],
            "Statistics_Power_H2_integrate": [60.0, 65.0],
            "Unrelated_Col": [1.0, 2.0],
        }
    )


@pytest.fixture()
def power_m_targetdefs():
    return {
        "PowerM": {
            "csv": "heat.measures/values.csv",
            "rematch": r"Statistics_PowerM_\w+",
            "post": {"type": "Statistics_PowerM", "math": "integrate"},
        }
    }


def test_getTarget_filters_columns(power_csv, power_m_targetdefs):
    df = getTarget(power_m_targetdefs, "PowerM", power_csv)
    assert all("Statistics_PowerM" in col or col == list(df.columns)[0] for col in power_csv.columns if col in df.columns)
    assert "Unrelated_Col" not in df.columns
    assert "Statistics_Power_H1_integrate" not in df.columns


def test_getTarget_renames_columns(power_csv, power_m_targetdefs):
    df = getTarget(power_m_targetdefs, "PowerM", power_csv)
    for col in df.columns:
        assert "Statistics_PowerM_" not in col
        assert "_integrate" not in col


def test_getTarget_preserves_row_count(power_csv, power_m_targetdefs):
    df = getTarget(power_m_targetdefs, "PowerM", power_csv)
    assert len(df) == len(power_csv)


def test_getTarget_missing_key_raises():
    with pytest.raises(KeyError):
        getTarget({}, "NonExistent", pd.DataFrame({"col": [1]}))


def test_getTarget_no_matching_columns_returns_empty_df():
    targetdefs = {
        "X": {
            "csv": "x.csv",
            "rematch": r"NoSuchPattern_\d+",
            "post": {"type": "NoSuchPattern", "math": "val"},
        }
    }
    csv = pd.DataFrame({"Statistics_PowerM_integrate": [1.0]})
    df = getTarget(targetdefs, "X", csv)
    assert df.empty


def test_getTarget_returns_deep_copy(power_csv, power_m_targetdefs):
    """Mutating the returned DataFrame must not affect the original."""
    original_val = power_csv["Statistics_PowerM_integrate"].iloc[0]
    df = getTarget(power_m_targetdefs, "PowerM", power_csv)
    col = df.columns[0]
    df[col] = 0.0
    assert power_csv["Statistics_PowerM_integrate"].iloc[0] == original_val
