# Power BI build guide

This folder holds a ready-to-load model. It does not contain a `.pbix` file.

## Load
1. Power BI Desktop → Get data → Text/CSV: `dim_date.csv`, `dim_series.csv`, `fact_cpi_monthly.csv`, `fact_outlook.csv`.
2. Model view: `dim_date[date]` 1→* `fact_cpi_monthly[date]`; `dim_series[series]` 1→* `fact_cpi_monthly[series]`. Mark `dim_date` as the date table.
3. Add a what-if parameter named `Amount` (10,000 to 500,000, step 5,000).
4. Paste the measures from [`measures.dax`](measures.dax).

## Suggested pages
| Page | Visuals |
|---|---|
| Overview | Cards: Headline YoY (latest), Food YoY (latest). Line: YoY % by month for All Items, Food, Core. Slicer: geography. |
| Drivers | Bar: Contribution pp by division (`dim_series[label]`, filter `series_group = Division`). |
| Your naira | Slicer on start month + `Amount` parameter → card `Amount in Today's Naira`. |
| Outlook | Line + band from `fact_outlook` by scenario. Add a text banner using `January Dip Flag`. |
| Data notes | The January anomaly bar chart and the limitations from the README. |

Colour-blind-safe palette used in the charts: `#0072B2`, `#D55E00`, `#009E73`, grey `#8a8f98`.

> The DAX measures have not been validated in Power BI Desktop yet; check them against the Python results (see the main README) when you build the report.
