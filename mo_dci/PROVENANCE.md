# Provenance

Source-of-record details for the MO DCI complaint dataset. Outputs in `mo_dci/output/` are reproducible by re-running `scripts/01_download.py` then `scripts/02_parse.py`. The authoritative manifest is `interim/manifest.json`.

## Sources (URLs verified live 2026-05-05)

The DCI publishes these reports on its **Reports → Historical Reports** landing page:

- Landing page: <https://insurance.mo.gov/reports/historical-reports>
- Complaint Index Report section lists three years (2021, 2022, 2023) as direct PDF links.

Each link goes through a `/media/<id>` short-link redirector that resolves to a stable PDF URL under `/sites/insurance/files/<YYYY-MM>/<filename>.pdf`. Resolved URLs (snapshot 2026-05-05):

| Report | Short link | Resolved PDF URL | sha256 (first 16) |
|---|---|---|---|
| 2021 | `https://insurance.mo.gov/media/25301` | `https://insurance.mo.gov/sites/insurance/files/2024-09/2021ComplaintReport.pdf` | (recorded in `interim/manifest.json`) |
| 2022 | `https://insurance.mo.gov/media/25306` | `https://insurance.mo.gov/sites/insurance/files/2024-09/2022ComplaintReport.pdf` | |
| 2023 | `https://insurance.mo.gov/media/27486` | `https://insurance.mo.gov/sites/insurance/files/2024-11/2023%20Complaint%20Index.pdf` | |

The publication-month directory (`2024-09`, `2024-11`) is when the file was uploaded to the CMS, not when the data covers — both 2021 and 2022 reports were re-published in Sep 2024.

## Access notes

- **Rate-limit oddity.** The MO origin returns HTTP 429 ("Too Many Requests") even when the response body is a valid PDF. The downloader treats a 429 with a `%PDF-` body as success. Sleeping ~30 seconds between requests reduces the chance of a true rejection.
- **User-Agent.** A Chrome-like UA is used for fetching. Anonymous bot UAs may be 403'd.
- **Initial recon.** The PDFs were originally pulled into `.tmp/mo_recon/` during 2026-05-05 reconnaissance, then promoted to `mo_dci/interim/` once the project structure landed.

## Section / page index per report (data-page mapping)

These page numbers are the PDF-page indexes (1-based) used by the parser. They differ slightly from each report's printed content-page numbers because of TOC/cover offsets.

| Report | "Total Complaints by Line" | "Complaint Resolution" | Section 8 (All Companies) start |
|---:|---:|---:|---:|
| 2021 | 6 | 6 (same page) | 39 |
| 2022 | 5 | 6 | 51 |
| 2023 | 6 | 7 | 65 |

Section-8 sub-line ordering is consistent across reports (PPA → Homeowners/Farm/MH/Fire → A&H → LTC → MedSup → Life & Annuity → HMO).

## Layout differences across reports

| Property | 2021 | 2022 | 2023 |
|---|---|---|---|
| PDF version | 1.6 (zip-deflate) | 1.4 | 1.4 |
| `pdfplumber.extract_tables()` works? | No (text-mode rendering) | Yes | Yes |
| Per-company column order | Code &#124; Name &#124; ... | Code &#124; Name &#124; ... | Name &#124; Code &#124; ... |
| Both Section-4 tables on one page? | Yes (page 6) | No (pages 5 + 6) | No (pages 6 + 7) |
| Sub-line headers | Plain text | Plain text + over-section "All Companies" | Garbled/double-rendered + "8.<n>" prefix |

The parser handles each variant: tables-or-regex fallback, both column orders, both single-page and split-page Section-4 layouts, and both "8.<n>" and plain-title sub-line detection.

## P&C Supplement (out of scope for this project)

The DCI publishes a parallel **P&C Supplement Report** at the same `historical-reports` page. It is purely *financial* (premiums by sub-line, historical trends, loss ratios, ~516 pages) — no complaint data — so it's not extracted here. URL pattern matches the complaint reports (`/media/<id>` → `/sites/insurance/files/...`). Sample: 2023 P&C Supplement at <https://insurance.mo.gov/media/27536>. If you ever want per-premium normalization that isn't already in `complaints_company_by_period.avg_annual_premium`, this is where the bigger denominators live.

## Run history

### 2026-05-05 — initial build

- 3 PDFs pulled (1.6 MB + 5.9 MB + 5.5 MB = 13 MB total).
- Yearly aggregates: 300 rows across 3 reports (2017–2023 × 11 lines × 2 metrics, with cross-report duplicates retained).
- Per-company indices: 4,165 rows across 3 reporting periods.
- Cross-report agreement: 10 (year, line) cells disagree by 1–3 complaints (treated as legitimate revisions, not parser errors).
- Sub-line breakdown per report (rows): see `output/run_log.txt`.
