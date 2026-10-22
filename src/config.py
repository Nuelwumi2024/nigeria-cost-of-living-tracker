"""Paths, assumptions and event dates. Every business assumption lives here."""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_XLSX = ROOT / "data" / "raw" / "nbs_cpi_september_2026.xlsx"
PROCESSED = ROOT / "data" / "processed"
FIGURES = ROOT / "figures"
POWERBI = ROOT / "powerbi"

SOURCE_URL = "https://microdata.nigerianstat.gov.ng/index.php/catalog/154"
SOURCE_NOTE = "National Bureau of Statistics, Consumer Price Index and Inflation (NGA-NBS-CPI), September 2026 release, base 2024 = 100"

# The NBS rebased the CPI (2024 base, COICOP 2018, 934 varieties). In the published
# series the all-items index falls ~2.8% month-on-month in January 2025 AND January 2026,
# after no January from 1996 to 2024 fell by more than 1%. The cause is not documented in the
# workbook, so these months are flagged rather than silently "fixed".
JANUARY_DIPS = ["2025-01-01", "2026-01-01"]

# Statutory national minimum wage (NGN per month). Assumption inputs, not NBS data.
MIN_WAGE_2019 = 30_000   # Minimum Wage Act 2019
MIN_WAGE_2024 = 70_000   # Minimum Wage (Amendment) Act, July 2024
MIN_WAGE_2019_DATE = "2019-04-01"
MIN_WAGE_2024_DATE = "2024-07-01"

# Dated policy events used only as chart annotations.
EVENTS = {
    "2023-06-01": "Subsidy removal &\nnaira float",
    "2025-01-01": "CPI rebased",
}

# Division names as published -> short labels used in charts
DIVISION_LABELS = {
    "Food And Non-Alcoholic Beverages": "Food & beverages",
    "Alcoholic Beverages, Tobacco And Narcotics": "Alcohol & tobacco",
    "Clothing And Footwear": "Clothing",
    "Housing, Water, Electricity, Gas And Other Fuels": "Housing & utilities",
    "Furnishings, Household Equipment And Routine Household Maintenance": "Household goods",
    "Health.": "Health",
    "Transport": "Transport",
    "Information And Communication": "Communication",
    "Recreation, Sport And Culture": "Recreation",
    "Education Services": "Education",
    "Restaurants And Accomodation Services": "Restaurants & hotels",
    "Insurance and Financial Services": "Insurance & finance",
    "Personal Care, Social Protection And Miscellaneous Goods And Services": "Personal care & misc",
}
