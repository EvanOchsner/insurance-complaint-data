# Maryland MIA — §27-1001 first-party bad-faith complaint dispositions (FY 2008–FY 2025)

Per-fiscal-year disposition data for first-party bad-faith complaints filed with the Maryland Insurance Administration under Md. Insurance Article §27-1001(h). Each fiscal year is broken into four outcome buckets — settled/withdrawn, no violation (insurer wins), breach to pay only (partial finding for insured), and bad-faith violation (insurer at fault).

This is the cleanest 4-bucket regulator-finding dataset in the project; it serves as the **canonical model** for the cross-state outcome taxonomy used in the unified viewer. See [`SUPPLIED_README.md`](SUPPLIED_README.md) for the full curatorial notes.

## What's in this folder

| Path | What it is |
|---|---|
| `output/md_complaints_yearly.parquet` (and `.csv`) | **Headline.** One row per fiscal year. Columns: `fy, total, settled_wd_dismissed, no_violation, breach_pay_only, bad_faith, on_merits, pct_insured_wins, pct_any_insured_finding, source`. |
| `data.csv` | The same table as a flat CSV — supplied verbatim by the curator. |
| `chart.png` / `chart.pdf` | The supplied static chart (with MD-specific commissioner-tenure overlay). Historical artifact; the unified viewer renders MD using its own consistent style (no commissioner overlay). |
| `source_reports/FY{YYYY}.pdf` | The 18 original MIA annual reports under §27-1001(h). |
| `scripts/build.py` | Project-canonical builder; writes the parquet + csv from the hand-curated inline data table. |
| `scripts/plot.py` | The supplied matplotlib script that renders `chart.png`/`chart.pdf` (kept as-is). |
| `SUPPLIED_README.md` | Curator's full README — methodology, judgment calls, source URLs, commissioner timeline. |
| `METHODOLOGY.md` | This pipeline's contract: bucket definitions, fiscal-year semantics, what's not in here. |
| `PROVENANCE.md` | Source URLs, per-year provenance, sha256 of the supplied data files. |

## How to load

```python
import polars as pl

df = pl.read_parquet("md_mia/output/md_complaints_yearly.parquet")
df.sort("fy")

# Lifetime against-rate (the headline 5.68%):
total_bf = df["bad_faith"].sum()
total_om = df["on_merits"].sum()
print(f"{total_bf}/{total_om} = {total_bf/total_om*100:.2f}%")
```

## How to re-run

```
python3 md_mia/scripts/build.py        # < 1 s; writes the parquet from inline data
```

The data is hand-curated; there's no API or PDF parser to re-run. To audit a year's figures, open the corresponding `source_reports/FY{YYYY}.pdf` and compare against the row in [`data.csv`](data.csv).

## Headline caveats

1. **First-party bad-faith only.** §27-1001 covers first-party property/casualty bad-faith complaints. Other regulator-finding pipelines (TX TDI, CT CID, NY DFS) cover all consumer complaints and use different statutory frames; they're conceptually adjacent but not identical.
2. **`breach_pay_only` is the canonical "mixed" bucket.** When the insurer was found to have breached the duty to pay (insured prevailed on damages) but was *not* found to have acted in bad faith — so no §27-1001 fee-shifting applies. The MIA tables broke this out as a distinct row starting with the FY 2022 report. One row across the full 18 years (FY 2022).
3. **FY 2008 is partial.** The statute took effect Oct 1, 2007, so FY 2008 covers Oct 1, 2007 – Jun 30, 2008 (9 months). Annotated as `partial_year: 2008` in the viz manifest.
4. **FY 2011 was retrospectively revised.** The original FY 2011 report had Settled=8 / Violation=2 / NoViol=16. By the FY 2013 report it was re-tabulated to 7 / 1 / 18 after appeals/reclassifications closed out. The retrospective figures are used here.
5. **FY 2025 settled-bucket reconciliation.** The FY 2025 report's Table 1 has an internal arithmetic discrepancy (27 + 30 ≠ 52). The on-merits decomposition is internally consistent and preserved verbatim; the settled bucket is recorded as 22 to reconcile to the report's headline total. See [`SUPPLIED_README.md`](SUPPLIED_README.md) for full details.
6. **Maryland fiscal year ends June 30.** Year labels (e.g., "FY 2025") refer to the year the FY *ends*. The supplied chart uses calendar-year tick labels for that reason.
7. **No per-line / per-insurer breakdown at this aggregation.** §27-1001 is statutorily limited to property/casualty first-party claims, but the annual reports do not break out the four buckets by sub-line or by insurer.

## Headline numbers (sanity check)

From the 2026-05-04 build:

- 711 complaints filed across FY 2008 – FY 2025.
- 493 reviewed on the merits (`bad_faith + no_violation + breach_pay_only`).
- 28 bad-faith findings (`against_insurer`).
- 1 breach-to-pay-only finding (`mixed`, FY 2022 only).
- Lifetime aggregate **bad-faith / on-merits = 28 / 493 = 5.68%**.
- "Any finding for insured" rate (bad-faith + breach-pay-only) = 29 / 493 = 5.88%.
