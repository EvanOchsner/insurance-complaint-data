# California CDI insurance complaints — by year, line, company, and "Justified"

Two source streams from the California Department of Insurance, distilled to year-by-year tables of complaint volume and regulator outcomes.

CDI publishes no API and no bulk data download. Everything here is parsed from PDFs that CDI publishes annually:

- **Annual Report of the Insurance Commissioner** — gives state-level totals (`Complaint Cases Closed`, `Complaint Cases Opened`) plus a "Percentage of Complaints by Lines of Coverage" multi-year table. 5 PDFs cover 2020-2024.
- **Consumer Complaint Study** (Auto/Home/Life, one PDF per line per study year) — gives per-company rolling-3-year `Justified Complaint Ratio` and `Number of Justified Complaints`. 3 study years × 3 lines × 3 trailing years cover 2020-2024.

CDI's `Justified Complaint` finding is conceptually equivalent to TX's `Confirmed`: the regulator determined the insurer violated a statute, regulation, or contract.

## What's in this folder

| Path | What it is |
|---|---|
| `output/ca_complaints_state_yearly.parquet` (and `.csv`) | One row per year (2020-2024). Columns: `complaints_opened, complaints_closed, consumer_dollars_recovered, telephone_and_in_person_assistance`. |
| `output/ca_complaints_state_by_line_pct.parquet` (and `.csv`) | `(year, coverage_type, percentage, source_ar_year)`. Eight CDI-native coverage lines × ~8 years (deduped: latest AR wins per `(year, coverage_type)`). |
| `output/ca_complaints_company_yearly.parquet` (and `.csv`) | Per-company panel from the Consumer Complaint Studies. `(year, line, rank_in_study, company_canonical, company_name, exposure, justified_ratio, justified_count, study_year)`. Deduped by `(year, line, company_canonical)` keeping the most recent study year. |
| `output/ca_complaints_yearly_justified.parquet` (and `.csv`) | **Headline aggregate.** `(year, line, source_study_year, total_justified_top50, total_exposure_top50, n_companies, justified_per_100k_exposure)`. For each `(year, line)` the values come from the most recent CDI study covering that year — exactly 50 companies. |
| `output/run_log.txt` | Appended each run. |
| `scripts/01_download.py` | Fetches the 14 PDFs (5 ARs + 9 composites) into `interim/`. Verifies `Content-Type: application/pdf` because CDI returns HTTP 200 with an HTML 404 page for missing files. |
| `scripts/02_parse.py` | Parses both PDF families and writes the four output files. |
| `interim/` | Raw PDFs + `manifest.json`. **Gitignored.** |
| `METHODOLOGY.md` | What "Justified" means; rolling-window choice; what's not in here. |
| `PROVENANCE.md` | URLs, SHA-256 hashes, fetch timestamps, run history. |

## How to load

```python
import polars as pl

# State headline (5 years):
state = pl.read_parquet("ca_cdi/output/ca_complaints_state_yearly.parquet")

# Headline justified-rate trend by line (the closest to TX's confirmed_rate):
agg = pl.read_parquet("ca_cdi/output/ca_complaints_yearly_justified.parquet")
agg.filter(pl.col("line") == "auto").sort("year")

# Per-company drill-down (e.g., State Farm Auto over time):
co = pl.read_parquet("ca_cdi/output/ca_complaints_company_yearly.parquet")
co.filter(
    (pl.col("line") == "auto")
    & pl.col("company_canonical").str.contains("STATE FARM MUTUAL AUTOMOBILE")
).sort("year")
```

## How to re-run

```
python3 ca_cdi/scripts/01_download.py    # ~30 sec, ~17 MB of PDFs
python3 ca_cdi/scripts/02_parse.py       # ~70 sec (pdfplumber on 14 PDFs)
```

`01_download.py` always re-fetches; CDI doesn't expose ETags reliably and the file count is small. `interim/manifest.json` records SHA-256 of every PDF so you can compare runs.

## Headline caveats

1. **`Justified` ≠ "won bad-faith lawsuit".** Per CDI's published definitions (CCR Title 10, Subchapter 7.4), Justified means the licensee acted in contravention of statute, regulation, or contract. Many complaints found Justified are administrative; many bad-faith lawsuits never appear here.
2. **The headline aggregate covers only the top 50 insurers per line.** Smaller carriers' justified complaints are not summed in the per-line totals; this is by construction (CDI only publishes the top 50). Treat `total_justified_top50` as a lower bound on CA-wide justified complaints in the line.
3. **Coverage is 2020-2024 only.** The Consumer Complaint Study archive on the CDI site only retains the last 3 study years, and the earliest archived Annual Report is 2020. Older data would require Wayback Machine or FOIA.
4. **The `exposure` column is approximate and snapshotted as of the most recent year of each study.** When a year is sourced from a study published a few years later, the exposure value reflects the company's market presence then, not in the data year. The published `justified_per_100k_exposure` is CDI's own metric using its own contemporaneous denominators; we re-derive it from the summed values for transparency.
5. **The `state_yearly` table reflects all complaints (regardless of finding); the `yearly_justified` table reflects just the regulator-found-against-insurer count.** They aren't the same denominator. CA does not publish a state-wide "% of complaints found Justified" headline.
6. **Health complaints are systematically undercounted.** Most managed-care complaints in CA go to DMHC (a separate agency); CDI's health complaint data captures only the indemnity-health subset. A consolidated view requires the CDII Complaint Data Reports (out of scope for v1).

## Headline numbers

From the 2026-05-04 build:

**State-level total complaints closed:**

| Year | Closed | Opened | Consumer $ Recovered |
|---:|---:|---:|---:|
| 2020 | 44,535 | 42,212 | $136,792,347 |
| 2021 | 41,181 | 41,297 | $123,669,419 |
| 2022 | 44,712 | 44,947 | $133,035,994 |
| 2023 | 56,827 | 58,525 | $129,868,724 |
| 2024 | 62,002 | 62,559 | $124,407,106 |

**Top-50 justified complaints per 100k exposure (lower is better for consumers in absolute terms; rising means the regulator is increasingly finding in their favor):**

| Year | Auto | Home | Life |
|---:|---:|---:|---:|
| 2020 | 2.81 | 2.80 | 1.04 |
| 2021 | 3.26 | 3.30 | 1.02 |
| 2022 | 3.25 | 2.71 | 1.07 |
| 2023 | 3.33 | 5.68 | 1.03 |
| 2024 | 4.98 | **10.58** | 1.14 |

The home-insurance jump (2.80 → 10.58, 3.8x in 4 years) is the most striking signal — coincident with the CA insurance crisis around wildfire risk and FAIR Plan stress.
