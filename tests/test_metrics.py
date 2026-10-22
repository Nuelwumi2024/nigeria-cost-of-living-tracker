import sys
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

import extract  # noqa: E402
import forecast as fc  # noqa: E402
import metrics as mx  # noqa: E402


@pytest.fixture(scope="module")
def tables():
    return extract.load_workbook()


@pytest.fixture(scope="module")
def head(tables):
    return mx.series(tables["national"], "All Items")


def test_series_is_complete_monthly(head):
    gaps = head.index.to_series().diff().dropna().dt.days
    assert gaps.between(28, 31).all()
    assert head.index.min() == pd.Timestamp("1995-01-01")


def test_yoy_matches_nbs_published_figures(head, tables):
    ours = mx.yoy(head)
    nbs = tables["reported"].set_index("date").nbs_yoy_pct
    diff = (ours - nbs).dropna()
    assert len(diff) > 300
    assert diff.abs().max() < 0.01


def test_weights_sum_to_100_over_divisions(tables):
    from config import DIVISION_LABELS
    w = tables["weights"].set_index("series").weight
    assert w[list(DIVISION_LABELS)].sum() == pytest.approx(100, abs=0.5)


def test_contributions_add_to_headline(tables, head):
    long = pd.concat([tables["national"], tables["urban"], tables["rural"]])
    d = head.index[-1]
    c = mx.contributions(long, tables["weights"], d.strftime("%Y-%m-%d"))
    assert c.contribution_pp.sum() == pytest.approx(mx.yoy(head)[d], rel=1e-6)
    assert c.share_of_inflation_pct.sum() == pytest.approx(100, rel=1e-6)


def test_real_value_roundtrip():
    idx = pd.Series([100.0, 150.0], index=pd.to_datetime(["2024-01-01", "2025-01-01"]))
    assert mx.real_value(1000, idx, "2024-01-01", "2025-01-01") == pytest.approx(1500)
    assert mx.purchasing_power_lost(idx, "2024-01-01", "2025-01-01") == pytest.approx(100 / 3)


def test_dip_adjusted_removes_the_dip():
    idx = pd.Series([100, 102, 99.0, 101.0], index=pd.date_range("2024-11-01", periods=4, freq="MS"))
    adj = mx.dip_adjusted(idx, months=["2025-01-01"])
    assert mx.mom(adj)["2025-01-01"] > 0
    assert adj.iloc[0] == idx.iloc[0]                    # earlier months untouched
    assert mx.mom(adj)["2025-02-01"] == pytest.approx(mx.mom(idx)["2025-02-01"])  # later growth preserved


def test_snd_forecast_replays_last_years_pattern():
    dates = pd.date_range("2023-01-01", periods=24, freq="MS")
    m = pd.Series(np.tile(np.arange(1.0, 13.0), 2), index=dates)
    f = fc.project_mom(m, "snd", 3)
    assert list(f.round(6)) == [1.0, 2.0, 3.0]


def test_forecast_is_deterministic(head):
    m = mx.mom(head)
    a = fc.forecast_index(head, m, "ewma", 6)
    b = fc.forecast_index(head, m, "ewma", 6)
    pd.testing.assert_series_equal(a, b)
    assert len(a) == 6
