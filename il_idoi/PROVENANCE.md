# Provenance — Illinois IDOI Consumer Complaint Ratio Reports

## Source

- **Publisher:** Illinois Department of Insurance, Office of Consumer Health Insurance.
- **Landing:** <https://idoi.illinois.gov/reports/consumer-complaint.html>
- **PDF base:** `https://idoi.illinois.gov/content/dam/soi/en/web/insurance/reports/reports/`

URL stems differ across years (no stable convention). The downloader hardcodes the per-year stem since IL has used 4 different naming patterns over the 5 years.

## First build (2026-05-04)

| Field | Value |
|---|---|
| `discovered_at` | 2026-05-05T02:59:08Z |
| Files | 5 PDFs (2018, 2019, 2020, 2023, 2024) |
| Polite delay | 1 request / second |
| User-Agent | `insurance-complaint-rates/1.0 (research; contact: evan.ochsner@gmail.com)` |

Per-file SHA-256:

```
2018.pdf  315,202 bytes  sha256=73786267b4a8…  (URL: 2018-complaint-ratios.pdf)
2019.pdf  162,057 bytes  sha256=0fae6be78eab…  (URL: 2019-complaint-ratios.pdf)
2020.pdf  255,374 bytes  sha256=62883854591e…  (URL: 2020-complaints-ratio-report.pdf)
2023.pdf  407,497 bytes  sha256=c7a8a0be424e…  (URL: 2023-complaint-ratio-report.pdf)
2024.pdf  249,598 bytes  sha256=d83df09db9e8…  (URL: 2024-complaint-ratio-report.pdf)
```

## Coverage gaps

2021 and 2022 do not have consolidated ratio-report PDFs posted. IL appears to have published only "summary" reports for those years (state-level counts, no per-company), which would not produce comparable per-company ratio data.

## File schema (per row, after parse)

| Field | Type | Notes |
|---|---|---|
| `year` | i32 | Data year |
| `line` | str | Canonical line slug |
| `naic_code` | str nullable | Present only for 2018 (cocode column) |
| `company_name` | str | As printed |
| `complaints` | i64 | Complaint count |
| `premium` | f64 nullable | Earned premium (P&C, USD) OR policies-in-force / members for Life/HMO |
| `market_share` | f64 nullable | 2018 only |
| `complaint_share` | f64 nullable | 2018 only |
| `ratio` | f64 nullable | The published ratio |
| `ratio_type` | str | `share_of_share` (2018) or `per_million_ep` (2019+) |
| `reason_*` columns | i64 nullable | Not extracted in v1 |
| `source_file` | str | Filename of source PDF |

## Run log

The parser appends to `output/run_log.txt`. Sample first run:

```
=== run started 2026-05-05T03:03:39+00:00 ===
  2018.pdf (old layout): 1911 rows, 361 non-row lines skipped
  2019.pdf (new layout): 191 rows, 167 non-row lines skipped
  2020.pdf (new layout): 175 rows, 134 non-row lines skipped
  2023.pdf (new layout): 261 rows, ...
  2024.pdf (new layout): 277 rows, ...
Wrote il_complaints_company_yearly.parquet (2,671 rows)
Wrote il_complaints_yearly.parquet (29 rows)
=== run completed ... ===
```
