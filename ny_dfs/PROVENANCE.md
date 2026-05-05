# Provenance

Source-of-record details for the NY DFS auto + health complaint datasets. Output files in `ny_dfs/output/` are reproducible by re-running the two scripts. Re-runs may show small deltas as DFS amends past records.

## Sources (URLs verified live 2026-05-04)

### Auto stream

| Field | Value |
|---|---|
| Source | New York DFS, via Open Data NY (Socrata) |
| Dataset name | Automobile Insurance Company Complaint Rankings: Beginning 2009 |
| Dataset 4×4 ID | `h2wd-9xfe` |
| Resource API | <https://data.ny.gov/resource/h2wd-9xfe.json> |
| Metadata API | <https://data.ny.gov/api/views/h2wd-9xfe.json> |
| Landing page | <https://data.ny.gov/Government-Finance/Automobile-Insurance-Company-Complaint-Rankings-Be/h2wd-9xfe> |
| Authentication | Anonymous (one Socrata GET) |

### Health stream

| Field | Value |
|---|---|
| Source | NY DFS, *Consumer Guide to Health Insurers* (annual PDF) |
| URL pattern | `https://www.dfs.ny.gov/consumers/health_insurance/guide_{guide_year}` |
| Landing page | <https://www.dfs.ny.gov/consumers/health_insurance/health_insurance_complaint_rankings> |
| Format | PDF (~1-1.7 MB each, 90+ pages) |
| Year mapping | guide year YYYY reports on calendar-year YYYY-1 data |

User-Agent: `insurance-complaint-rates/1.0 (research; contact: evan.ochsner@gmail.com)`

## First-run snapshot — 2026-05-04

### Auto

- Rows pulled: 2,461
- Server `viewLastModified` (epoch): 1775249846
- `filing_year` range: 2009 – 2024 (16 years)

### Health PDFs (10 files, 12.8 MB total)

| Guide year | Data year | Bytes | SHA-256 (first 16 chars) |
|---:|---:|---:|---|
| 2016 | 2015 | 1,569,470 | `60c4264b219562a1…` |
| 2017 | 2016 | 1,671,356 | `602bbde53edf62e1…` |
| 2018 | 2017 |   977,984 | `c6e8f3015bf999a7…` |
| 2019 | 2018 | 1,087,420 | `d87078e5b2e6985c…` |
| 2020 | 2019 | 1,167,670 | `66b10242434b3e57…` |
| 2021 | 2020 | 1,200,328 | `8d8c3e5aa5965907…` |
| 2022 | 2021 | 1,252,214 | `9f3d5c3a1f1d57f3…` |
| 2023 | 2022 | 1,204,659 | `d10c4f6203af965e…` |
| 2024 | 2023 | 1,599,559 | `091758c9b0b88efa…` |
| 2025 | 2024 | 1,089,273 | `4094607d97a7a40b…` |

The authoritative manifest is `interim/manifest.json` — the table above is a human-readable copy.

## Output files

| File | Rows | What |
|---|---:|---|
| `ny_auto_complaints_company_year.parquet` | 2,461 | Per-(filing_year, company) Socrata rows, typed |
| `ny_auto_complaints_yearly.parquet` | 16 | Statewide auto rollup; columns suffixed `_2yr` |
| `ny_health_complaints_company_year.parquet` | 688 | Per-(data_year, plan_type, plan_name) after dedup |
| `ny_health_complaints_yearly.parquet` | 30 | Per-(year, plan_type) rollup, 2015–2024 × 3 types |
| `run_log.txt` | (append-only) | Per-run timestamps + sanity tables |

The health pre-dedup row count is 1,012; after deduplicating on `(data_year, plan_type, plan_name)` keeping the most recent guide year, 688 rows remain. The deduplication is necessary because each Consumer Guide reprints the prior year's tables in a "previous year" appendix (e.g., the 2024 guide also has the 2022 tables).

## Run history

### 2026-05-04T19:29Z

- 1 Socrata GET + 10 PDF GETs; 0 failures.
- Auto parsed: 2,461 rows / 16 filing years (2009–2024).
- Health parsed: 1,012 raw rows from 78 page-tables across 10 PDFs → 688 deduped rows / 30 (year, plan_type) cells.
- Health row counts per page in the run log; 0 cases of "0 rows" from a complaints-table page (HMO appendix pages 11 sometimes return 0 rows because they're a layout artifact, not a real table — these are inconsequential).
- Headline trends:
  - Auto rolling-2-year upheld bottomed at 281 (2015–2016 — see anomaly note in METHODOLOGY) and recovered to 629 in 2024.
  - Health EPO/PPO upheld rose from 1,139 (2015) to 3,290 (2024) — the most striking signal.
  - Health HMO upheld is volatile (10 plans in 2015 → 7 plans in 2024).

Append future runs below this line.
