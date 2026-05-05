# Federal civil insurance filings (Nature of Suit 110), by state and year

Counts of federal civil cases coded **Nature of Suit = 110 ("Insurance")** filed in U.S. district courts, broken out by state and calendar year of filing, derived from the Federal Judicial Center's Integrated Database (IDB).

This is the federal-court lens on insurance litigation pressure. State-court filings are not in this dataset and are out of scope here; that's a separate (per-state) collection effort.

## What's in this folder

| Path | What it is |
|---|---|
| `output/insurance_filings_by_state_year.parquet` (and `.csv`) | One row per `(state, year)`: count of NoS=110 filings. **Primary deliverable.** |
| `output/insurance_filings_by_state_year_origin.parquet` (and `.csv`) | Same, but split by `ORIGIN` (original filing vs removed-from-state-court vs other). Use this if you care about the removal-vs-original split. |
| `output/run_log.txt` | Appended each run: timestamps, row counts, sanity checks, headline yearly totals. |
| `scripts/01_download.py` | Fetches the FJC IDB combined civil zip, records SHA-256 and Last-Modified to `interim/manifest.json`. |
| `scripts/02_extract_and_aggregate.py` | Filters NoS=110, joins district→state, writes the four output files. |
| `scripts/districts.csv` | The 94 federal judicial districts mapped to 2-letter state postal codes. **Single source of truth** for the state mapping. Hand-curated; verified against `reference/office-codes.xlsx`. |
| `reference/` | Source-of-record documents (research guide, NoS code descriptions, FJC office codes, field-length spec). |
| `interim/` | Raw download zip, unzipped txt, and the download manifest. **Gitignored** — large and reproducible from the scripts. |
| `METHODOLOGY.md` | How counts are produced, what's included/excluded, caveats. |
| `PROVENANCE.md` | Source URL with verified date, file hashes, fetch timestamps, codebook gap notes. |

## How to load the data

```python
import polars as pl
df = pl.read_parquet("fjc_idb/output/insurance_filings_by_state_year.parquet")
df.filter((pl.col("state") == "MD") & (pl.col("year") >= 2018))
```

Or the origin-split version:

```python
df = pl.read_parquet("fjc_idb/output/insurance_filings_by_state_year_origin.parquet")
# Removal share by year, nationwide:
df.group_by("year").agg(
    pl.col("count").sum().alias("total"),
    pl.col("count").filter(pl.col("origin_code") == 2).sum().alias("removed"),
).with_columns(removal_share=pl.col("removed") / pl.col("total")).sort("year")
```

## How to re-run end-to-end

From the project root, with Python 3.10+ and `polars` installed:

```
python fjc_idb/scripts/01_download.py        # ~5 min, ~310 MB download
python fjc_idb/scripts/02_extract_and_aggregate.py   # ~10 sec
```

Re-running `01_download.py` is idempotent — it short-circuits if the local zip's sha256 still matches the server's `Last-Modified`/`ETag`. To force a refetch, delete `interim/manifest.json` first.

## Headline caveats — read this before plotting

1. **NoS=110 ≠ "bad faith".** The Insurance NoS code covers contract disputes, tort claims related to insurance, subrogation, etc. — broader than bad faith specifically. We are tracking *insurance litigation pressure*, not bad-faith filings.
2. **Federal court only.** Many insurance cases (and most bad-faith cases) are filed and stay in state court. Those don't appear here. Cases removed *to* federal court do appear, with `origin_code = 2`.
3. **The most recent year is partial.** The IDB has roughly a 2-month reporting lag; a calendar year present in the data is only complete once the IDB has been refreshed past March of the following year. Treat the trailing year as preliminary.
4. **NoS-110 undercounts insurance-flavored cases coded elsewhere** (e.g., NoS 791 ERISA, 360 Other PI, 190 Other Contract). v1 holds the line at NoS=110 and accepts the undercount.
5. **Origin code labels for codes ≥7 are conservative.** The FJC civil codebook PDF was not at a reliably guessable URL when this dataset was built (see PROVENANCE.md). Codes 1-6 are well-documented and load-bearing; codes 7-13 are rare (well under 1% combined) and labeled generically as "Other / subsequent codebook variant" pending codebook verification.
6. **Territories included.** Output includes Puerto Rico, the Virgin Islands, Guam, and the Northern Mariana Islands (postal codes `PR`, `VI`, `GU`, `MP`). Filter them out for "50 states + DC" plots.

See `METHODOLOGY.md` for the rationale behind each of these.

## Headline numbers (for sanity check)

From the run that produced the committed Parquet files:

- 38 years covered: 1988–2025 (2025 partial)
- 55 jurisdictions: 50 states + DC + 4 territories
- 2,051 `(state, year)` rows in the headline output
- 372,547 federal NoS=110 filings counted (post-1988 filter applied)
- Most: Louisiana (46k), Texas (42k), California (33k), Florida (30k), Pennsylvania (22k)
- Removal share trend: ~38% in 1988 → ~58% in 2025 (insurer-driven removals trending up)
