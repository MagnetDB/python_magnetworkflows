"""
Tests for python_magnetworkflows.real_methods

All tests in this file are pure Python — no feelpp dependency.

Note on getMin: the current implementation reads the column
``Statistics_Max{field}_{marker}_min`` (using "Max" prefix, not "Min").
This is documented in tests so that a future fix to this naming
inconsistency is easy to identify.
"""

import pytest
import pandas as pd

from python_magnetworkflows.real_methods import getMax, getMean, getMin


@pytest.fixture()
def temp_df():
    """DataFrame simulating feelpp temperature statistics output."""
    return pd.DataFrame(
        {
            "Statistics_MeanT_ConductorH1_mean": [295.0, 296.5, 300.0],
            "Statistics_MaxT_ConductorH1_max": [310.0, 315.0, 320.0],
            # NOTE: getMin reads Statistics_Max* (not Statistics_Min*) columns
            "Statistics_MaxT_ConductorH1_min": [290.0, 291.0, 292.0],
            "Statistics_MeanT_ConductorH2_mean": [298.0, 299.0, 301.0],
        }
    )


# ---------------------------------------------------------------------------
# getMean
# ---------------------------------------------------------------------------


def test_getMean_returns_last_row_value(temp_df):
    assert getMean(temp_df, "ConductorH1", "T") == pytest.approx(300.0)


def test_getMean_correct_marker(temp_df):
    assert getMean(temp_df, "ConductorH2", "T") == pytest.approx(301.0)


def test_getMean_single_row():
    df = pd.DataFrame({"Statistics_MeanT_M1_mean": [42.5]})
    assert getMean(df, "M1", "T") == pytest.approx(42.5)


def test_getMean_missing_column_raises(temp_df):
    with pytest.raises(KeyError):
        getMean(temp_df, "NonExistent", "T")


# ---------------------------------------------------------------------------
# getMax
# ---------------------------------------------------------------------------


def test_getMax_returns_last_row_value(temp_df):
    assert getMax(temp_df, "ConductorH1", "T") == pytest.approx(320.0)


def test_getMax_single_row():
    df = pd.DataFrame({"Statistics_MaxT_M1_max": [99.9]})
    assert getMax(df, "M1", "T") == pytest.approx(99.9)


def test_getMax_missing_column_raises(temp_df):
    with pytest.raises(KeyError):
        getMax(temp_df, "NonExistent", "T")


# ---------------------------------------------------------------------------
# getMin — NOTE: reads Statistics_Max{field}_{marker}_min (not Statistics_Min*)
# ---------------------------------------------------------------------------


def test_getMin_uses_max_prefix_in_column_name():
    """getMin reads Statistics_Max{field}_{marker}_min, not Statistics_Min{field}."""
    df = pd.DataFrame({"Statistics_MaxT_ConductorH1_min": [288.0, 289.0, 287.5]})
    assert getMin(df, "ConductorH1", "T") == pytest.approx(287.5)


def test_getMin_returns_last_row_value(temp_df):
    assert getMin(temp_df, "ConductorH1", "T") == pytest.approx(292.0)


def test_getMin_single_row():
    df = pd.DataFrame({"Statistics_MaxT_M1_min": [10.5]})
    assert getMin(df, "M1", "T") == pytest.approx(10.5)


def test_getMin_missing_column_raises(temp_df):
    with pytest.raises(KeyError):
        getMin(temp_df, "NonExistent", "T")


# ---------------------------------------------------------------------------
# All methods use iloc[-1] (last row)
# ---------------------------------------------------------------------------


def test_all_methods_use_last_row():
    df = pd.DataFrame(
        {
            "Statistics_MeanT_M1_mean": [1.0, 2.0, 99.0],
            "Statistics_MaxT_M1_max": [5.0, 6.0, 88.0],
            "Statistics_MaxT_M1_min": [0.5, 0.6, 77.0],
        }
    )
    assert getMean(df, "M1", "T") == pytest.approx(99.0)
    assert getMax(df, "M1", "T") == pytest.approx(88.0)
    assert getMin(df, "M1", "T") == pytest.approx(77.0)
