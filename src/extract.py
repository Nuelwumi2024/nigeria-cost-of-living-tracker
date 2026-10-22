"""Parse the NBS CPI workbook into tidy tables.

The workbook is laid out for humans: year in column A on the first row of each
year only, month names in column B, one column per index. This module turns it
into long-format data (one row per month x series) and checks it.
"""
from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from config import PROCESSED, RAW_XLSX

MONTHS = {m: i for i, m in enumerate(
    ["jan", "feb", "mar", "apr", "may", "jun", "jul", "aug", "sep", "oct", "nov", "dec"], 1)}


def _clean_name(name: object) -> str:
    return re.sub(r"\s+", " ", str(name).replace("\n", " ")).strip()


def _month_number(value: object) -> int | None:
    if not isinstance(value, str):
        return None
    return MONTHS.get(value.strip().lower()[:3])


def parse_index_sheet(raw: pd.DataFrame, name_row: int) -> pd.DataFrame:
    """Wide index sheet (rows = months) -> long: date, series, value."""
    names = {c: _clean_name(raw.iat[name_row, c]) for c in range(2, raw.shape[1])
             if isinstance(raw.iat[name_row, c], str)}
    # columns whose label is a change % rather than an index level
    names = {c: n for c, n in names.items() if "(%)" not in n}

    year = None
    records = []
    for r in range(name_row + 1, raw.shape[0]):
        y, m = raw.iat[r, 0], _month_number(raw.iat[r, 1])
        if isinstance(y, pd.Timestamp):
            y = y.year
        if pd.notna(y) and str(y).strip().replace(".0", "").isdigit():
            year = int(float(y))
        if m is None or year is None:
            continue
        date = pd.Timestamp(year=year, month=m, day=1)
        for c, n in names.items():
            v = pd.to_numeric(raw.iat[r, c], errors="coerce")
            if pd.notna(v):
                records.append((date, n, float(v)))
    return pd.DataFrame(records, columns=["date", "series", "index_value"])


def load_workbook(path: Path = RAW_XLSX) -> dict[str, pd.DataFrame]:
    xl = pd.ExcelFile(path)
    t2 = xl.parse("Table2", header=None)
    t3 = xl.parse("Table3", header=None)
    t4 = xl.parse("Table4", header=None)
    national = parse_index_sheet(t2, name_row=1)
    urban = parse_index_sheet(t3, name_row=1)
    rural = parse_index_sheet(t4, name_row=1)
    urban["geography"], rural["geography"], national["geography"] = "Urban", "Rural", "National"
    weights = _weights(t2)
    reported = _reported_headline(xl.parse("Table1", header=None))
    return {"national": national, "urban": urban, "rural": rural,
            "weights": weights, "reported": reported}


def _weights(t2: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for c in range(2, t2.shape[1]):
        n = t2.iat[1, c]
        w = pd.to_numeric(t2.iat[2, c], errors="coerce")
        if isinstance(n, str) and pd.notna(w) and "(%)" not in n:
            rows.append((_clean_name(n), float(w)))
    return pd.DataFrame(rows, columns=["series", "weight"])


def _reported_headline(t1: pd.DataFrame) -> pd.DataFrame:
    """NBS's own published headline m/m and y/y, used to validate our recomputation."""
    out, year = [], None
    for r in range(3, t1.shape[0]):
        y, m = t1.iat[r, 0], _month_number(t1.iat[r, 1])
        if pd.notna(y) and str(y).strip().replace(".0", "").isdigit():
            year = int(float(y))
        if m is None or year is None:
            continue
        out.append((pd.Timestamp(year=year, month=m, day=1),
                    pd.to_numeric(t1.iat[r, 4], errors="coerce"),
                    pd.to_numeric(t1.iat[r, 5], errors="coerce")))
    return pd.DataFrame(out, columns=["date", "nbs_mom_pct", "nbs_yoy_pct"])


def run() -> dict[str, pd.DataFrame]:
    PROCESSED.mkdir(parents=True, exist_ok=True)
    tables = load_workbook()
    long = pd.concat([tables["national"], tables["urban"], tables["rural"]], ignore_index=True)
    long.to_csv(PROCESSED / "cpi_long.csv", index=False)
    tables["weights"].to_csv(PROCESSED / "series_weights.csv", index=False)
    tables["reported"].to_csv(PROCESSED / "nbs_reported_headline.csv", index=False)
    return tables


if __name__ == "__main__":
    t = run()
    n = t["national"]
    print(f"national: {n.date.min():%b %Y} to {n.date.max():%b %Y}, {n.series.nunique()} series, {len(n):,} rows")
