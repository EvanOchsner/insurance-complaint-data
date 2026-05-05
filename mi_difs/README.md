# Michigan DIFS — per-company complaint ratios + per-line / per-reason aggregates

Per-company complaint ratios and per-year aggregates from the Michigan Department of Insurance and Financial Services (DIFS) public *Complaint Statistics and Ratios* tool. Three years of data (2022, 2023, 2024) across 5 lines of business, 4 reason categories, and 3 entity types.

This is **Michigan's complaint-ratio metric**: complaints per $1M of direct written premium. Different formula than MO/IN/KS/ID/IL (which use the NAIC-tradition share-of-share index normalized to 100). Documentation in `METHODOLOGY.md` explains how to relate the two if you need an apples-to-apples cross-state comparison.

## What's in this folder

| Path | What it is |
|---|---|
| `output/mi_complaints_company_yearly.parquet` (and `.csv`) | **Per-company per-line per-year ratios.** One row per `(year, line, company)`. Columns: `state, year, line, company_id, company_name_raw, complaints, written_premium, complaint_ratio_per_million`. ~1,033 rows total across 5 lines × 3 years. Note: only companies that wrote ≥ $1M premium for that line in that year are included (DIFS exclusion rule). |
| `output/mi_complaints_yearly.parquet` (and `.csv`) | **Per-line aggregate counts.** From the Line of Coverage stats page. Columns: `state, year, line, count`. 7 lines × 3 years = 21 rows. Lines: `accident_health, annuity, automobile, fire_allied_cmp, homeowners, liability, life`. (Includes 2 lines without per-company tables: `fire_allied_cmp` and `liability` — DIFS doesn't publish per-company ratios for those.) |
| `output/mi_complaints_total_yearly.parquet` (and `.csv`) | **Per-year totals by entity type.** Columns: `state, year, entity_type, count`. Entity types: `insurance_company, hmo, other, total`. 4 buckets × 3 years = 12 rows. |
| `output/mi_complaints_by_reason.parquet` (and `.csv`) | **Per-year per-reason × per-entity-type counts.** Columns: `state, year, reason_category, entity_type, count, pct_within_entity`. 4 reasons × 3 entities × 3 years = 36 rows. Reasons: Claim Handling, Marketing & Sales, Customer Service, Underwriting. |
| `output/run_log.txt` | Appended each run: per-file row counts and a sanity-check comparing per-company-table sums to Line-of-Coverage totals. |
| `scripts/01_download.py` | Fetches all 24 HTML pages (5 lines × 3 years for company ratios + 3 stats × 3 years for aggregates) from `difs.state.mi.us`. |
| `scripts/02_parse.py` | BeautifulSoup-based parser using stable `aria-label` and `data-th` selectors. |
| `interim/files/` | Raw HTML pages. Gitignored. |
| `interim/manifest.json` | Discovery + fetch metadata (sha256, source URL). |
| `METHODOLOGY.md` | DIFS ratio definition, $1M premium exclusion floor, comparison with MO/IN/KS, peer-state reconciliation. |
| `PROVENANCE.md` | Source URLs + per-file hashes + access notes. |
| `PLAN.md` | Open follow-ups: pre-2022 history, NAIC-code mapping, per-company detail page extraction. |

## How to load

```python
import polars as pl

# Per-company auto ratios for 2024:
c = pl.read_parquet("mi_difs/output/mi_complaints_company_yearly.parquet")
c.filter((pl.col("year")==2024) & (pl.col("line")=="automobile")).sort("complaint_ratio_per_million", descending=True).head(20)

# Per-year aggregate by line:
y = pl.read_parquet("mi_difs/output/mi_complaints_yearly.parquet")
y.sort(["line", "year"])
```

## How to re-run

```sh
python3 mi_difs/scripts/01_download.py    # ~25s (24 HTML pages, 1s sleep between)
python3 mi_difs/scripts/02_parse.py        # < 5s
```

## Caveats — read before plotting

1. **Ratio = complaints / premium-in-millions, NOT NAIC share-of-share.** A MI ratio of 0.19 means 0.19 complaints per $1M premium written. Do not directly compare to MO/IN/KS complaint indices (which are scaled to 100=industry-average). See `METHODOLOGY.md` for cross-state reconciliation.
2. **$1M premium exclusion.** Companies that wrote less than $1M in premium for the line in the report year are NOT in the per-company table. The line-of-coverage aggregate (`mi_complaints_yearly`) DOES include them, so per-company sums will undercount the line total. The diff is logged each run.
3. **HMO complaints are separate.** "Insurance Company Complaints" and "HMO Complaints" are disjoint buckets in `mi_complaints_total_yearly`. The per-company table does NOT include HMOs (no per-HMO ratios are published). For a true total, sum the entity types or use the `total` row.
4. **No NAIC code published.** The per-company table uses DIFS's internal `company_id` (e.g., `0000401`) — not a NAIC code. NAIC group rollup requires a fuzzy-name match against the canonical NAIC group reference. See `PLAN.md`.
5. **Only 3 years available.** DIFS currently exposes 2022, 2023, 2024. Earlier years are not linked from the public site. To go further back, an Internet Archive crawl or PRR is needed (see `PLAN.md`).
6. **Company-detail pages NOT extracted in v1.** Each company link on a per-line page goes to a per-company detail page (`/InsuranceRatioDetail?companyID=...&forYear=...`) that may have additional fields (per-reason breakdown for that company, prior-year history). Out of scope; see `PLAN.md`.
