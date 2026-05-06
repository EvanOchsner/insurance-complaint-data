# NAIC IDRR — state-regulator consumer complaints (1998–2022)

Per-state, per-year counts of **consumer complaints received** by each U.S. state insurance department, plus the corresponding **inquiry counts**, extracted from NAIC's annual *Insurance Department Resources Report* (IDRR), Volume 1.

This is the regulator-side nationwide longitudinal series — the FJC IDB's analogue for "what walked through the door at the state insurance regulator," covering all 50 states, DC, and 5 U.S. territories.

## Scope and headline numbers

- **Coverage:** 1998–2022 (24 years; 2003 is unparseable from the source PDF, see *Caveats*).
- **Granularity:** one row per `(year, jurisdiction)`. 56 jurisdictions max (50 states + DC + American Samoa, Guam, N. Mariana Islands, Puerto Rico, U.S. Virgin Islands).
- **Metrics:** `complaints` (received), `inquiries` (received). NAIC does not break these into "closed/confirmed" buckets at this level — that's the CIS dataset, see *What this is not*.

National totals (illustrative):

| Year | Complaints | Inquiries |
|---:|---:|---:|
| 1998 | 403,815 | 3,548,071 |
| 2002 | 492,600 | 3,706,393 |
| 2010 | 304,455 | 2,141,912 |
| 2018 | 287,641 | 1,632,612 |
| 2022 | 282,567 | 1,516,175 |

The long-run trend is downward: complaint volumes peaked in the early 2000s and have run roughly 250–310k/year since 2010.

## Quick load

```python
import polars as pl
df = pl.read_parquet("naic_idrr/output/naic_idrr_complaints_state_yearly.parquet")
df.filter(pl.col("jurisdiction") == "CA").sort("year")
```

## What this is *not*

NAIC's most-cited "consumer complaints" public data is the **Consumer Information Source (CIS) Closed Complaints** series — broken down by reason / disposition / coverage type — *not* the IDRR. The IDRR's per-state numbers are a self-reported workload count (everything that came in the door), while CIS surfaces only the subset that closed and was confirmed against the insurer.

The CIS data lives in three Tableau dashboards on `tableau.naic.org`. v1 captures the wrapper HTML for provenance but does **not** extract the underlying tables — that requires implementing Tableau's `bootstrapSession` protocol. See [`PROVENANCE.md`](PROVENANCE.md#cis-tableau-dashboards-snapshots-only--data-not-extracted) for the URLs and v2 path.

## How to reproduce

```sh
# Phase 1: download all IDRR PDFs + CIS dashboard HTML snapshots
python3 naic_idrr/scripts/01_download.py
# → naic_idrr/interim/idrr/<year>.pdf (+ manifest.json with sha256 per file)
# → naic_idrr/interim/cis/{by_reason,by_disposition,by_coverage}.html

# Phase 2: parse the IDRR PDFs to long-format parquet + csv
python3 naic_idrr/scripts/02_parse.py
# → naic_idrr/output/naic_idrr_complaints_state_yearly.{parquet,csv}
# → naic_idrr/output/run_log.txt (appended sanity log)

# Phase 3: republish in the cross-state aggregate schema
python3 naic_idrr/scripts/03_canonicalize.py
# → naic_idrr/output/idrr_complaints_yearly.{parquet,csv}    (50 states + DC, territories dropped)
# → naic_idrr/output/tail_states_coverage.csv                 (per-tail-state coverage cross-walk)
```

Both scripts are idempotent and reproduce the snapshot recorded in `interim/manifest.json`. Parser-induced data drops are gated behind a 5%-tolerance check against each PDF's printed national Total row — see [`scripts/02_parse.py`](scripts/02_parse.py).

## Caveats — read before plotting

1. **"Complaints received," not "complaints upheld."** This is workload, not regulator finding. A state that's aggressive about logging informal consumer contacts will have higher numbers than a state with the same actual insurer behavior. Use the CIS taxonomy (when v2 lands) for confirmed/disposition outcomes.
2. **Inquiries are not bad-behavior signals.** They are pre-complaint research questions. Included in the dataset for context but should generally be excluded from "insurer behavior" plots.
3. **State methodology varies.** Some states count auto-claim disputes the carrier handles internally; others don't. Some include Medicaid / Medicare supplement complaints; others route those elsewhere. Cross-state ratios are *suggestive* not authoritative.
4. **2003 is missing.** The 2003 IDRR PDF is laid out in two columns side-by-side, and `pdfplumber` interleaves rows from both columns into a single text stream. The data could be recovered with bbox-aware extraction; v1 doesn't bother.
5. **1998–2002 numbers may be noisy at ±0.5%.** A handful of rows in those years have small parser-vs-PDF-Total discrepancies. Acceptable for trend analysis; not for headline-level citations.
6. **Pre-1998 PDFs are scanned at low DPI.** The earliest IDRR PDFs (1986–1993) are scanned bitmaps with poor OCR; the parser skips them with a logged warning. Recovering those would require an OCR pass (Tesseract) — out of scope.
7. **NAIC IDRR is published in year *N+1* with year *N*'s data.** The parser uses the data year from the table title, not the publication year from the file's archive label.

## Data dictionary

| Column | Type | Description |
|---|---|---|
| `year` | int32 | Calendar year the complaints/inquiries were received (data year, not publication year) |
| `jurisdiction` | string | Postal-style code: 50 states + DC + AS / GU / MP / PR / VI |
| `jurisdiction_name` | string | Full name as printed in the IDRR (e.g. "Dist. of Columbia", "U.S. Virgin Islands") |
| `complaints` | int64? | Consumer complaints received by the state insurance department in that year. Null if dashed in source. |
| `inquiries` | int64? | Consumer inquiries received. Null if dashed. |

## Visualization

This dataset surfaces in the unified viewer at [`viz/index.html`](../viz/index.html) under the "regulator findings" category. Manifest at [`viz_manifest.json`](viz_manifest.json).
