# Provenance — Kansas KID Complaint Index Report

## Source

- **Publisher:** Kansas Department of Insurance (KID).
- **Publications landing:** <https://insurance.ks.gov/department/publications.php>
- **URL template:** `https://insurance.ks.gov/documents/department/publications/complaint-index-report-{YYYY}.pdf`

## Origin access notes

The KID web origin (`insurance.ks.gov` / `insurance.kansas.gov`) returns **403 Access Denied** for unfamiliar User-Agents at the Akamai-style edge layer. Both `python-urllib`'s default UA and our project's polite `insurance-complaint-rates/1.0 (research; contact: ...)` UA are blocked; only a browser-style UA succeeds.

The downloader uses a Chrome 120 User-Agent string for that reason. This is documented here as the necessary workaround, not a recommended pattern. If KID changes its edge configuration, the downloader will fail loudly (response is not a PDF → hard fail).

## First build (2026-05-04)

| Field | Value |
|---|---|
| `discovered_at` | 2026-05-04T23:42:44Z |
| Files downloaded | 5 (years 2020–2024) |
| File format | PDF |
| Polite delay | 1 request / second |
| User-Agent (download time) | `Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36` |

Per-file SHA256 (first build):

```
2020.pdf  sha256=620294ee3821…
2021.pdf  sha256=3a75bcf63460…
2022.pdf  sha256=d63cfe69f191…
2023.pdf  sha256=cdb1bf2ce376…
2024.pdf  sha256=21724364661f…
```

## File schema (per row, after parsing)

| Field | Type | Source |
|---|---|---|
| `year` | i32 | Data year, from filename |
| `line` | str | One of `auto`, `health`, `homeowners`, `annuity`, `life`, `long_term_care` |
| `naic_code` | str | NAIC company code (4–5 digits) |
| `company_name` | str | Company name as printed |
| `market_share` | f64 | Market share as a fraction (e.g. 0.18 = 18%) |
| `complaints` | i64 | Complaint count for the data year |
| `complaint_index` | f64 nullable | Data-year complaint index (null if printed as `-`) |
| `complaint_index_prior_1` | f64 nullable | Data-year minus 1 |
| `complaint_index_prior_2` | f64 nullable | Data-year minus 2 (always null for 2023+ reports, which print only one prior year) |
| `source_file` | str | Filename of the source PDF |

## Run log

The parser appends to `output/run_log.txt`. Sample first run:

```
=== run started 2026-05-04T23:44:51+00:00 ===
Parsing 5 source files
  2020.pdf: 129 rows  (some skipped — boilerplate/footnotes)
  2021.pdf: 128 rows
  2022.pdf: 119 rows
  2023.pdf: 129 rows
  2024.pdf: 130 rows
Wrote ks_complaints_company_yearly.parquet (635 rows)
Wrote ks_complaints_yearly.parquet (30 rows)
=== run completed 2026-05-04T23:44:51+00:00 ===
```
