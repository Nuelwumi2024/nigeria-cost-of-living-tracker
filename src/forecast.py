"""Six-month inflation outlook: project monthly price growth, rebuild the index, read off y/y.

Three methods are backtested on 2016-2024 history, where the index behaves normally:
  naive : next months grow like the latest month
  ewma  : next months grow like a smoothed recent average
  snd   : "seasonal naive + drift": each month grows like the same month last year,
          shifted by how much recent months ran above their year-ago values
Because the published index has dipped every January since 2025 (see config), the outlook
is reported as two scenarios rather than one number: the dip repeats (snd) or not (ewma).
"""
from __future__ import annotations

import numpy as np
import pandas as pd

METHODS = ("naive", "ewma", "snd")


def project_mom(m: pd.Series, method: str, h: int) -> pd.Series:
    """Forecast monthly growth (%) for the h months after the end of `m`."""
    m = m.dropna()
    dates = pd.date_range(m.index[-1] + pd.DateOffset(months=1), periods=h, freq="MS")
    if method == "naive":
        vals = np.full(h, m.iloc[-1])
    elif method == "ewma":
        vals = np.full(h, m.ewm(alpha=0.5).mean().iloc[-1])
    elif method == "snd":
        last = m.index[-1]
        recent = [d for d in m.index[-3:] if d - pd.DateOffset(years=1) in m.index]
        drift = np.mean([m[d] - m[d - pd.DateOffset(years=1)] for d in recent]) if recent else 0.0
        vals = np.array([m.get(d - pd.DateOffset(years=1), m.iloc[-1]) + drift for d in dates])
        _ = last
    else:
        raise ValueError(method)
    return pd.Series(vals, index=dates)


def forecast_index(idx: pd.Series, mom_pct: pd.Series, method: str, h: int) -> pd.Series:
    g = project_mom(mom_pct.loc[:idx.index[-1]], method, h) / 100
    return idx.iloc[-1] * (1 + g).cumprod()


def backtest(idx: pd.Series, mom_pct: pd.Series, first: str, last: str, h: int = 6) -> pd.DataFrame:
    """Rolling-origin backtest of y/y forecasts: one row per origin x method x step."""
    rows = []
    for origin in pd.date_range(first, last, freq="MS"):
        hist = idx.loc[:origin]
        for method in METHODS:
            f = forecast_index(hist, mom_pct, method, h)
            for step, (d, v) in enumerate(f.items(), 1):
                base = d - pd.DateOffset(years=1)
                if d in idx.index and base in idx.index:
                    rows.append((origin, method, step, (v / idx[base] - 1) * 100,
                                 (idx[d] / idx[base] - 1) * 100))
    return pd.DataFrame(rows, columns=["origin", "method", "step", "forecast_yoy", "actual_yoy"])


def score(bt: pd.DataFrame) -> pd.DataFrame:
    err = (bt.forecast_yoy - bt.actual_yoy).rename("err")
    g = pd.concat([bt[["method", "step"]], err], axis=1).groupby(["method", "step"]).err
    return pd.DataFrame({"mae": g.apply(lambda e: e.abs().mean()), "bias": g.mean(),
                         "n": g.count()}).reset_index()


def interval(bt: pd.DataFrame, method: str, step: int, level: float = 0.8) -> tuple[float, float]:
    """Empirical quantiles of (forecast - actual) for a method at a horizon."""
    sub = bt[(bt.method == method) & (bt.step == step)]
    e = sub.forecast_yoy - sub.actual_yoy
    lo, hi = np.quantile(e, [(1 - level) / 2, 1 - (1 - level) / 2])
    return float(lo), float(hi)
