# Connecticut CID consumer complaints — by year, coverage, and disposition

Closed insurance consumer complaints from the Connecticut Insurance Department, by calendar year of close. Each row carries CID's `disposition` (the regulator's resolution of the complaint), which we group into three buckets: `against_insurer` (regulator action favored consumer), `for_insurer` (regulator confirmed insurer position), `ambiguous` (no clear finding).

This is CT's analogue to TX TDI's `Confirmed`/`Not Confirmed` series and MD MIA's "in favor of insured" series. CT does not publish a clean binary like TX, so the three-bucket mapping is a methodology choice — see [`METHODOLOGY.md`](METHODOLOGY.md).

## What's in this folder

| Path | What it is |
|---|---|
| `output/ct_complaints_yearly_confirmed.parquet` (and `.csv`) | **Headline.** One row per `(year_closed, coverage)` plus an `ALL` row per year. Columns: `total, against_insurer, for_insurer, ambiguous, no_disposition, against_rate_of_decided, against_rate_of_total`. |
| `output/ct_complaints_yearly.parquet` (and `.csv`) | Multi-dim pivot — one row per `(year_closed, coverage, disposition)` with a count. |
| `output/ct_complaints_complaint_level.parquet` (and `.csv`) | One row per closed complaint, all CID-native fields plus parsed dates and derived bucket. Use for ad-hoc analysis. |
| `output/run_log.txt` | Appended each run: timestamps, row counts, sanity tables. |
| `scripts/01_pull.py` | Paginated Socrata fetch → `interim/t64r-mt64.parquet` + manifest. |
| `scripts/02_aggregate.py` | Parse, derive `year_closed`, classify dispositions, write the three output files. |
| `interim/` | Raw API pull and `manifest.json`. **Gitignored.** |
| `METHODOLOGY.md` | Bucket mapping; calendar-year-of-close; what's not in here. |
| `PROVENANCE.md` | Source URL with date verified; pull manifest; row counts; run log. |

## How to load

```python
import polars as pl

# Headline yearly trend (just the "ALL" rows):
df = pl.read_parquet("ct_cid/output/ct_complaints_yearly_confirmed.parquet")
df.filter(pl.col("coverage") == "ALL").sort("year_closed")

# By-coverage trend:
df.filter((pl.col("coverage") != "ALL") & (pl.col("year_closed") >= 2022))

# Complaint-level:
cl = pl.read_parquet("ct_cid/output/ct_complaints_complaint_level.parquet")
cl.filter(pl.col("year_closed") == 2025).group_by("reason").len().sort("len", descending=True)
```

## How to re-run

```
python3 ct_cid/scripts/01_pull.py        # ~10 s, ~0.7 MB parquet
python3 ct_cid/scripts/02_aggregate.py   # < 5 s
```

`01_pull.py` always does a fresh full pull (~77k rows). `interim/manifest.json` records the fetch timestamp and the server's `rowsUpdatedAt`.

## Headline caveats

1. **Effective coverage starts ~2022.** The dataset has rows back to 2018-01-09, but pre-2022 is sparse: 66 (2018), 59 (2019), 84 (2020), 212 (2021) closed complaints — versus 10k–20k/year from 2022 onward. CID appears to have begun loading every closed complaint into the open-data feed in 2022. Treat 2018–2021 as backfill, not steady-state.
2. **`against_insurer` is a derived bucket, not a CID native field.** CID publishes a free-form `disposition` column; we group its values into three buckets per [`METHODOLOGY.md`](METHODOLOGY.md). The bucket mapping is the methodology contract; if a previously-unseen `disposition` value appears, the build fails by design.
3. **~40% of closed rows have null `disposition`.** Even on `status='Closed'` rows, the `disposition` field is null for ~40% across all years. We track these in the `no_disposition` column and exclude them from the `against`/`for` numerator/denominator. The `against_rate_of_decided` denominator is `against + for`; `against_rate_of_total` divides by everything including no_disposition rows.
4. **The temporal anchor is `closed`** (calendar year of close, CID's column name). The `opened` date is also in the complaint-level file.
5. **The most recent year is partial.** Data through `2026-05-01` at the time of the first build. Treat the trailing year as preliminary.
6. **`A & H` and `Group` cover most of the volume.** Accident & Health (22k rows of 75k closed) and Group health (14k) together are ~50% of closed complaints. Auto (`Individual Private Passenger`) is third at ~13k. Workers' compensation is small here for the same reason as TX — most WC adjudication routes to a separate workers'-comp authority.
7. **No per-company breakdown in the headline.** Per-company data is in the complaint-level file (`company`, `naic_code` columns); aggregating to a per-company yearly is straightforward but deferred to v2.

## Headline numbers (for sanity check)

From the 2026-05-04 build (sha-stable as long as the source dataset doesn't change):

- 75,045 closed complaints from 2018-01-09 through 2026-05-01.
- 2022+ is the steady-state series. Top coverages 2024: A&H (6.1k), Group (4.3k), Individual Private Passenger (3.3k), Individual life (2.4k).
- **Against-insurer rate (of decided), ALL coverages:**
  | Year | Closed | Against | For | Decided | Rate (of decided) |
  |---:|---:|---:|---:|---:|---:|
  | 2022 | 10,579 | 2,166 | 3,089 | 5,255 | 41.2% |
  | 2023 | 15,751 | 3,892 | 3,710 | 7,602 | 51.2% |
  | 2024 | 19,988 | 4,909 | 5,427 | 10,336 | 47.5% |
  | 2025 | 19,184 | 3,772 | 5,275 | 9,047 | 41.7% |
  | 2026 (partial) | 9,122 | 1,781 | 2,186 | 3,967 | 44.9% |
