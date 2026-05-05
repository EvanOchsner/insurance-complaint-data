# Provenance

Source-of-record details for the WA OIC IFCA + AR datasets. Outputs in `wa_oic/output/` are reproducible by re-running the two scripts. Re-runs may show small deltas as OIC amends or appends records.

## Sources (URLs verified live 2026-05-04)

### IFCA notice PDFs

Base path: `https://www.insurance.wa.gov/sites/default/files/{YYYY}-{MM}/`

| Year | Filename | Status |
|---|---|---|
| 2025 | `2025-notices-of-potential-lawsuits.pdf` (`/2025-03/`) | online |
| 2026 | `2026-notices-of-potential-lawsuits.pdf` (`/2026-04/`) | online (partial year) |
| 2008-2024 | various | **redirect to landing page (file removed by OIC)** |

The IFCA landing page (<https://www.insurance.wa.gov/laws-rules/insurance-fair-conduct-act-ifca>) is the canonical resolver if the URL pattern shifts — re-resolve there.

### Annual Report PDFs

| Year | URL |
|---|---|
| 2020 | <https://www.insurance.wa.gov/sites/default/files/2024-09/oic-annual-report-2020-final-web.pdf> |
| 2021 | <https://www.insurance.wa.gov/sites/default/files/2024-09/OIC-annual-report-2021.pdf> |
| 2022 | <https://www.insurance.wa.gov/sites/default/files/2024-09/oic-annual-report-2022.pdf> |
| 2023 | <https://www.insurance.wa.gov/sites/default/files/2024-12/oic-annual-report-2023.pdf> |
| 2024 | <https://www.insurance.wa.gov/sites/default/files/2025-07/OIC-annual-report-2024-final.pdf> |

Landing: <https://www.insurance.wa.gov/oic-annual-reports>.

### User-Agent quirk

The OIC's Varnish CDN cache returns **HTTP 403** for unrecognized User-Agents. The downloader sends a browser-like Chrome UA:

```
Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36
```

This is a workaround for the cache, not stealth — we identify ourselves transparently in this file and in the project's README. The manifest records both the wire-UA and our `project_tag` for traceability.

## First-run snapshot — 2026-05-04

Total downloaded: 6.5 MB across 7 PDFs.

### IFCA PDFs (2 files)

| Year | Bytes | SHA-256 (first 16 chars) |
|---:|---:|---|
| 2025 |   883,520 | `e15d686d14c11069…` |
| 2026 | 1,835,578 | `c88650a269e0ecf7…` |

### Annual Report PDFs (5 files)

| Year | Bytes | SHA-256 (first 16 chars) |
|---:|---:|---|
| 2020 | 1,086,513 | `74ebc0896059c41d…` |
| 2021 |   636,268 | `87188b42a5cf5a13…` |
| 2022 |   813,119 | `2bca2b7741cc8b26…` |
| 2023 |   764,460 | `b8bfd902dfedbf6c…` |
| 2024 |   528,500 | `e842f492f04df437…` |

The authoritative manifest is `interim/manifest.json` — the table above is a human-readable copy.

## Output files

| File | Rows | What |
|---|---:|---|
| `wa_ifca_notices.parquet` | 1,941 | Per-notice rows (1,439 from 2025 + 502 from 2026 partial) |
| `wa_ifca_notices_yearly.parquet` | 26 | Per-(year, line) totals + per-year `ALL` row |
| `wa_complaints_state_yearly.parquet` | 5 | One row per AR year (2020-2024) |
| `run_log.txt` | (append-only) | Per-run timestamps + sanity tables |

## Run history

### 2026-05-04T19:43Z

- 2 IFCA + 5 AR PDFs downloaded successfully (Content-Type and `%PDF-` magic verified).
- IFCA parsing: 1,941 notices total. Sequence check passed for both years (no gaps in IFCA #).
  - 2025: 1,439 notices, IFCA # 0001-1439, complete.
  - 2026: 502 notices, IFCA # 0001-0502, complete (partial calendar year).
- AR parsing: 5 years extracted.
  - 2020: 6,678 complaints / $45.4M
  - 2021: 7,705 / $15.7M
  - 2022: 8,603 / $26.9M
  - 2023: 9,441 / $27.4M
  - 2024: 10,127 / $27.4M
- Headline trends:
  - Regulator complaint volume rose 52% from 2020 to 2024.
  - 2025 IFCA notices skew P&C (Property+Homeowners+Liability+Title = 661 = 46%) and Auto-related (Auto+UIM+UM+PIP = 531 = 37%).

Append future runs below this line.
