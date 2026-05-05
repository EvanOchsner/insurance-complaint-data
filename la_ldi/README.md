# Louisiana LDI — per-company complaint indices, 4 lines, 10 years

Per-company complaint indices and per-line per-year aggregates from the Louisiana Department of Insurance (LDI) public *Consumer Complaint Data* tool. Four lines of insurance, 10 years (2015–2024), full long-tail company list per (line, year).

This is a **NAIC-tradition complaint index** dataset (same metric class as MO/IN/KS/ID/IL/CO/WI). LA passes the Phase 5 "has dimensions IDRR doesn't have" test cleanly: per-company indices with NAIC-style methodology, plus 10 years of history (the deepest in this peer set).

The data is also a striking case study: **homeowners complaints jumped from ~315 in 2019 to 4,492 in 2021** as Hurricane Ida (Aug 29, 2021) hit, and the per-company indices for 2021 cleanly identify the carriers that subsequently went insolvent (Ocean Harbor, Allied Trust, Southern Fidelity, FedNat, United Property & Cas, Maison, GeoVera Specialty).

## What's in this folder

| Path | What it is |
|---|---|
| `output/la_complaints_company_yearly.parquet` (and `.csv`) | **Per-company per-line per-year complaint index, premium, market share.** ~9,550 rows total across 4 lines × 10 years. Columns: `state, year, line, company_name_raw, premium_written, market_share, complaints, complaint_index, source_pdf`. |
| `output/la_complaints_yearly.parquet` (and `.csv`) | **Per-line per-year aggregates** (40 rows). Columns: `state, year, line, n_companies, total_complaints, total_premium`. |
| `output/run_log.txt` | Appended each parse run; per-file company / complaint / premium subtotals. |
| `scripts/01_download.py` | Fetches all 40 PDFs from `ldi.la.gov/onlineservices/complaintindex/`. Uses `cloudscraper` to clear LDI's Cloudflare managed challenge, then replays the ASP.NET WebForms POST per (line, year). |
| `scripts/02_parse.py` | Regex-based per-row parser (pdfplumber's table extractor returns single-cell rows for these PDFs, so we work directly off the text). |
| `interim/files/` | Raw PDFs. Gitignored. |
| `interim/manifest.json` | Discovery + fetch metadata (sha256 per file, source URL). |
| `METHODOLOGY.md` | LDI complaint index definition, comparison with peer states. |
| `PROVENANCE.md` | Source URL, form-field details, Cloudflare bypass note. |
| `PLAN.md` | Open follow-ups: pre-2015 history, NAIC code mapping, line "Life Company Sort" (the page text mentions a 5th line that doesn't appear in the form's actual coverage-type dropdown — verify with LDI). |

## How to load

```python
import polars as pl

# Per-company by line for the most recent year:
c = pl.read_parquet("la_ldi/output/la_complaints_company_yearly.parquet")
c.filter((pl.col("year") == 2024) & (pl.col("line") == "homeowners")).sort("complaint_index", descending=True).head(10)

# Per-line trend:
y = pl.read_parquet("la_ldi/output/la_complaints_yearly.parquet")
y.filter(pl.col("line") == "homeowners").sort("year")
```

## How to re-run

```sh
python3 la_ldi/scripts/01_download.py    # ~2 min (40 PDFs, 2.5s sleep between fetches)
python3 la_ldi/scripts/02_parse.py        # ~10 s
```

## Caveats — read before plotting

1. **Cloudflare challenge.** LDI's online-services subdomain is behind Cloudflare's managed challenge. The downloader uses `cloudscraper` to clear the challenge, then drives the WebForms with the same session. If the challenge changes (which Cloudflare periodically does), the downloader may break and require updating cloudscraper or switching to browser-based automation.
2. **Index methodology = NAIC share-of-share** (same as MO/IN/KS): `(company complaints / total complaints) / (company premium / total premium)`. **A score of 1.0 = industry average for that line.** Score > 1 means more complaints than expected for the company's premium volume.
3. **No outcome / disposition data.** Like MI and OH, LDI publishes complaint *counts* and *ratios* but not merits-decision categorization. Outcome data would need a public-records request.
4. **Coverage type "Life Company Sort"** (mentioned in the page's body text) does NOT appear in the form's actual coverage-type dropdown. Either the page text is stale, or "Life Company" requires a different access path. Out of scope; flagged in `PLAN.md`.
5. **Negative premiums** appear in some rows (e.g., `($232.00)`, `-$50,594.00`). These are accounting-style negative amounts — premium reversals or end-of-year accounting adjustments. The parser preserves the sign so downstream code can filter or include as appropriate.
6. **Index can be capped or extreme.** Companies with very small (or zero) premium that received any complaints can show very large complaint indices (e.g., `9999+`, or `63,542`). LDI does not appear to apply a cap, unlike MO (which caps at 9,999). Filter on `premium_written > 0` and `market_share > 0.0001` for stable comparisons.
7. **Accident & Health line saw a methodology change in 2023.** Pre-2023 reports showed ~300+ companies; 2023+ reports show ~115-130. Likely an exclusion of certain plan types (Medicare Advantage / Medicaid managed care / etc.). Worth investigating before doing year-over-year A&H trend analysis.
8. **No NAIC code published per company.** LDI prints "Company Name as filed." Cross-state NAIC group rollup requires fuzzy matching against the canonical NAIC group reference (same situation as MI, KS, ID, IL).
