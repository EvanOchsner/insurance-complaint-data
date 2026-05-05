# Missouri DCI — per-company complaint indices + per-year per-line counts

Per-company complaint indices and per-year per-line aggregate counts from the Missouri Department of Commerce & Insurance (DCI) annual *Complaint Index Report*. Three reports published as PDFs (2021, 2022, 2023) cover **2017–2023** in per-year aggregate form and **2018–2023** in 3-year-pooled per-company form.

This is a **NAIC-tradition complaint index** dataset — same metric class as IN, KS, ID, IL — plus a per-year per-line workload-and-resolution series that's richer than what most complaint-index states publish. Lives under the "Regulator complaint indexes" + "Regulator findings" viz categories.

## What's in this folder

| Path | What it is |
|---|---|
| `output/mo_complaints_yearly.parquet` (and `.csv`) | **Per-year per-line aggregates.** One row per `(report_year, year, line, metric)` so cross-report agreement is auditable. Metrics: `complaints_total` and `pct_resolved_consumer_relief`. Lines: 11 (PPA, Homeowners, Other P&C, Total P&C, LTC, MedSup, HMO, All-Other-A&H, Total A&H, Life & Annuities, Total). Years 2017–2023. |
| `output/mo_complaints_company_by_period.parquet` (and `.csv`) | **Per-company complaint indices** for each 3-year reporting period. One row per `(report_year, line, NAIC code)`. Columns: `complaints_pooled, avg_annual_premium, avg_market_share, complaint_index`, plus `period_start`/`period_end`. ~4,165 rows total across the three periods (2018–2020, 2020–2022, 2021–2023). |
| `output/run_log.txt` | Appended each run: per-file row counts, sub-line breakdowns, and cross-report-agreement diagnostics. |
| `scripts/01_download.py` | Fetch the three PDFs from `insurance.mo.gov`. Tolerates HTTP 429 rate-limit responses that still deliver a valid PDF body. |
| `scripts/02_parse.py` | Walk each PDF: extract the per-year aggregates from Section 4, and per-company indices from Section 8. Hardcoded section-8 start pages per report (the three PDFs use different layouts; see `PROVENANCE.md`). |
| `interim/files/` | Raw PDFs. **Gitignored.** |
| `interim/manifest.json` | Discovery + fetch metadata (sha256, source URL). |
| `METHODOLOGY.md` | DCI complaint index definition, 3-year rolling window caveat, comparison with IN/KS/ID/IL. |
| `PROVENANCE.md` | Source URLs + per-file hashes + access notes (rate limits). |
| `PLAN.md` | Open follow-ups: pre-2018 history, per-year disaggregation, Section 5 reason breakouts, Section 4 P&C sub-line breakouts. |

## How to load

```python
import polars as pl

# Per-year per-line aggregates:
y = pl.read_parquet("mo_dci/output/mo_complaints_yearly.parquet")
y.filter((pl.col("line") == "private_passenger_auto") & (pl.col("metric") == "complaints_total")).sort("year")

# Per-company complaint indices for the 2021–2023 reporting period:
c = pl.read_parquet("mo_dci/output/mo_complaints_company_by_period.parquet")
c.filter((pl.col("report_year") == 2023) & (pl.col("line") == "private_passenger_auto")).sort("complaint_index", descending=True).head(20)
```

## How to re-run

```sh
python3 mo_dci/scripts/01_download.py    # ~95s with rate-limit padding
python3 mo_dci/scripts/02_parse.py        # ~30s for 357 PDF pages
```

## Caveats — read before plotting

1. **Per-company indices are 3-year-pooled, not per-year.** The complaint index is computed against three years of complaints and three years of premium. Each published report covers a different rolling window: 2018–2020 (2021 report), 2020–2022 (2022 report), 2021–2023 (2023 report). To get single-year per-company counts, deconvolution across overlapping windows is algebraically underdetermined for individual years; a public-records request to DCI Statistics would be required for true annualized per-company data.
2. **Per-year per-line counts ARE genuinely per-year.** Section 4 of each report shows the prior-five-years' annual totals separately. The three reports together give a per-year series for **2017–2023**.
3. **Cross-report disagreements of 1–3 complaints exist.** When a year (e.g., 2020) appears in two reports, the values usually agree exactly but occasionally differ by 1–3 complaints. These are real revisions, not parser errors. The `mo_complaints_yearly` parquet keeps a row per `(report_year, year, line, metric)` so the disagreements remain auditable; downstream code typically picks the most-recent report's value as authoritative.
4. **Index cap is 9,999.** Per the report's methodology, complaint indices are capped at 9,999. Use that as a sentinel if you need to detect capped rows.
5. **"All complaints, regardless of resolution" — not just confirmed.** Unlike TX `Confirmed` or MD `in favor of insured`, MO's complaint counts include every complaint regardless of how it was resolved. The closest outcome metric is `pct_resolved_consumer_relief` (per-line per-year, in `mo_complaints_yearly`), which approximates the canonical `regulator_finding_against_insurer` rate.
6. **Sections 5 (per-reason), 4-third-table (P&C sub-line breakouts), 6/7 (top-40 writers) NOT extracted in v1.** See `PLAN.md` for follow-ups.
7. **"Other P&C" is opaque.** Sub-line breakouts (Commercial Auto, General Liability, Workers' Comp, etc.) are in the 2022/2023 reports' Section 4 third table but not extracted in v1.
