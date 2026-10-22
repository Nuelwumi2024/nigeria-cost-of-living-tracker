"""End-to-end: extract -> metrics -> forecast -> tables for Power BI and the figures."""
from __future__ import annotations

import json

import pandas as pd

import extract
import forecast as fc
import metrics as mx
from config import (MIN_WAGE_2019, MIN_WAGE_2019_DATE, MIN_WAGE_2024, MIN_WAGE_2024_DATE,
                    PROCESSED)


def main() -> dict:
    t = extract.run()
    long = pd.concat([t["national"], t["urban"], t["rural"]], ignore_index=True)
    nat = t["national"]
    head = mx.series(nat, "All Items")
    latest = head.index[-1]
    prior = latest - pd.DateOffset(years=1)
    L, P = latest.strftime("%Y-%m-%d"), prior.strftime("%Y-%m-%d")

    # 1. Headline numbers
    y = mx.yoy(head)
    m_all = mx.mom(head)
    s = {"latest_month": latest.strftime("%Y-%m"), "headline_yoy": float(y[latest]),
         "headline_yoy_prior_year": float(y[prior])}
    for name, key in [("Food", "food"), ("Core Index (All Items Less Farm Produce And Energy)", "core"),
                      ("Energy", "energy"), ("Farm Produce", "farm"), ("Services", "services"),
                      ("Goods", "goods")]:
        s[f"{key}_yoy"] = float(mx.yoy(mx.series(nat, name))[latest])
    pk = mx.peak_and_latest(y, "2022-01-01")
    s.update(peak_yoy=float(pk["peak"]), peak_yoy_date=pk["peak_date"].strftime("%Y-%m"))

    # 2. Purchasing power
    s["power_lost_since_2023_05_pct"] = mx.purchasing_power_lost(head, "2023-05-01", L)
    s["power_lost_last_12m_pct"] = mx.purchasing_power_lost(head, P, L)
    s["n100k_may2023_in_today_naira"] = mx.real_value(100_000, head, "2023-05-01", L)
    s["wage_70k_jul2024_in_jul2024_money"] = MIN_WAGE_2024
    s["wage_70k_now_in_jul2024_money"] = mx.real_value(MIN_WAGE_2024, head, L, MIN_WAGE_2024_DATE)
    s["wage_30k_2019_in_jul2024_money"] = mx.real_value(MIN_WAGE_2019, head, MIN_WAGE_2019_DATE, MIN_WAGE_2024_DATE)
    s["wage_needed_today_to_match_70k_jul2024"] = mx.real_value(MIN_WAGE_2024, head, MIN_WAGE_2024_DATE, L)

    # 3. Drivers and geography
    contrib = mx.contributions(long, t["weights"], L)
    contrib.to_csv(PROCESSED / "contributions_latest.csv", index=False)
    urban = mx.yoy(mx.series(long, "All Items", "Urban"))
    rural = mx.yoy(mx.series(long, "All Items", "Rural"))
    s.update(urban_yoy=float(urban[latest]), rural_yoy=float(rural[latest]))
    gap = (rural - urban).dropna()
    s["rural_minus_urban_avg_since_2020_pp"] = float(gap[gap.index >= "2020-01-01"].mean())

    # 3b. Sensitivity: what if the two January dips are artefacts?
    adj = mx.dip_adjusted(head)
    s["jan_mom_pct_2016_2024_min"] = float(m_all.loc[(m_all.index.month == 1) & (m_all.index.year.isin(range(1996, 2025)))].min())
    s["jan_mom_pct_2025"], s["jan_mom_pct_2026"] = float(m_all["2025-01-01"]), float(m_all["2026-01-01"])
    s["power_lost_since_2023_05_pct_adjusted"] = mx.purchasing_power_lost(adj, "2023-05-01", L)
    s["wage_needed_today_to_match_70k_jul2024_adjusted"] = mx.real_value(MIN_WAGE_2024, adj, MIN_WAGE_2024_DATE, L)
    s["headline_yoy_adjusted"] = float(mx.yoy(adj)[latest])

    # 4. Outlook: choose among methods on 2016-2024 history, then show two scenarios
    m = m_all
    bt = fc.backtest(head, m, "2016-01-01", "2024-06-01", h=6)
    sc = fc.score(bt)
    sc.to_csv(PROCESSED / "forecast_backtest_scores.csv", index=False)
    mae6 = sc[sc.step == 6].set_index("method").mae
    s.update({f"backtest_mae_6m_{k}": float(v) for k, v in mae6.items()}, backtest_origins=int(bt.origin.nunique()))
    rows = []
    for scenario, method in [("January dip repeats", "snd"), ("No January dip", "ewma")]:
        f = fc.forecast_index(head, m, method, 6)
        f_yoy = pd.Series({d: (v / head[d - pd.DateOffset(years=1)] - 1) * 100 for d, v in f.items()})
        lo, hi = fc.interval(bt, method, 6)
        for d, v in f_yoy.items():
            rows.append((scenario, method, d, v, v - hi, v - lo))
    fdf = pd.DataFrame(rows, columns=["scenario", "method", "date", "forecast_yoy", "low_80", "high_80"])
    fdf.to_csv(PROCESSED / "forecast_yoy.csv", index=False)
    end = fdf[fdf.date == fdf.date.max()].set_index("scenario")
    s["forecast_end_date"] = fdf.date.max().strftime("%Y-%m")
    for sc_name, key in [("January dip repeats", "dip"), ("No January dip", "nodip")]:
        s[f"forecast_end_yoy_{key}"] = float(end.loc[sc_name, "forecast_yoy"])
        s[f"forecast_end_low_{key}"] = float(end.loc[sc_name, "low_80"])
        s[f"forecast_end_high_{key}"] = float(end.loc[sc_name, "high_80"])

    # 5. Tidy export for the dashboard
    wide = pd.DataFrame({
        "headline_index": head, "headline_yoy": y, "headline_mom": m_all,
        "food_yoy": mx.yoy(mx.series(nat, "Food")),
        "core_yoy": mx.yoy(mx.series(nat, "Core Index (All Items Less Farm Produce And Energy)")),
        "energy_yoy": mx.yoy(mx.series(nat, "Energy")), "urban_yoy": urban, "rural_yoy": rural})
    wide.index.name = "date"
    wide.to_csv(PROCESSED / "headline_monthly.csv")
    (PROCESSED / "summary.json").write_text(json.dumps(s, indent=2))
    return s


if __name__ == "__main__":
    for k, v in main().items():
        print(f"{k:40s} {v:,.2f}" if isinstance(v, float) else f"{k:40s} {v}")
