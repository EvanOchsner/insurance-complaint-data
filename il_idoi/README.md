# Illinois IDOI — per-company complaint ratio, by line and year

Per-company complaint-ratio data from the Illinois Department of Insurance *Consumer Complaint Ratio Reports*. NAIC-tradition complaint index, same metric class as IN/KS/ID.

**Important caveat:** IL changed its ratio definition between 2018 and 2019, and the denominator varies by line. The output preserves both ratio types in a `ratio_type` column. See [METHODOLOGY](METHODOLOGY.md).

## What's in this folder

| Path | What it is |
|---|---|
| `output/il_complaints_company_yearly.parquet` (and `.csv`) | **Headline.** One row per `(year, line, company)`. Columns: `naic_code, company_name, complaints, premium, market_share, complaint_share, ratio, ratio_type, source_file`. |
| `output/il_complaints_yearly.parquet` (and `.csv`) | Per `(year × line)` aggregate. Columns: `total_complaints, n_companies, median_ratio, total_premium`. |
| `output/run_log.txt` | Append-only log: per-file row counts and skipped-line counts. |
| `scripts/01_download.py` | Fetch 5 consolidated ratio-report PDFs (2018, 2019, 2020, 2023, 2024). |
| `scripts/02_parse.py` | Dual-layout parser (content-based dispatch). |
| `interim/` | Raw PDFs + manifest. **Gitignored.** |
| `METHODOLOGY.md` | Both ratio definitions, line-specific denominators. |
| `PROVENANCE.md` | Source URLs + per-file hashes + run log. |

## How to load

```python
import polars as pl
df = pl.read_parquet("il_idoi/output/il_complaints_company_yearly.parquet")

# Per-company by ratio type:
df.group_by("ratio_type").agg(pl.len().alias("rows"))

# Auto top-10 by ratio in 2024 (per $1M EP definition):
df.filter((pl.col("year") == 2024) & (pl.col("line") == "auto")).sort("ratio", descending=True).head(10)
```

## How to re-run

```
python3 il_idoi/scripts/01_download.py        # ~5 s
python3 il_idoi/scripts/02_parse.py           # < 10 s
```

## Headline caveats

1. **Two ratio definitions.** 2018 = `complaint share / market share` (NAIC standard, ~1.0 parity). 2019+ = `complaints per $1M earned premium` for P&C, `per 10k policies in force` for Life, `per 10k members` for HMO/health. The `ratio_type` column tells you which.
2. **No 2021 / 2022 ratio reports.** IL published only "summary" reports (counts only) for those years; the ratio reports skip 2021/2022. Coverage years: 2018, 2019, 2020, 2023, 2024.
3. **Denominator varies by line.** Even within 2019+ data, the ratio's denominator changes per line. Don't compare auto's "0.32" against life's "1.93" — different units.
4. **Reason-code columns not extracted in v1.** 2019–2020 has 6 reason-code columns; 2023–2024 has 4. Inconsistent enough that v1 skips them; they remain in the source PDFs.
5. **Some company-name rows wrap to two lines and are skipped.** ~100–250 lines skipped per file (mostly headers/footers/wraps). Logged in run_log.txt.

## Headline numbers (sanity check)

From the 2026-05-04 build:

- 5 source PDFs (2018, 2019, 2020, 2023, 2024).
- 2,671 per-company rows across 29 (year × line) slices.
- Years: 2018 (most lines, 7), then 2019/2020 (6 each), 2023/2024 (5 each).
- Lines: auto, homeowners, life, annuity, individual_health, group_health, hmo (2018–2020); auto, homeowners, life, annuity, health (2023–2024).
- Median ratio for auto stays ~0.3–0.4 in the new ratio_type — directly comparable across 2019+ years for auto.
