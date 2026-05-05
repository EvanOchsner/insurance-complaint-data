# Wisconsin OCI — complaints by type of insurance, by year

Per-line annual complaint counts from the Wisconsin Office of the Commissioner of Insurance (OCI) annual *Wisconsin Insurance Report* (WIR). Extracted from Table II ("Complaints Filed By Type of Insurance") in each WIR's Division of Market Regulation and Enforcement section.

Workload counts only — WI does NOT publish per-company complaint indexes in PDF form (a separate interactive tool exists, out of scope for v1). Categorically the same metric class as CO DOI's `co_workload_yearly` and VA SCC's `va_complaints_yearly`: complaints received by line, not regulator findings or per-company indexes.

## What's in this folder

| Path | What it is |
|---|---|
| `output/wi_complaints_yearly.parquet` (and `.csv`) | **Headline.** One row per `(data_year, line)`, canonical (= latest report's value). 84 rows = 6 years × 14 lines. |
| `output/wi_complaints_all_versions.parquet` (and `.csv`) | Audit trail — every report's value for every `(data_year, line)`. Useful when OCI revises prior-year numbers. |
| `output/run_log.txt` | Per-run extraction log. |
| `scripts/01_download.py` | Fetch 5 WIR PDFs at predictable URLs. |
| `scripts/02_parse.py` | Locate Table II in each PDF; extract rows; canonicalize via latest-report-wins. |
| `interim/files/WIR_{year}.pdf` | Raw PDFs. **Gitignored.** Total ~66 MB across 5 reports. |
| `interim/manifest.json` | Per-file SHA-256 + Last-Modified + fetched-at. |
| `METHODOLOGY.md` | Line slugs, canonicalization rules, audit-table semantics. |
| `PROVENANCE.md` | Source URLs, per-file hashes, Table II page numbers per year. |

## How to load

```python
import polars as pl

# Canonical time series:
df = pl.read_parquet("wi_oci/output/wi_complaints_yearly.parquet")
df.filter(pl.col("line") == "grand_total").sort("data_year")

# Per-line trend:
df.filter(pl.col("line").is_in(["auto", "homeowners_tenants_farmowners", "group_health"])).sort(["data_year", "line"])

# Audit cross-version:
all_v = pl.read_parquet("wi_oci/output/wi_complaints_all_versions.parquet")
all_v.filter(pl.col("data_year") == 2020).sort(["line", "report_year"])
```

## How to re-run

```
python3 wi_oci/scripts/01_download.py     # ~30 s (5 PDFs, last is 44 MB)
python3 wi_oci/scripts/02_parse.py        # < 30 s
```

## Headline caveats

1. **Workload signal, not regulator finding.** Counts of complaints filed; the WIR doesn't publish per-line confirmed-vs-not dispositions. Don't fold these into the canonical 4-bucket outcome taxonomy.
2. **Revisions across reports.** OCI sometimes adjusts prior-year values in later reports (e.g., 2020 grand total was 2,588 in the 2020 report and 2,589 in the 2021 report — likely a late-arriving complaint reclassification). Canonical = latest report's value. The audit parquet preserves every version.
3. **2021 report's Table II is laid out beside Table I** in the source PDF. pdfplumber's text extraction interleaves the two tables, so the 2021 report's Table II contributed only 7 of 14 lines per year. The canonical output cross-fills from adjacent reports (2020 and 2022 cover everything), so the headline parquet is complete.
4. **A complaint may involve more than one type of insurance.** Per OCI footnote, sub-line totals don't sum to the Total Property and Casualty / Total Accident and Health rows — a single complaint counted in multiple coverage types appears in multiple sub-lines. Use the OCI-published total rows (`total_*`) rather than summing sub-lines.
5. **No per-company breakdown.** Per-company data lives in OCI's interactive lookup tool (separate URL); not in v1.

## Headline numbers (sanity check)

From the 2026-05-04 build:

| Year | Grand Total | A&H Total | P&C Total | Life | Source report |
|---:|---:|---:|---:|---:|---|
| 2019 | 2,807 | 1,080 | 1,299 | 428 | WIR_2020 |
| 2020 | 2,588 | 1,038 | 1,196 | 354 | WIR_2020 / 2021 |
| 2021 | 2,121 | 858 | 960 | 303 | WIR_2022 |
| 2022 | 2,467 | 832 | 1,328 | 307 | WIR_2023 |
| 2023 | 2,878 | 939 | 1,554 | 385 | WIR_2024 |
| 2024 | 3,219 | 1,049 | 1,733 | 437 | WIR_2024 |
