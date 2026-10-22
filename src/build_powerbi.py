"""Export a Power BI-ready star schema (CSV) from the processed CPI data."""
from __future__ import annotations

import pandas as pd

import metrics as mx
from config import DIVISION_LABELS, JANUARY_DIPS, POWERBI, PROCESSED

GROUPS = {"All Items": "Headline", "Food": "Component", "Farm Produce": "Component", "Energy": "Component",
          "Services": "Component", "Goods": "Component", "Imported Food": "Component",
          "Core Index (All Items Less Farm Produce And Energy)": "Component",
          "All Items Less Farm Produce": "Component"}


def main() -> None:
    POWERBI.mkdir(exist_ok=True)
    long = pd.read_csv(PROCESSED / "cpi_long.csv", parse_dates=["date"])
    weights = pd.read_csv(PROCESSED / "series_weights.csv")

    parts = []
    for (series, geo), g in long.groupby(["series", "geography"]):
        idx = g.set_index("date").index_value.sort_index()
        parts.append(pd.DataFrame({"date": idx.index, "series": series, "geography": geo,
                                   "index_value": idx.values, "yoy_pct": mx.yoy(idx).values,
                                   "mom_pct": mx.mom(idx).values}))
    fact = pd.concat(parts, ignore_index=True)
    fact["january_dip_flag"] = fact.date.isin(pd.to_datetime(JANUARY_DIPS)) & (fact.series == "All Items")
    fact.to_csv(POWERBI / "fact_cpi_monthly.csv", index=False, float_format="%.4f")

    dim_series = weights.assign(
        label=lambda d: d.series.map(DIVISION_LABELS).fillna(d.series),
        series_group=lambda d: d.series.map(GROUPS).fillna(
            d.series.map(lambda s: "Division" if s in DIVISION_LABELS else "Other")))
    dim_series.to_csv(POWERBI / "dim_series.csv", index=False)

    dates = pd.date_range(long.date.min(), long.date.max(), freq="MS")
    pd.DataFrame({"date": dates, "year": dates.year, "month_no": dates.month,
                  "month": dates.strftime("%b"), "year_month": dates.strftime("%Y-%m"),
                  "quarter": "Q" + dates.quarter.astype(str)}).to_csv(POWERBI / "dim_date.csv", index=False)

    pd.read_csv(PROCESSED / "forecast_yoy.csv").to_csv(POWERBI / "fact_outlook.csv", index=False)
    print(f"fact rows: {len(fact):,}; series: {len(dim_series)}; dates: {len(dates)}")


if __name__ == "__main__":
    main()
