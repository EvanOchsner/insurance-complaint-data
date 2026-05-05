# Idaho DOI — per-company complaint index, by line and year

Per-company complaint index data from the Idaho Department of Insurance *Consumer Complaint Comparison Tables*. One row per `(year, line, company)`, with Idaho's published complaint index, market share, premium, and complaint count.

NAIC-tradition complaint index — same metric class as [`in_idoi/`](../in_idoi/) and [`ks_kid/`](../ks_kid/). Lives under the "Regulator complaint indexes" viz category.

## What's in this folder

| Path | What it is |
|---|---|
| `output/id_complaints_company_yearly.parquet` (and `.csv`) | **Headline.** One row per `(year, line, company)`. Columns: `company_name, premium, market_share, complaints, complaint_index`. |
| `output/id_complaints_yearly.parquet` (and `.csv`) | Per `(year × line)` aggregate. Columns: `total_complaints, n_companies, median_index, market_share_covered, total_premium`. |
| `output/run_log.txt` | Append-only log: per-run row counts and any in-source quirks corrected. |
| `scripts/01_download.py` | Fetch the landing-page HTML. |
| `scripts/02_parse.py` | BeautifulSoup parse + canonical line-slug normalization + per-row column-swap correction. |
| `interim/landing.html` | Raw HTML. **Gitignored.** |
| `interim/manifest.json` | Fetch metadata. |
| `METHODOLOGY.md` | Complaint-index definition, line slugs, coverage caveats. |
| `PROVENANCE.md` | Source URL + sha256. |

## How to load

```python
import polars as pl
df = pl.read_parquet("id_doi/output/id_complaints_company_yearly.parquet")
df.filter((pl.col("year") == 2020) & (pl.col("line") == "auto")).sort("complaint_index", descending=True)
```

## How to re-run

```
python3 id_doi/scripts/01_download.py     # < 5 s
python3 id_doi/scripts/02_parse.py        # < 5 s
```

## Headline caveats

1. **Same metric class as IN IDOI and KS KID; not directly comparable to TX/CT/MD counts.** Complaint index = `(share of complaints) / (share of premium)`, normalized so 1.0 = parity.
2. **Top-20 premium writers per line per year.** Smaller carriers don't appear. Many top-20 entries have 0 complaints in a given year (Idaho is a small market), so the median index per slice is often 0.
3. **5 rows in 2018 Individual Accident/Health had swapped Complaints/Index columns at source.** The parser auto-detects (decimal in Complaints + integer in Index) and corrects. The run log records the count.
4. **Coverage is short: 2018–2020.** The DOI page hasn't been refreshed since the 2020 data was published. Compare to IN (2009–2024) and KS (2020–2024).
5. **Group vs Individual Accident/Health are kept distinct.** Idaho uses separate `group_health` and `individual_health` line slugs; IN folds health into one slug; KS uses a single `health` slug. Cross-state rollups should account for this if needed.

## Headline numbers (sanity check)

From the 2026-05-04 build:

- 240 per-company rows (3 years × 4 lines × top-20).
- 12 (year × line) slices, all populated.
- Median complaint index across slices: 0.00 — most top-20 premium writers in a small state had 0 complaints in any given year.
- Auto 2020 top-3 complaint indexes: Bristol West (10.84), Viking WI (10.29), Progressive Direct (3.86).
