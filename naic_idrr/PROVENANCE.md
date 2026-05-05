# Provenance

Source-of-record details for the NAIC IDRR (Insurance Department Resources Report) dataset. Outputs in `naic_idrr/output/` are reproducible by re-running `scripts/01_download.py` then `scripts/02_parse.py`. The authoritative manifest is `interim/manifest.json` — the tables here are a human-readable copy.

## Sources (URLs verified live 2026-05-04)

### IDRR Vol 1 PDFs

The 1986–2022 archive is hosted on NAIC's third-party document portal (Soutron Global). The current-publication-year Vol 1 + Vol 2 PDFs are on `content.naic.org`.

| Era | Host | URL pattern |
|---|---|---|
| 1986–2022 | Soutron Global archive | `https://naic.soutronglobal.net/Portal/Public/en-US/DownloadImageFile.ashx?objectId=<id>&ownerType=0&ownerId=11628` |
| Current (2023 publication) | content.naic.org | `https://content.naic.org/sites/default/files/publication-sta-bb-volume-one.pdf` |
| Current (2023 Vol 2) | content.naic.org | `https://content.naic.org/sites/default/files/publication-sta-bb-volume-two.pdf` |

The `objectId` per year is recorded in [`reference/idrr_pdf_index.csv`](reference/idrr_pdf_index.csv). Resolver landing pages:

- Soutron archive index: <https://naic.soutronglobal.net/Portal/Public/en-US/RecordView/Index/11628>
- NAIC publications page (filtered): <https://content.naic.org/publications?name=Insurance+Department+Resources+Report&field_publication_category_target_id=All>

### Year naming convention

NAIC publishes the IDRR in calendar year *N+1* with calendar year *N*'s data. Soutron's archive labels the file by **publication year**, while the table titles inside read "Consumer Complaints/Inquiries - YYYY" with the **data year**. The parser extracts the data year from the title and uses it as canonical; the publication-year-labeled "2023" PDF currently still contains 2022 data because the 2023-data IDRR has not been released as of fetch time.

### CIS Tableau dashboards (snapshots only — data not extracted)

The three NAIC CIS aggregated complaint reports are embedded Tableau dashboards rendered client-side:

| URL | Tableau view |
|---|---|
| <https://content.naic.org/cis_agg_reason.htm> | `tableau.naic.org/views/CIS-WB-MostCommonComplaintsByReason/CISDBComplaintsbyReason2` |
| <https://content.naic.org/cis_agg_disposition.htm> | `tableau.naic.org/views/CIS-WB-MostCommonComplaintsByDispositions/CISDBComplaintsbyDisposition2` |
| <https://content.naic.org/cis_agg_type.htm> | `tableau.naic.org/views/CIS-WB-MostCommonComplaintsByType_0/CISDBComplaintsbyType2` |

The wrapper HTML is captured to `interim/cis/<name>.html` for provenance, but **the underlying tables are not extracted in v1**. Doing so requires implementing Tableau's `bootstrapSession` protocol (POST a session token, parse a custom concatenated-JSON response, decode Tableau's integer-pointer column scheme). The NAIC CIS dashboards cover only the most recent ~3 years of closed *confirmed* complaints, so the depth value is small relative to the implementation cost; deferred to v2. See `METHODOLOGY.md` for what these dashboards measure.

### User-Agent

The downloader sends a browser-like Chrome UA. This is not stealth — we identify ourselves transparently here and in `interim/manifest.json` via `project_tag = "insurance-complaint-rates/1.0 (research; contact: evan.ochsner@gmail.com)"`. Some NAIC infrastructure 403s on bot-like UAs.

## First-run snapshot — 2026-05-04

Total downloaded: **140.6 MB** across **39 IDRR PDFs** (1986–2023, both volumes for 2023) + **3 CIS dashboard HTML snapshots**.

| Year | File | Bytes | SHA-256 (first 16) |
|---:|---|---:|---|
| 1986 | `1986.pdf` |   552,436 | `5c8e4fe991bc0904…` |
| 1987 | `1987.pdf` |   948,904 | `04ebf333fa08ff56…` |
| 1988 | `1988.pdf` | 1,040,224 | `e7b4a0efc8d61af3…` |
| ... | (full table in manifest.json) | | |
| 2022 | `2022.pdf` | 8,199,535 | `d6396b39cf6ae9dd…` |
| 2023 | `2023.pdf` (currently 2022 data) | 3,968,296 | `da5174bc8804cbac…` |
| 2023 | `2023_vol2.pdf` | 4,248,329 | `ec6c0a2ccec25373…` |

## Output files

| File | Rows | What |
|---|---:|---|
| `naic_idrr_complaints_state_yearly.parquet` | 1,261 | One row per `(year, jurisdiction)` for 1998–2022 (24 years × 56 jurisdictions, sparse where territories report nothing) |
| `naic_idrr_complaints_state_yearly.csv` | 1,261 | CSV mirror |
| `run_log.txt` | (append-only) | Per-run parse log with sum-vs-Total verification |

## Year coverage and skip log

| Year | Status | Reason |
|---|---|---|
| 1986–1993 | skipped | Source PDFs are scanned at low DPI; pdfplumber text extraction returns OCR garbage with no parseable table |
| 1994 | skipped | Sum-vs-printed-Total Δ = 23%; data unreliable |
| 1995 | skipped | Only 32 of ~55 jurisdictions extracted before parser bailed |
| 1996, 1997 | skipped | Same OCR issues as 1986–1993 |
| 1998–2002 | parsed | Δ ≤ 0.4% against printed Total |
| 2003 | skipped | Multi-column PDF layout interleaves the table with another table on the same page; `pdfplumber.extract_text()` returns mangled rows |
| 2004–2022 | parsed | Δ = 0% against printed Total for almost all years |

The parser rejects any year whose per-state sum diverges from the printed national Total by more than 5%, OR where fewer than 45 jurisdiction rows extract. This is the auto-tolerance gate; the rejected-year log is in `output/run_log.txt`.

## Run history

### 2026-05-04T22:10Z

- 39 IDRR PDFs downloaded successfully (`%PDF-` magic verified per file).
- 3 CIS Tableau dashboard HTML snapshots captured for provenance only.
- Parse: 24 years × 56 jurisdictions = 1,261 rows in final output.
- 13 PDFs skipped per the table above.
- Sum-vs-Total verification: Δ=0 for 21 of 24 retained years; Δ<0.5% for the other 3 (1998 Δ=1,508; 1999 Δ=9,688; 2002 Δ=3,672 — these are differences between the parser's per-state sum and the printed PDF Total row, suggesting one or two rows in those years where pdfplumber misparsed a value; the data is good for trend purposes but expect ±0.5% noise on the 1998–2002 sub-era).

Append future runs below this line.
