# Provenance

Source-of-record details for the CA CDI complaint dataset. Output files in `ca_cdi/output/` are reproducible by re-running the two scripts. The 14 source PDFs live in `interim/` (gitignored) with SHA-256 hashes recorded in `interim/manifest.json`.

## Source URLs (all verified live 2026-05-04)

### Annual Reports of the Insurance Commissioner

Base: `https://www.insurance.ca.gov/0400-news/0200-studies-reports/0700-commissioner-report/upload/`

| Year | Filename |
|---|---|
| 2020 | `2020-Annual-Report-of-the-Insurance-Commissioner.pdf` |
| 2021 | `2021Annual-Report-of-the-Insurance-Commissioner.pdf` (note: no hyphen between "2021" and "Annual") |
| 2022 | `2022-Annual-Report-of-the-Insurance-Commissioner.pdf` |
| 2023 | `2023-Annual-Report-of-the-Insurance-Commissioner.pdf` |
| 2024 | `2024-Annual-Report-of-the-Commissioner.pdf` (note: word "Insurance" dropped) |

### Consumer Complaint Studies

Base: `https://www.insurance.ca.gov/01-consumers/120-company/03-concmplt/upload/`

| Study Year | Auto | Home | Life |
|---|---|---|---|
| 2023 | `2023-Consumer-Complaint-Study-Auto.pdf` | `…-Home.pdf` | `…-Life.pdf` |
| 2024 | `2024-Consumer-Complaint-Study-Auto.pdf` | `…-Home.pdf` | `…-Life.pdf` |
| 2025 | `2025-Consumer-Complaint-Study-Auto.pdf` | `…-Home.pdf` | `…-Life.pdf` |

User-Agent: `insurance-complaint-rates/1.0 (research; contact: evan.ochsner@gmail.com)`

**Important quirk**: the CDI server returns `HTTP 200` with a generic HTML "page not found" body for every URL it doesn't recognize. The downloader probes `Content-Type: application/pdf` *and* checks the `%PDF-` magic bytes after download. URL probes that rely only on HTTP status codes will give false positives.

## First-run snapshot — 2026-05-04T18:11:51Z

Total downloaded: 16.6 MB across 14 PDFs.

### Annual Reports

| Year | Bytes | SHA-256 (first 16 chars) |
|---:|---:|---|
| 2020 | 3,884,765 | `149e60cc08956ad5…` |
| 2021 | 4,606,965 | `0e5905a5f356f120…` |
| 2022 | 2,196,082 | `ffc366fcc594a7d3…` |
| 2023 | 2,413,033 | `50d93b245efac95a…` |
| 2024 | 2,227,506 | `4a2474ef432d92e7…` |

### Composite Studies

| Study | Bytes | SHA-256 (first 16 chars) |
|---|---:|---|
| 2023-auto | 185,747 | `ec728cf387272589…` |
| 2023-home | 155,043 | `bdf6fc70a1699bad…` |
| 2023-life | 152,832 | `69bfd0ad7aae993f…` |
| 2024-auto | 132,188 | `f9859cc6a16b198f…` |
| 2024-home | 132,638 | `d8cf0c97a73aa88b…` |
| 2024-life | 132,893 | `5e555f312b0fd5f3…` |
| 2025-auto | 126,216 | `2abfb1886c09fecd…` |
| 2025-home | 128,222 | `f93658fd705d3e52…` |
| 2025-life | 127,652 | `4277b5e8eff403d0…` |

The authoritative manifest is `interim/manifest.json` — the table above is a human-readable copy.

## Output files

After a successful run, `output/` contains:

| File | Rows | What |
|---|---:|---|
| `ca_complaints_state_yearly.parquet` | 5 | One row per AR year (2020-2024). |
| `ca_complaints_state_by_line_pct.parquet` | 64 | `(year, coverage_type, percentage)` for 8 lines × 8 years (2017-2024), deduped to most-recent AR per (year, coverage_type). |
| `ca_complaints_company_yearly.parquet` | 951 | Per-company panel after deduplication. |
| `ca_complaints_yearly_justified.parquet` | 15 | 5 years × 3 lines headline aggregate. |
| `run_log.txt` | (append-only) | Sanity tables and timestamps per run. |

## Run history

### 2026-05-04T18:22:03Z

- All 14 PDFs downloaded successfully (Content-Type and `%PDF-` magic verified).
- 5 ARs parsed: extracted `Complaint Cases Closed` for each — 44,535 / 41,181 / 44,712 / 56,827 / 62,002.
- 9 composite studies parsed: each yielded 150 row-data points (50 companies × 3 data years).
- After dedup: 951 rows in `company_yearly`; 15 rows in `yearly_justified` (5 years × 3 lines × 50 companies each).
- Headline metric: `justified_per_100k_exposure` for the home insurance line jumped from 2.80 (2020) to 10.58 (2024).

Append future runs below this line.
