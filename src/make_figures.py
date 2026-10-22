"""Charts for the README and brief. One message per chart; titles state the finding."""
from __future__ import annotations

import json

import matplotlib
matplotlib.use("Agg")
import matplotlib.dates
import matplotlib.pyplot as plt
import pandas as pd

from config import EVENTS, FIGURES, MIN_WAGE_2019, MIN_WAGE_2024, PROCESSED, SOURCE_NOTE

INK, MUTED, GRID = "#1f2933", "#6b7280", "#e5e7eb"
BLUE, ORANGE, GREEN, GREY = "#0072B2", "#D55E00", "#009E73", "#8a8f98"
SRC = "Source: " + SOURCE_NOTE.split(",")[0] + ", CPI Sept 2026 release. Author's analysis."

plt.rcParams.update({"font.family": "DejaVu Sans", "axes.edgecolor": GRID, "axes.labelcolor": MUTED,
                     "xtick.color": MUTED, "ytick.color": MUTED, "axes.spines.top": False,
                     "axes.spines.right": False, "axes.grid": True, "grid.color": GRID,
                     "grid.linewidth": 0.8, "axes.axisbelow": True, "figure.dpi": 140,
                     "axes.titleweight": "bold", "axes.titlesize": 12.5, "axes.titlelocation": "left"})


def _finish(fig, ax, title, subtitle, name):
    ax.set_title(title, color=INK, pad=22)
    ax.text(0, 1.02, subtitle, transform=ax.transAxes, color=MUTED, fontsize=9)
    fig.text(0.01, 0.01, SRC, color=MUTED, fontsize=7)
    fig.tight_layout(rect=(0, 0.03, 1, 1))
    fig.savefig(FIGURES / name, bbox_inches="tight")
    plt.close(fig)


def headline_trend(d, s):
    x = d.loc["2015-01-01":]
    fig, ax = plt.subplots(figsize=(9, 4.6))
    ax.plot(x.index, x.headline_yoy, color=BLUE, lw=2.2)
    ax.plot(x.index, x.food_yoy, color=ORANGE, lw=1.6)
    ax.plot(x.index, x.core_yoy, color=GREEN, lw=1.6)
    last = x.index[-1]
    for col, c, lab in [("headline_yoy", BLUE, "Headline"), ("food_yoy", ORANGE, "Food"), ("core_yoy", GREEN, "Core")]:
        ax.annotate(f"{lab} {x[col].iloc[-1]:.1f}%", (last, x[col].iloc[-1]), xytext=(6, 0),
                    textcoords="offset points", color=INK, fontsize=8.5, va="center")
        ax.plot(last, x[col].iloc[-1], "o", color=c, ms=5)
    top = x.headline_yoy.max()
    for dt, label in EVENTS.items():
        ax.axvline(pd.Timestamp(dt), color=MUTED, lw=0.8, ls=":")
        ax.text(pd.Timestamp(dt), top * 1.02, label, fontsize=7, color=MUTED, ha="center", va="bottom")
    ax.set_ylim(0, top * 1.22); ax.set_xlim(x.index[0], last + pd.DateOffset(months=14))
    ax.set_ylabel("Year-on-year change (%)")
    _finish(fig, ax, f"Inflation has fallen from {s['peak_yoy']:.1f}% to {s['headline_yoy']:.1f}%, but food is rising again",
            "Headline, food and core CPI, year-on-year %", "01_headline_trend.png")


def january_anomaly(d, s):
    m = d.headline_mom[d.index.month == 1].loc["2015":]
    fig, ax = plt.subplots(figsize=(9, 4.2))
    cols = [ORANGE if v < 0 else BLUE for v in m]
    ax.bar(m.index.year, m.values, color=cols, width=0.65)
    ax.axhline(0, color=INK, lw=0.8)
    for yr, v in m.items():
        ax.text(yr.year, v + (0.15 if v >= 0 else -0.15), f"{v:+.1f}", ha="center",
                va="bottom" if v >= 0 else "top", fontsize=8, color=INK)
    ax.set_ylabel("January month-on-month change (%)"); ax.set_xticks(m.index.year)
    ax.set_ylim(-3.8, 3.4)
    _finish(fig, ax, "The published index fell ~2.8% in both January 2025 and January 2026",
            "All-items CPI, change from December to January. It rose in every January from 2015 to 2024.",
            "02_january_anomaly.png")


def drivers(c, s):
    c = c.head(8).iloc[::-1]
    fig, ax = plt.subplots(figsize=(9, 4.4))
    ax.barh(c.division, c.contribution_pp, color=BLUE, height=0.62)
    for i, (v, sh) in enumerate(zip(c.contribution_pp, c.share_of_inflation_pct)):
        ax.text(v + 0.1, i, f"{v:.1f} pp  ({sh:.0f}%)", va="center", fontsize=8.5, color=INK)
    ax.set_xlim(0, c.contribution_pp.max() * 1.3); ax.grid(axis="y", visible=False)
    ax.set_xlabel("Contribution to headline inflation (percentage points)")
    _finish(fig, ax, "Food and eating out account for two-thirds of inflation",
            f"Approximate contribution by CPI division, {s['latest_month']} vs a year earlier", "03_drivers.png")


def wage(s):
    labels = ["₦30,000 (Apr 2019)\nin Jul 2024 prices", "₦70,000 (Jul 2024)\nin Jul 2024 prices",
              f"₦70,000 (Jul 2024)\nin {s['latest_month']} prices"]
    vals = [s["wage_30k_2019_in_jul2024_money"], MIN_WAGE_2024, s["wage_70k_now_in_jul2024_money"]]
    fig, ax = plt.subplots(figsize=(9, 4.4))
    ax.bar(labels, vals, color=[GREY, BLUE, ORANGE], width=0.55)
    for i, v in enumerate(vals):
        ax.text(i, v + 1500, f"₦{v:,.0f}", ha="center", fontsize=10, color=INK, fontweight="bold")
    ax.set_ylim(0, 95000); ax.grid(axis="x", visible=False); ax.set_ylabel("Monthly value, constant prices (₦)")
    _finish(fig, ax, "The ₦70,000 minimum wage now buys what about ₦48,000 did in July 2024",
            "Statutory minimum wage deflated with the national CPI. Wage dates are assumptions (see config).", "04_minimum_wage.png")


def outlook(d, f, s):
    x = d.loc["2024-01-01":].headline_yoy
    fig, ax = plt.subplots(figsize=(9, 4.6))
    ax.plot(x.index, x.values, color=BLUE, lw=2.2)
    for scen, c, ls in [("January dip repeats", GREEN, "-"), ("No January dip", ORANGE, "--")]:
        g = f[f.scenario == scen]
        ax.plot(pd.concat([pd.Series([x.index[-1]]), g.date]), [x.iloc[-1]] + list(g.forecast_yoy), color=c, lw=2, ls=ls)
        ax.fill_between(g.date, g.low_80, g.high_80, color=c, alpha=0.10, lw=0)
        off = 0.9 if scen == "No January dip" else -0.9
        ax.text(g.date.iloc[-1] + pd.Timedelta(days=12), g.forecast_yoy.iloc[-1] + off, scen, fontsize=8.5, color=INK, va="center")
    ax.axvline(x.index[-1], color=MUTED, lw=0.8, ls=":")
    ax.set_xlim(x.index[0], pd.Timestamp("2027-08-01")); ax.set_ylim(0, 40)
    ax.xaxis.set_major_locator(matplotlib.dates.YearLocator()); ax.xaxis.set_major_formatter(matplotlib.dates.DateFormatter("%Y"))
    ax.set_ylabel("Year-on-year change (%)")
    _finish(fig, ax, "Inflation is likely near 12% by March 2027",
            "Two scenarios for year-on-year %, depending on whether the January index dip repeats. Bands: 80% backtest errors, probably too narrow.", "05_outlook.png")


def urban_rural(d, s):
    x = d.loc["2019-01-01":]
    fig, ax = plt.subplots(figsize=(9, 4.2))
    ax.plot(x.index, x.urban_yoy, color=BLUE, lw=2); ax.plot(x.index, x.rural_yoy, color=ORANGE, lw=2)
    for col, c, lab in [("urban_yoy", BLUE, "Urban"), ("rural_yoy", ORANGE, "Rural")]:
        ax.annotate(f"{lab} {x[col].iloc[-1]:.1f}%", (x.index[-1], x[col].iloc[-1]), xytext=(6, 0),
                    textcoords="offset points", fontsize=8.5, color=INK, va="center")
    ax.set_xlim(x.index[0], x.index[-1] + pd.DateOffset(months=10)); ax.set_ylabel("Year-on-year change (%)")
    _finish(fig, ax, "Rural households faced slightly lower inflation than urban ones for most of 2020-2026",
            "All-items CPI, year-on-year %, urban vs rural", "06_urban_rural.png")


def main():
    FIGURES.mkdir(exist_ok=True)
    s = json.loads((PROCESSED / "summary.json").read_text())
    d = pd.read_csv(PROCESSED / "headline_monthly.csv", parse_dates=["date"]).set_index("date")
    c = pd.read_csv(PROCESSED / "contributions_latest.csv")
    f = pd.read_csv(PROCESSED / "forecast_yoy.csv", parse_dates=["date"])
    headline_trend(d, s); january_anomaly(d, s); drivers(c, s); wage(s); outlook(d, f, s); urban_rural(d, s)


if __name__ == "__main__":
    main()
