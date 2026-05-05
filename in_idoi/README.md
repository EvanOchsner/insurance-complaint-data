# Indiana IDOI — per-company complaint index, by line and year

Per-company complaint index data from the Indiana Department of Insurance (IDOI) *Company Complaint Index* publications. One row per `(year, line, company)`, with the IDOI-published complaint index (~share of complaints / share of premium, normalized to 1.0 for parity), the underlying complaint count, and the company's premium volume.

This is a **NAIC-tradition complaint index** — a different metric class than TX TDI's `Confirmed`/`Not Confirmed` or CT CID's `disposition` buckets. The viz lives under a separate "Regulator complaint indexes" category for that reason. See [`METHODOLOGY.md`](METHODOLOGY.md) for the distinction.

## What's in this folder

| Path | What it is |
|---|---|
| `output/in_complaints_company_yearly.parquet` (and `.csv`) | **Headline.** One row per `(year, line, company)`. Columns: `naic_code, company_name, premium, complaints, complaint_index, source_file`. |
| `output/in_complaints_yearly.parquet` (and `.csv`) | Per `(year × line)` aggregate. Columns: `total_complaints, total_premium, n_companies, median_index`. |
| `output/run_log.txt` | Appended each run: per-file row counts, anomalies, sanity stats. |
| `scripts/01_download.py` | Discover the (year × line) → URL grid from the IDOI landing page; fetch all files; record per-file SHA256 + Last-Modified. |
| `scripts/02_parse.py` | Regex-parse each PDF (and the 2014 XLSX); concat into outputs. |
| `interim/files/` | Raw downloaded files. **Gitignored.** |
| `interim/manifest.json` | Discovery + fetch metadata. |
| `METHODOLOGY.md` | What the complaint index means; coverage exclusions; population vs sample interpretation. |
| `PROVENANCE.md` | Source URLs + per-file hashes + run log. |

## How to load

```python
import polars as pl

# All per-company rows:
df = pl.read_parquet("in_idoi/output/in_complaints_company_yearly.parquet")
df.filter((pl.col("year") == 2024) & (pl.col("line") == "auto")).sort("complaint_index", descending=True).head(10)

# Yearly aggregate:
yr = pl.read_parquet("in_idoi/output/in_complaints_yearly.parquet")
yr.filter(pl.col("line") == "auto").sort("year")
```

## How to re-run

```
python3 in_idoi/scripts/01_download.py        # ~90 s (80 files; 1 req/s polite delay)
python3 in_idoi/scripts/02_parse.py           # < 10 s
```

`01_download.py` fetches every (year × line) file from the IDOI landing page. `interim/manifest.json` records SHA256 + Last-Modified per file so re-runs are auditable.

## Headline caveats

1. **The complaint index is a ratio, not a count.** IDOI defines it as `(company's share of total complaints) / (company's share of total written premium)`, normalized so 1.0 means the company received complaints proportional to its market presence. Above 1.0 means more complaints than its market share would predict; below 1.0 means fewer. **Index values are not directly comparable to TX `Confirmed` counts or CT `against_insurer` counts** — different metric.
2. **Only complaint-having companies appear in the per-company file.** IDOI excludes companies with zero complaints from each per-(year × line) table. The footnotes in each PDF report the count and aggregate premium of the excluded zero-complaint companies. **The median of the per-company file is biased above 1.0** for that reason; the population median across all premium-writing companies is closer to the premium-weighted average and lower.
3. **Index is null when IDOI prints "DNC"** — Did Not Compute, applied when the company's premium denominator is too small (typically <$1M) to yield a meaningful index. The complaint count is still recorded.
4. **Premium is null when IDOI prints "None"** — no premium reported by the company in that year.
5. **2017–2018 PDFs use `$` prefixes on premium values** while other years don't; the parser handles both.
6. **2014 is XLSX, not PDF.** Same logical schema; parsed via openpyxl.
7. **Reports are issued ~12–18 months after the data year.** The 2024 reports (newest at first build) cover calendar-year 2024 complaints. Earlier years go back to 2009.

## Headline numbers (for sanity check)

From the 2026-05-04 build:

- 80 source files (16 years × 5 lines).
- 4,852 per-company rows total.
- All 80 (year × line) slices present with non-zero rows.
- **Median index by line, last 5 years (among complaint-having companies only):**
  | Line | 2020 | 2021 | 2022 | 2023 | 2024 |
  |---|---:|---:|---:|---:|---:|
  | annuity | 8.37 | 16.42 | 4.74 | 5.91 | 3.94 |
  | auto | 2.07 | 2.07 | 1.90 | 2.03 | 2.59 |
  | health | 3.03 | 2.82 | 2.68 | 2.93 | 2.95 |
  | homeowners | 1.85 | 1.55 | 1.74 | 1.45 | 1.87 |
  | life | 3.07 | 2.27 | 5.90 | 4.08 | 4.04 |

The medians sit well above 1.0 because zero-complaint companies are excluded from the report — see caveat 2.
