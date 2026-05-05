# Provenance — Indiana IDOI Company Complaint Index

## Source

- **Publisher:** Indiana Department of Insurance (IDOI), Consumer Services Division.
- **Landing page:** <https://www.in.gov/idoi/consumer-services/complaint-index/company-complaint-index/>
- **File hosting:** Each per-(year × line) report is at `https://www.in.gov/idoi/files/...` with year/line-specific filenames discovered by the downloader.

## First build (2026-05-04)

| Field | Value |
|---|---|
| `discovered_at` | 2026-05-04T23:37:34Z |
| Files downloaded | 80 (16 years × 5 lines) |
| Years covered | 2009–2024 inclusive |
| Lines covered | annuity, auto, health, homeowners, life |
| File formats | 79 PDF + 1 XLSX (2014) |
| Polite delay | 1 request / second |
| User-Agent | `insurance-complaint-rates/1.0 (research; contact: evan.ochsner@gmail.com)` |

Per-file SHA256 + Last-Modified are recorded in `interim/manifest.json`. A few representative entries:

```
2009_annuity.pdf       sha256=692a53c1758f…  url=…/2009_Annuity_Complaint_index_for_website.pdf
2009_auto.pdf          sha256=c0e0a1a565d0…  url=…/2009_auto_complaint_index_for_website.pdf
2024_homeowners.pdf    sha256=2f5a6bfd78ba…  url=…/2024-Homeowners-Index.pdf
2024_life.pdf          sha256=bd916b6b1d86…  url=…/2024-Life-Index.pdf
```

## File schema (per row, after parsing)

| Field | Type | Source |
|---|---|---|
| `year` | i32 | Data year, from the source filename (resolved by `01_download.py`) |
| `line` | str | One of `annuity`, `auto`, `health`, `homeowners`, `life` |
| `naic_code` | str | NAIC company code as printed (4–5 digits, kept as string to preserve leading zeros) |
| `company_name` | str | Company name as printed |
| `premium` | f64 nullable | Indiana written premium for the line; null if printed as "None" |
| `complaints` | i64 | Complaint count |
| `complaint_index` | f64 nullable | Null when printed as "DNC" (premium too small to compute) |
| `source_file` | str | Filename of the source PDF/XLSX (for traceability) |

## URL stability

IDOI filenames are inconsistent across years (e.g., `2024-Auto-Index.pdf`, `Auto-Complaint-Index.pdf`, `2021Auto.pdf`, `2009_auto_complaint_index_for_website.pdf`). The downloader **discovers URLs from the landing page** rather than guessing them, so re-runs work even if IDOI re-uploads files under new names. If IDOI restructures the landing page itself, the regex in `01_download.py` will fail loudly.

## Run log

The parser appends to `output/run_log.txt` on every run. Sample first run (truncated):

```
=== run started 2026-05-04T23:39:18+00:00 ===
Parsing 80 source files
  2009_annuity.pdf: 41 rows  (4 skipped)
  2009_auto.pdf: 129 rows  (5 skipped)
  ...
  2024_life.pdf: 41 rows  (7 skipped)
Wrote in_complaints_company_yearly.parquet (4,852 rows)
Wrote in_complaints_yearly.parquet (80 rows)
=== run completed 2026-05-04T23:39:19+00:00 ===
```

"Skipped" lines per file are the boilerplate footer rows ("Subtotal Premium and Complaints", "X Companies with Zero Complaints", "DNC- did not calculate ...", "Premium information from Annual Statement Page Y, Col. Z"). They are not silent data losses; the parser logs them when there are <8 to confirm only boilerplate was dropped.
