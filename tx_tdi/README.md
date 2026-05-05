# Texas TDI consumer complaints — by year, coverage, and "Confirmed" finding

Closed insurance consumer complaints from the Texas Department of Insurance, by calendar year of close. The headline metric is **`finding_type`**, which TDI itself classifies as either `Confirmed` (regulator found the insurer acted improperly) or `Not Confirmed` (regulator left the insurer's position intact). The data starts in 2012.

This is the closest TX analogue to Maryland MIA's "in favor of insured" series — the most useful regulator-side proxy for "bad-faith-adjacent" behavior at scale.

## What's in this folder

| Path | What it is |
|---|---|
| `output/tx_complaints_yearly_confirmed.parquet` (and `.csv`) | **Headline.** One row per `(year_closed, coverage_type)` plus an `ALL` row per year. Columns: `total, confirmed, not_confirmed, confirmed_rate`. |
| `output/tx_complaints_yearly.parquet` (and `.csv`) | Multi-dim pivot — one row per `(year_closed, coverage_type, finding_type)` with a count. Use this to plot Confirmed-vs-Not stacked or side-by-side. |
| `output/tx_complaints_complaint_level.parquet` (and `.csv`) | One row per closed complaint, all 11 fields, parsed dates. Use for ad-hoc analysis (reason codes, complainant type, etc.). |
| `output/run_log.txt` | Appended each run: timestamps, row counts, sanity tables. |
| `scripts/01_pull.py` | Paginated Socrata fetch → `interim/jjc8-mxkg.parquet` + manifest. |
| `scripts/02_aggregate.py` | Parse, derive `year_closed`, write the three output files. |
| `interim/` | Raw API pull and `manifest.json`. **Gitignored.** |
| `METHODOLOGY.md` | What "Confirmed" means; calendar-year-of-close; what's not in here. |
| `PROVENANCE.md` | Source URL with date verified; pull manifest; row counts; run log. |

## How to load

```python
import polars as pl

# Headline yearly trend (just the "ALL" rows):
df = pl.read_parquet("tx_tdi/output/tx_complaints_yearly_confirmed.parquet")
df.filter(pl.col("coverage_type") == "ALL").sort("year_closed")

# By-coverage trend:
df.filter((pl.col("coverage_type") != "ALL") & (pl.col("year_closed") >= 2020))

# Complaint-level:
cl = pl.read_parquet("tx_tdi/output/tx_complaints_complaint_level.parquet")
cl.filter(pl.col("year_closed") == 2025).group_by("complaint_type").len().sort("len", descending=True)
```

## How to re-run

```
python3 tx_tdi/scripts/01_pull.py        # ~30 s, ~3 MB parquet
python3 tx_tdi/scripts/02_aggregate.py   # < 5 s
```

`01_pull.py` always does a fresh full pull (281k rows is small enough that incrementals aren't worth the complexity). `interim/manifest.json` records the fetch timestamp and the server's `rowsUpdatedAt` so you can compare runs.

## Headline caveats

1. **`Confirmed` ≠ "won bad-faith lawsuit".** It means TDI's complaint-handling staff reviewed the matter and concluded the insurer violated a statute, rule, or policy provision. Many complaints that go on to litigation never appear here, and many "Confirmed" findings are about administrative issues unrelated to bad faith specifically.
2. **The temporal anchor is `closed_date`** (calendar year of close), matching how TDI itself reports complaint volumes. Year of receipt is also in the complaint-level file.
3. **The most recent year is partial.** Data through `2026-05-01` at the time of the first build. Treat the trailing year as preliminary and either drop it or mark it visually.
4. **Coverage starts 2012**, not earlier. The dataset's oldest closed complaint is 2012-05-21.
5. **Workers' comp underrepresented.** TDI's `coverage_type` lacks a "Workers' Comp" line; WC indemnity disputes go to a separate Division of Workers' Compensation flow not in this dataset. ~1,800 rows do appear under `complaint_type` values like "Workers Compensation Network" and "Workers' Compensation"; treat them as a partial signal.
6. **No per-company breakdown here.** That requires the separate "Complaint indexes and policy counts" dataset (out of scope for this v1).

## Headline numbers (for sanity check)

From the 2026-05-04 build (sha-stable as long as the source dataset doesn't change):

- 281,397 closed complaints from 2012-05-21 through 2026-05-01 (1 row dropped for null `finding_type`).
- 7 native coverage_type lines: Accident and Health (40.8%), Automobile (34.0%), Homeowners (14.4%), Life & Annuity (5.4%), Miscellaneous (3.3%), Liability (1.3%), Fire/Allied/CMP (0.8%).
- **Confirmed rate by year (ALL coverages):**
  | Year | Total | Confirmed | Rate |
  |---:|---:|---:|---:|
  | 2013 | 20,151 | 2,959 | 14.7% |
  | 2018 | 21,296 | 3,553 | 16.7% |
  | 2019 | 30,878 | 4,319 | 14.0% |
  | 2022 | 14,476 | 2,189 | 15.1% |
  | 2023 | 19,256 | 3,469 | 18.0% |
  | **2024** | 17,369 | 4,734 | **27.3%** |
  | **2025** | 22,562 | 7,057 | **31.3%** |
  | 2026 (partial) | 10,284 | 2,618 | 25.5% |
- The recent jump in confirmed rate is broad-based: every coverage line roughly doubled its 2021 rate by 2025 (Auto 8% → 27%; A&H 18% → 47%; Homeowners 11% → 28%; Life 17% → 35%).
