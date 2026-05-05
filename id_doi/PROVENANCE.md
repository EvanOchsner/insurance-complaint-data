# Provenance — Idaho DOI Consumer Complaint Comparison Tables

## Source

- **Publisher:** Idaho Department of Insurance, Consumer Services Division.
- **Landing:** <https://doi.idaho.gov/information/public/reports/complaint-index/>

The data lives as a single embedded HTML table on the landing page (no separate per-year PDFs).

## First build (2026-05-04)

| Field | Value |
|---|---|
| `fetched_at` | 2026-05-05T02:52:37Z |
| Source size | 283,199 bytes |
| SHA-256 | `8da084b333a241fff5be8c45743085d3cece1e82cfe5c0f3cad0e60439146009` |
| User-Agent | `insurance-complaint-rates/1.0 (research; contact: evan.ochsner@gmail.com)` |
| Years parsed | 2018, 2019, 2020 |
| Lines parsed | Auto, Group Accident/Health, Homeowner, Individual Accident/Health |
| Per-company rows | 240 |

## File schema (per row, after parse)

| Field | Type | Notes |
|---|---|---|
| `year` | i32 | Data year |
| `line` | str | One of `auto`, `group_health`, `homeowners`, `individual_health` |
| `company_name` | str | As printed |
| `premium` | f64 | Idaho written premium for the line, USD |
| `market_share` | f64 | Fraction (e.g. 0.12 = 12%) |
| `complaints` | i64 | Complaint count |
| `complaint_index` | f64 nullable | Null when source prints "DNC" |

## Source quirks

- 5 rows in the 2018 Individual Accident/Health slice have swapped Complaints/Index columns at source. The parser detects swap candidates per row and corrects them inline. Run log records the count.

## Run log

The parser appends to `output/run_log.txt`. Sample first run:

```
=== run started 2026-05-05T02:52:38+00:00 ===
Parsed 240 data rows from landing.html
NOTE: corrected 5 rows where Complaints/Index columns were swapped at source
Wrote id_complaints_company_yearly.parquet (240 rows)
Wrote id_complaints_yearly.parquet (12 rows)
=== run completed 2026-05-05T02:53:33+00:00 ===
```
