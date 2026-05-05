# New York DFS insurance complaints — auto and health

NY DFS publishes per-insurer **upheld** complaint counts: DFS's own determination that the insurer acted improperly. This is the closest NY analogue to TX `Confirmed`, CA `Justified`, and MD's "in favor of insured" — directly comparable across the regulator-side states in this project.

Two streams cover the consumer-facing lines:

- **Auto** (Open Data NY, 2009-2024) — clean Socrata API, ~2,500 rows, per-company per-year. The metric is a 2-year rolling complaint ratio per NY's statutory ranking methodology.
- **Health** (Consumer Guide PDFs, 2015-2024) — annual ranking PDFs with structured per-company tables for HMOs, EPO/PPO plans, and Commercial Health Insurers. Annual single-year metric.

## What's in this folder

| Path | What it is |
|---|---|
| `output/ny_auto_complaints_company_year.parquet` (and `.csv`) | One row per `(filing_year, naic, company_name)`. Columns: `upheld_complaints, question_of_fact_complaints, not_upheld_complaints, total_complaints, premiums_written_in_millions, ratio, rank`. **Note the 2-year rolling caveat** — see METHODOLOGY.md. |
| `output/ny_auto_complaints_yearly.parquet` (and `.csv`) | Statewide rollup, one row per year (2009-2024). Columns suffixed `_2yr` to make the windowing explicit. |
| `output/ny_health_complaints_company_year.parquet` (and `.csv`) | Per-plan per-year health complaint counts. Columns: `data_year, plan_type, plan_name, rank, total_complaints_dfs, upheld_complaints_dfs, premiums_millions, complaint_ratio_dfs, total_complaints_doh, upheld_complaints_doh` (DOH columns null for non-HMO). |
| `output/ny_health_complaints_yearly.parquet` (and `.csv`) | Per-(year, plan_type) rollup with `upheld_per_million_premium`. |
| `output/run_log.txt` | Appended each run. |
| `scripts/01_download.py` | Auto Socrata pull + 10 health PDF downloads. |
| `scripts/02_parse.py` | Parses both streams. |
| `interim/` | Raw API JSON + 10 PDFs + manifest. **Gitignored.** |
| `METHODOLOGY.md` | What "upheld" means; the 2-yr rolling caveat; what's not in here. |
| `PROVENANCE.md` | URLs, hashes, fetch times, run history. |

## How to load

```python
import polars as pl

# Headline auto trend (note the 2-yr rolling window):
auto = pl.read_parquet("ny_dfs/output/ny_auto_complaints_yearly.parquet")
auto.sort("year")

# Per-company auto ranking, 2024:
auto_co = pl.read_parquet("ny_dfs/output/ny_auto_complaints_company_year.parquet")
auto_co.filter(pl.col("filing_year") == 2024).sort("rank").head(20)

# Health by plan type:
health = pl.read_parquet("ny_dfs/output/ny_health_complaints_yearly.parquet")
health.filter(pl.col("plan_type") == "HMO").sort("year")
```

## How to re-run

```
python3 ny_dfs/scripts/01_download.py    # ~15 sec, ~13 MB total
python3 ny_dfs/scripts/02_parse.py       # ~3-5 min (pdfplumber on 10 PDFs)
```

`01_download.py` always re-fetches; the small auto dataset and 10 small PDFs make incremental mode unnecessary.

## Headline caveats

1. **Auto's rolling-2-year metric** is not directly comparable to TX/CA's annual rates. Sums across `filing_year`s would double-count. Documented in METHODOLOGY.md.
2. **2015 = 2016 in the auto live data** — totals are identical. Likely a year not separately published. Treat one or both as a duplicate.
3. **Health data starts 2015** (the earliest Consumer Guide PDF currently online is the 2016 guide).
4. **Health includes both DFS and DOH (Department of Health) numbers for HMOs.** DFS handles benefits/coverage disputes; DOH handles HMO quality-of-care. Both are upheld by the respective regulator. Our `_dfs` and `_doh` columns are kept separate.
5. **No P&C-non-auto, no life, no surplus lines.** Only auto + health for v1.
6. **Plan-name wrapping**: a few health PDFs have plan names that wrap to a continuation line (e.g., "Highmark Western and Northeastern New York Inc." in the 2025 guide wraps after "Northeastern"). v1 truncates at the wrap; the numeric counts are still correct.

## Headline numbers

From the 2026-05-04 build:

**Auto rolling-2-year upheld complaints (statewide totals):**

| filing_year | upheld_2yr | total_complaints_2yr | n_companies | premium_avg_2yr (M) |
|---:|---:|---:|---:|---:|
| 2009 | 966 | 6,808 | 181 | 9,713 |
| 2014 | 610 | 4,487 | 170 | 11,291 |
| 2015 | 281 | 3,043 | 158 | 12,277 |
| 2016 | 281 | 3,043 | 158 | 12,277 |
| 2019 | 419 | 2,672 | 139 | 14,078 |
| 2022 | 403 | 3,230 | 132 | 15,095 |
| 2023 | 445 | 3,499 | 124 | 16,202 |
| 2024 | **629** | 5,151 | 128 | **18,428** |

(2015 == 2016 in the live data — see METHODOLOGY.md.)

**Health upheld complaints (annual, by plan type) — DFS findings only:**

| year | HMO upheld | EPO/PPO upheld | Commercial upheld |
|---:|---:|---:|---:|
| 2015 | 784 | 1,139 | 79 |
| 2017 | 402 | 2,614 | 68 |
| 2019 | 544 | 1,692 | 73 |
| 2021 | 269 | 1,907 | 49 |
| 2023 | 788 | **3,700** | 77 |
| 2024 | 376 | 3,290 | 71 |

The EPO/PPO line is where the action is — DFS upheld findings rose from ~1,100 (2015) to ~3,300 (2024). The HMO trend is more volatile (probably reflecting market consolidation; n_plans drops from 10 in 2015 to 7 in 2024). Commercial Health stayed roughly flat in absolute terms.
