# Florida Civil Remedy Notice (CRN) — yearly counts by line of insurance

Year-by-year counts of Civil Remedy Notices filed with the Florida Department of Financial Services, broken out by type of insurance. Florida is the only US state with a public statewide registry of pre-litigation bad-faith notices (Fla. Stat. § 624.155 requires plaintiffs to file a CRN at least 60 days before suing). FDFS exposes a searchable web app but no API and no bulk download.

## ⚠️ FL CRN data is conceptually different from MD/TX/CA regulator data

A CRN is a **plaintiff-side allegation** (or, almost always, an allegation by a plaintiff's attorney). It is **not** a regulator finding that the insurer acted improperly. Many CRNs are routine claims-handling tactics that never produce litigation; many are "cured" by the insurer within 60 days and become moot.

For this reason, FL CRN counts should not be plotted on the same axis as TX `Confirmed` or CA `Justified` counts. They measure **litigation pressure**, not insurer wrongdoing per se. The cross-state visualization in this project keeps FL on its own panel.

This is captured in METHODOLOGY.md and surfaced in every other doc.

## What's in this folder

| Path | What it is |
|---|---|
| `output/fl_crn_yearly_total.parquet` (and `.csv`) | One row per year. `year, count` (total CRNs across all lines). |
| `output/fl_crn_yearly_counts.parquet` (and `.csv`) | One row per `(year, type_of_insurance)`. ~22 years × 9 lines ≈ 200 rows. |
| `output/run_log.txt` | Appended each run: timestamps, request count, per-year totals. |
| `scripts/01_crawl_counts.py` | Iterates `(year, line)` and reads the FDFS search result header to record counts. |
| `interim/manifest.json` | Run metadata. |
| `public_records_request.md` | Template for getting a bulk per-filing CSV from FDFS. The path to extend this dataset beyond counts. |
| `METHODOLOGY.md` | Why CRNs ≠ regulator findings; what's not in here. |
| `PROVENANCE.md` | URL, search-form schema, request log, run history. |

## How to load

```python
import polars as pl

# Yearly total (the headline plot):
df = pl.read_parquet("fl_crn/output/fl_crn_yearly_total.parquet")
df.sort("year")

# By line:
by_line = pl.read_parquet("fl_crn/output/fl_crn_yearly_counts.parquet")
by_line.filter(pl.col("type_of_insurance") == "Auto").sort("year")
```

## How to re-run

```
python3 fl_crn/scripts/01_crawl_counts.py
```

Takes ~8 minutes (~242 polite HTTP requests at 2-second spacing). Each run is a fresh crawl — no incremental mode. If FDFS updates historical filings, re-running will pick up the changes.

## Headline caveats

1. **A CRN is not a finding of bad faith.** Document this every time you cite the data.
2. **Hurricane-driven volume** is real. Irma (Sep 2017), Ian (Sep 2022), and Helene/Milton (2024) produce visible spikes — context, not noise.
3. **AOB litigation era (2014–2022)** inflated CRN counts massively in residential property. House Bill 7065 (2019) and SB 2A (2022) reformed AOB and changed the trajectory.
4. **The system became digital around 2014.** Pre-2014 years return 0 from the search interface; that doesn't mean zero CRNs were filed — just that the digital archive doesn't reach earlier.
5. **Counts only.** This dataset has no per-filing detail (insurer name, statute, reason, attorney, response). Per-filing requires a public records request — see `public_records_request.md`.
6. **§ 627.70152 property pre-suit notices are NOT in this dataset.** Those are a separate, post-2021 system. CRNs and 627.70152 notices serve different purposes; do not conflate.

## Headline numbers

From the 2026-05-04 crawl:

| Year | Total CRNs | Auto | Residential P&C | Notes |
|---:|---:|---:|---:|---|
| 2003-2013 | 0 each | – | – | Digital archive doesn't reach earlier |
| 2014 | 16,249 | – | – | First non-zero year |
| 2015 | 28,572 | – | – | |
| 2016 | 27,765 | – | – | |
| 2017 | 38,903 | – | – | Hurricane Irma (Sep 2017) |
| 2018 | 47,504 | 30,338 | 14,563 | |
| 2019 | 52,475 | 31,580 | 18,344 | HB 7065 AOB reform |
| 2020 | 63,850 | – | – | |
| 2021 | **69,203** | – | – | Peak; AOB litigation era apex |
| 2022 | 60,525 | – | – | Hurricane Ian (Sep 2022); SB 2A reform |
| 2023 | 65,251 | 37,857 | 24,796 | Ian aftermath in Residential P&C |
| 2024 | 62,320 | 42,469 | 17,636 | Helene/Milton (Sep–Oct) |
| 2025 | 61,828 | 46,785 | 12,260 | |
| 2026 | 18,369 | 14,075 | 3,526 | partial — through fetch date |

Auto dominates throughout (~60–75% of total). Residential P&C is the swing line — driven by hurricanes and the AOB litigation era. Health, Life, and the smaller lines combined never exceed ~3% of yearly volume.

**Compared to TX confirmed-complaint volume** (~15K-20K/year): FL CRNs run ~4x higher in absolute count, but they measure a different thing (plaintiff allegations, not regulator findings) — see METHODOLOGY.md.
