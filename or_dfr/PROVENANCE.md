# Provenance

Source-of-record details for the OR DFR complaint dataset. Outputs in `or_dfr/output/` are reproducible by re-running `scripts/01_download.py` then `scripts/02_parse.py`. The authoritative manifest is `interim/manifest.json`.

## Sources (URLs verified live 2026-05-05)

Landing page: <https://dfr.oregon.gov/help/complaints-licenses/Pages/complaint-information.aspx>

Per-PDF URL pattern:

```
https://dfr.oregon.gov/help/Documents/complaint-stats-{YEAR}/Complaint-{SLUG}-{YEAR}.pdf
```

Where `{YEAR}` is 2019..2025 and `{SLUG}` is one of `AutoFull`, `AnnuitiesFull`, `HealthFull`, `HomeownersFull`, `LifeFull`, `LTCfull`. The server is case-insensitive on the slug suffix (`LTCfull`, `LTCFull`, `LTCFULL` all work) but the parent directory `complaint-stats-{YEAR}` is case-sensitive. The downloader uses the exact casing documented on the landing page.

## Access notes

- **No Cloudflare**. Standard `urllib.request` with a polite User-Agent works; no scraping libraries needed.
- **No authentication / no cookies**.
- **No rate limit observed**, but the downloader sleeps 1s between fetches as a courtesy.

## Sources of variability

Two PDF layout variants observed:

| Layout | Years | Premium rendering |
|---|---|---|
| Split-digit | 2019, 2020, 2021, 2022, 2023, 2025 | `9 ,177,175` (leading digit separated by space from rest) |
| Clean | 2024 | `9,177,175` (single token) |

Both are handled by the regex in `02_parse.py` via an optional leading-digit capture group. The split-digit layout is a side-effect of right-aligned numeric columns and pdfplumber's text extraction.

The 2021 PDFs additionally lack the standard year banner ("`2021 Total Confirmed Complaint`") at the top of each page — only the line label is present. Year is taken from the manifest (filename) rather than the PDF body for those files. Six "WARN: parsed year None" log lines per run come from this; they're benign.

## Coverage

- **Years:** 2019 through 2025 (7 years).
- **Lines:** 6 personal lines per year.
- **Cutoff:** None published — DFR includes all authorized companies, including those with very small premium and zero complaints. ~70-360 companies per (line, year), roughly correlated with the line's market depth.

## Data integrity

- All 42 PDFs parse to ≥ 60 companies (worst case is LTC at ~70 companies; auto reaches 365).
- Sum of per-line totals across the 6 lines yields ~3,000-4,500 complaints per year, consistent with IDRR's OR baseline (~3,879/year) modulo informal contacts.
- Confirmed-complaint counts are 10-20% of total complaints in most (line, year) cells.

## Run history

### 2026-05-05 — initial build

- 42 PDFs fetched (~5 MB total).
- 9,428 per-company per-line per-year rows after parsing.
- 42 per-line per-year aggregate rows.
- Year banner missing on 2021 PDFs (not a data issue; year inferred from filename).
- Tesla General Insurance (a recent OR-licensed carrier) shows particularly high index — 31 complaints / 21 confirmed / index 82 in auto 2025.
