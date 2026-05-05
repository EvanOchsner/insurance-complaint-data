# Virginia SCC Bureau of Insurance — workload + health external review

Two streams from VA's State Corporation Commission, Bureau of Insurance (BOI) annual reports for FY 2022–FY 2025:

1. **Per-line workload** — annual count of consumer complaints received, broken into Property & Casualty vs Life & Health. This is "what walked through the door," not "what the regulator decided." Same metric class as NAIC IDRR's per-state totals, but with a 2-line breakout IDRR doesn't have.
2. **Health External Review (ER) dispositions** — for managed-care health-coverage appeals only, the regulator's reviewer adjudicates each case as Upheld / Overturned / Modified / Reversed-by-carrier / Terminated. This is the only VA-published breakdown by regulator finding, and it covers a narrow but meaningful slice of complaints. Mapped to the project's canonical 4-bucket outcome taxonomy.

Virginia was the only Phase 3 candidate that passed the recon test — see [`../multi_state_acquisition_plan.md`](../multi_state_acquisition_plan.md) §7.4. PA / NJ / NC dropped (no value over IDRR or no public reports); MA deferred (mass.gov hard-blocks fetches).

## What's in this folder

| Path | What it is |
|---|---|
| `output/va_complaints_yearly.parquet` (and `.csv`) | Per `(fiscal_year, line)` workload count. 8 rows (4 FYs × 2 lines). Columns: `fiscal_year, line, complaints_received, source_file`. |
| `output/va_external_review_yearly.parquet` (and `.csv`) | Per `fiscal_year` health-appeal disposition table. 4 rows. Columns: native `total_reviewed / eligible / ineligible / upheld / overturned / modified / reversed_self / terminated` plus canonical `against_insurer / for_insurer / mixed / no_decision / on_merits / against_rate_of_decided`. |
| `output/run_log.txt` | Per-FY parsed values + sanity warnings. |
| `scripts/01_download.py` | Fetch each `{YYYY}BOI.pdf` from the predictable URL template. |
| `scripts/02_parse.py` | Regex-extract fixed-label rows; project ER dispositions onto canonical buckets. |
| `interim/files/` | Raw PDFs. **Gitignored.** |
| `interim/manifest.json` | Per-file SHA256 + Last-Modified + fetched-at. |
| `METHODOLOGY.md` | Bucket-mapping contract; FY semantics; ER scope caveat. |
| `PROVENANCE.md` | Source URLs, per-file hashes, run log. |

## How to load

```python
import polars as pl

# Workload by line:
wk = pl.read_parquet("va_scc/output/va_complaints_yearly.parquet")
wk.sort(["fiscal_year", "line"])

# Health ER dispositions (canonical 4-bucket form):
er = pl.read_parquet("va_scc/output/va_external_review_yearly.parquet")
er.select(["fiscal_year", "against_insurer", "for_insurer", "mixed", "no_decision", "against_rate_of_decided"])
```

## How to re-run

```
python3 va_scc/scripts/01_download.py        # ~6 s (4 PDFs at 1 req/s)
python3 va_scc/scripts/02_parse.py           # < 5 s
```

## Headline caveats

1. **Workload ≠ regulator finding.** The P&C / L&H "complaints received" counts are workload signals, like IDRR. They tell you complaint volume, not how the regulator resolved them. The viewer presents these in line-only mode (no outcome buckets), with a caveat banner.
2. **External Review covers health appeals only.** The disposition table is for managed-care health-coverage appeals — a narrow sub-population of all complaints. The denominator is small (a few hundred per year), and the against-rate (~54% lifetime) is much higher than any state's overall regulator-finding-against-insurer rate would be, because eligibility filters out cases that don't have an adjudicable medical-necessity question. Don't compare ER's 54% against, e.g., MD MIA's 5.68% — different denominators, different scopes.
3. **Reversed-Itself counts as `against_insurer`.** When the carrier reverses its denial mid-review, the consumer prevails. Mapped to `against_insurer` per [METHODOLOGY](METHODOLOGY.md).
4. **VA fiscal year ends June 30.** "FY 2025" = July 1, 2024 – June 30, 2025. Year labels refer to FY-end.
5. **Workload totals roughly track IDRR.** VA's IDRR-reported 2022 calendar-year total (3,795) is close to but not equal to the FY 2022 BOI total (P&C 2,322 + L&H 1,347 = 3,669). The 3% gap is likely calendar-vs-fiscal-year accounting; both sources are real and consistent within their own conventions.
6. **FY 2024 minor arithmetic discrepancy.** Sum of dispositions (228) is 10 more than Eligible ER Requests (218) in the published table. We preserve the published numbers; soft-warn in the run log.

## Headline numbers (sanity check)

From the 2026-05-04 build:

| FY | P&C received | L&H received | ER reviewed | ER against | ER for | ER mixed | Against rate (of decided) |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 2022 | 2,322 | 1,347 | 524 | 83 | 75 | 0 | 52.5% |
| 2023 | 2,779 | 1,347 | 585 | 106 | 84 | 1 | 55.5% |
| 2024 | 3,230 | 1,809 | 543 | 114 | 110 | 3 | 50.2% |
| 2025 | 3,342 | 1,898 | 459 | 114 | 80 | 2 | 58.2% |

Lifetime ER aggregate: 417 / 772 = **54.02% against-insurer (of decided)**.
