"""Inflation metrics. Pure functions over index series so they are easy to test."""
from __future__ import annotations

import numpy as np
import pandas as pd

from config import DIVISION_LABELS, JANUARY_DIPS


def series(long: pd.DataFrame, name: str, geography: str = "National") -> pd.Series:
    s = long[(long.series == name) & (long.geography == geography)]
    return s.set_index("date").index_value.sort_index()


def yoy(idx: pd.Series) -> pd.Series:
    return (idx / idx.shift(12) - 1) * 100


def mom(idx: pd.Series) -> pd.Series:
    """Month-on-month %, as published (January 2025 and 2026 are negative; see config)."""
    return (idx / idx.shift(1) - 1) * 100


def dip_adjusted(idx: pd.Series, months: list[str] = JANUARY_DIPS) -> pd.Series:
    """Sensitivity series: replace each flagged month's m/m with the average of the
    months either side, and carry the level shift forward. Answers "how different would
    the cumulative picture look if the January dips are artefacts?" - not a correction."""
    m = mom(idx)
    out = idx.copy()
    for d in map(pd.Timestamp, months):
        if d not in m.index:
            continue
        before, after = d - pd.DateOffset(months=1), d + pd.DateOffset(months=1)
        target = np.nanmean([m.get(before, np.nan), m.get(after, np.nan)])
        factor = (1 + target / 100) / (1 + m[d] / 100)
        out.loc[out.index >= d] *= factor
    return out


def real_value(amount: float, idx: pd.Series, start: str, end: str) -> float:
    """What `amount` naira at `start` is worth in `end` money (same purchasing power,
    deflated by the CPI). Larger than `amount` means prices rose in between."""
    return amount * idx[pd.Timestamp(end)] / idx[pd.Timestamp(start)]


def purchasing_power_lost(idx: pd.Series, start: str, end: str) -> float:
    """Share (%) of a naira's purchasing power lost between two months."""
    return (1 - idx[pd.Timestamp(start)] / idx[pd.Timestamp(end)]) * 100


def contributions(long: pd.DataFrame, weights: pd.DataFrame, date: str) -> pd.DataFrame:
    """Approximate contribution of each COICOP division to headline y/y inflation.

    contribution_i = weight_i * (I_i,t - I_i,t-12) / sum_j(weight_j * I_j,t-12),
    rescaled so the contributions add up to the headline figure. Weights are the
    2024 basket weights, so this ranks drivers; it is not exact for a chained index."""
    d = pd.Timestamp(date)
    year_ago = d - pd.DateOffset(years=1)
    nat = long[long.geography == "National"]
    rows = []
    for raw_name, label in DIVISION_LABELS.items():
        s = series(nat, raw_name)
        w = float(weights.loc[weights.series == raw_name, "weight"].iloc[0])
        if d in s.index and year_ago in s.index:
            rows.append((label, w, s[year_ago], s[d]))
    t = pd.DataFrame(rows, columns=["division", "weight", "base", "latest"])
    t["yoy_pct"] = (t.latest / t.base - 1) * 100
    raw_contrib = t.weight * (t.latest - t.base) / (t.weight * t.base).sum() * 100
    head = series(nat, "All Items")
    target = (head[d] / head[year_ago] - 1) * 100
    t["contribution_pp"] = raw_contrib * target / raw_contrib.sum()
    t["share_of_inflation_pct"] = t.contribution_pp / target * 100
    return t.sort_values("contribution_pp", ascending=False).reset_index(drop=True)


def peak_and_latest(s: pd.Series, since: str) -> dict:
    x = s[s.index >= pd.Timestamp(since)].dropna()
    return {"peak_date": x.idxmax(), "peak": x.max(), "latest_date": x.index[-1], "latest": x.iloc[-1]}
