# Colorado DOI — workload + recoveries by line

Two streams from the Colorado Division of Insurance (DOI) annual reports for FY 2021-22 through FY 2024-25:

1. **Per-line workload** — annual count of consumer complaints (or complaints + inquiries) received and closed, broken into P&C, L&H, plus homeowners and health sub-lines for years 2024+.
2. **Per-line recoveries** — dollar amounts the DOI extracted from carriers and returned to consumers, broken into homeowners / auto / health / life+annuity / other categories. The recovery $ represent the only published "regulator finding" signal CO emits.

CO does NOT publish per-company complaint indexes in PDF form (an Oracle-backed interactive tool exists separately and is out of scope for v1). Built into the index-batch because the original plan grouped it there; viz category is `regulator_finding` rather than `regulator_complaint_index`.

## What's in this folder

| Path | What it is |
|---|---|
| `output/co_workload_yearly.parquet` (and `.csv`) | Per `(fiscal_year, line, count_type)` workload row. Columns: `fiscal_year, line, count, count_type, source_file`. count_type ∈ `received` / `closed` / `received_with_inquiries`. |
| `output/co_recoveries_yearly.parquet` (and `.csv`) | Per `(fiscal_year, line)` money-recovered row. Columns: `fiscal_year, line, amount_usd, source_file`. |
| `scripts/01_download.py` | Fetch 4 PDFs (Chrome UA). |
| `scripts/02_build.py` | Emit parquets from inline hand-verified values. |
| `interim/files/FY{YYYY}.pdf` | Raw PDFs for audit. **Gitignored.** |
| `interim/manifest.json` | Per-file SHA-256 + Last-Modified + fetched-at. |
| `METHODOLOGY.md` | What "received" / "closed" / "recoveries" mean per CO; FY semantics; line-slug normalization. |
| `PROVENANCE.md` | Source URLs, per-file hashes, page-by-page citations of inline values. |

## How to load

```python
import polars as pl

# Workload time series:
wk = pl.read_parquet("co_doi/output/co_workload_yearly.parquet")
wk.filter(pl.col("count_type") == "received").pivot(
    index="fiscal_year", on="line", values="count"
).sort("fiscal_year")

# Recoveries time series:
rc = pl.read_parquet("co_doi/output/co_recoveries_yearly.parquet")
rc.filter(pl.col("line") == "total").sort("fiscal_year")
```

## How to re-run

```
python3 co_doi/scripts/01_download.py     # ~10 s (4 PDFs at 1 req/s)
python3 co_doi/scripts/02_build.py        # < 5 s
```

Hand-verified inline data — no parser to break. Adding a future year is a 1-line edit to `02_build.py` (plus a fresh PDF for provenance).

## Headline caveats

1. **FY 2025 framing change.** The FY 2024-25 report reframes "complaints received" as "complaints AND inquiries received." The `count_type` column distinguishes — don't mix `received` and `received_with_inquiries` rows when computing year-over-year deltas.
2. **Recovery breakdown categories shift year-to-year.** Marshall Fire appears only in FY 2023; Other P&C appears only in FY 2025; sub-line splits (homeowners / auto / health / life+annuity) only appear consistently from FY 2024 onward.
3. **Workload sub-line counts are sparse pre-FY 2024.** Earlier reports give only P&C and L&H aggregates without per-line splits.
4. **Recoveries are not regulator findings in the strict sense.** They're dollar amounts the DOI helped recover — a directional indicator of insurer-action-required outcomes, but not a per-complaint disposition. Don't fold these into the canonical 4-bucket outcome taxonomy.
5. **CO fiscal year ends June 30.** "FY 2025" = July 1, 2024 – June 30, 2025.
6. **No per-company data here.** CO publishes per-company complaint indexes via an Oracle-backed interactive tool (separate URL); not in v1.
7. **Hand-verified inline data, not parsed.** Source PDFs are downloaded and sha256-anchored in `interim/manifest.json`, but the values come from a hand-verified inline table in `02_build.py`. PDFs are inconsistent enough across years that a unified parser wasn't worth the complexity for 4 rows.

## Headline numbers (sanity check)

From the 2026-05-04 build:

| FY | P&C received | L&H received | Total recovered | Homeowners $ | Auto $ | Health $ | Life+annuity $ |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2022 | — (not split) | — (not split) | $19.6M | — | — | — | — |
| 2023 | 3,300 | 2,620 | $21.5M | (Marshall $3.8M / other $9.8M) | — | $5.0M | $3.0M |
| 2024 | 3,829 | 1,929 | $26.5M | $10.6M | $5.0M | $4.1M | $3.2M |
| 2025 | 3,505¹ | 1,511¹ | $17.6M | $5.8M | $3.9M | $3.0M | $4.2M |

¹ FY 2025 numbers include inquiries; not strictly comparable to FY 2023/2024 "received" counts.
