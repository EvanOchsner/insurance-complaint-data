# Kansas KID — per-company complaint index, by line and year

Per-company complaint index data from the Kansas Department of Insurance (KID) annual *Complaint Index Report*. One row per `(year, line, company)`, with KID's published complaint index, market share, complaint count, and the prior 1–2 years' indexes for trend context.

This is a **NAIC-tradition complaint index** — same metric class as IN IDOI, different from TX `Confirmed` / CT `against_insurer` counts. Lives under the "Regulator complaint indexes" viz category.

## What's in this folder

| Path | What it is |
|---|---|
| `output/ks_complaints_company_yearly.parquet` (and `.csv`) | **Headline.** One row per `(year, line, company)`. Columns: `naic_code, company_name, market_share, complaints, complaint_index, complaint_index_prior_1, complaint_index_prior_2, source_file`. |
| `output/ks_complaints_yearly.parquet` (and `.csv`) | Per `(year × line)` aggregate. Columns: `total_complaints, n_companies, median_index, market_share_covered`. |
| `output/run_log.txt` | Appended each run: per-file row counts and sanity stats. |
| `scripts/01_download.py` | Fetch each per-year PDF from the KID publications URL template; record per-file SHA256 + Last-Modified. |
| `scripts/02_parse.py` | Walk pages, identify per-line section headers, regex-parse data rows. |
| `interim/files/` | Raw PDFs. **Gitignored.** |
| `interim/manifest.json` | Discovery + fetch metadata. |
| `METHODOLOGY.md` | KID complaint index definition, inclusion criteria, comparison with IN IDOI. |
| `PROVENANCE.md` | Source URLs + per-file hashes + run log. |

## How to load

```python
import polars as pl

# Per-company, with prior-year context:
df = pl.read_parquet("ks_kid/output/ks_complaints_company_yearly.parquet")
df.filter((pl.col("year") == 2024) & (pl.col("line") == "auto")).sort("complaint_index", descending=True)

# Yearly aggregate:
yr = pl.read_parquet("ks_kid/output/ks_complaints_yearly.parquet")
yr.filter(pl.col("line") == "auto").sort("year")
```

## How to re-run

```
python3 ks_kid/scripts/01_download.py        # ~6 s (5 PDFs)
python3 ks_kid/scripts/02_parse.py           # < 5 s
```

## Headline caveats

1. **Same metric class as IN IDOI; not directly comparable to TX/CT counts.** KID's complaint index is `(share of complaints) / (share of premium)`, normalized to ~1.0 for parity. See [`METHODOLOGY.md`](METHODOLOGY.md).
2. **KID's inclusion criterion includes zero-complaint companies.** Each per-(year × line) table covers the **top-20 premium-writing companies** in the line plus any company with 10+ complaints. This means many rows have `complaint_index = 0.00` (top-20 premium writer with no complaints that year). The median index in our file is therefore *closer to the population median* than IN's, where zero-complaint companies are excluded entirely. The two states' median indexes are not apples-to-apples.
3. **Prior-year indexes can be `null`.** When a company first appears in a year's report, the prior-year columns may be `-` in the source PDF (which we parse to null). The `complaint_index_prior_1` and `_prior_2` columns are useful for verifying year-over-year trends but should not be used to backfill a separate year's row.
4. **Line label rename mid-coverage.** "Accident & Health" (2020–2022) becomes "Health" (2023+); both map to `health` in our output for time-series continuity.
5. **2020–2022 expose 3 prior-year indexes; 2023–2024 expose 2.** The third (`prior_2`) is null for 2023 and 2024 because the source PDF only prints two prior years.
6. **Line set varies year-over-year.** 2020 covers Auto, A&H, Homeowners, Life. 2022 adds Annuity, Long-Term Care. 2023+ all six (Auto, Health, Homeowners & Renters, Annuity, Life, Long-Term Care). The `ks_complaints_yearly.parquet` aggregate has only the slices that actually appear in each year's PDF.

## Headline numbers (for sanity check)

From the 2026-05-04 build:

- 5 source PDFs (2020–2024).
- 30 (year × line) slices.
- 635 per-company rows.
- **Median index by line, 2020 → 2024:**
  | Line | 2020 | 2021 | 2022 | 2023 | 2024 |
  |---|---:|---:|---:|---:|---:|
  | auto | 0.90 | 0.79 | 0.70 | 0.99 | 1.30 |
  | health | 0.75 | 0.70 | 0.71 | 0.00 | 1.41 |
  | homeowners | 0.79 | 0.80 | 0.82 | 0.87 | 0.99 |
  | life | 0.42 | 0.31 | 0.25 | 0.32 | 0.25 |
  | annuity | 0.00 | 0.00 | 0.53 | 0.56 | 0.14 |
  | long_term_care | 0.00 | 0.34 | 0.70 | 0.12 | 0.54 |

  Medians sit closer to 1.0 than IN's because KID's report includes top-20 premium writers regardless of complaint count.
