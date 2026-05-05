# Oregon DFR — per-company complaint counts AND confirmed-complaint counts

Per-company complaint statistics from the Oregon Division of Financial Regulation (DFR), Department of Consumer and Business Services. **Six lines × seven years (2019–2025) = 42 reports**, with per-company columns for premium, **total complaints**, **confirmed complaints**, and complaint index.

This is the **first state in the per-company-index batch with published outcome data**. Oregon's "Confirmed Complaints" field is a regulator-issued merits-decision count — equivalent to TX's `Confirmed`, MD's "in favor of insured", and CT's "against insurer" series. That places OR alongside MD/TX/NY/CA/CT/VA in the small set of states publishing both volume AND outcome.

## What's in this folder

| Path | What it is |
|---|---|
| `output/or_complaints_company_yearly.parquet` (and `.csv`) | **Per-company per-line per-year**, ~9,428 rows. Columns: `state, year, line, company_name_raw, premium_written, total_complaints, confirmed_complaints, complaint_index, source_pdf`. |
| `output/or_complaints_yearly.parquet` (and `.csv`) | **Per-line per-year aggregates** (42 rows). Columns: `state, year, line, n_companies, total_complaints, total_confirmed, total_premium`. |
| `output/run_log.txt` | Appended each parse run. |
| `scripts/01_download.py` | Fetches all 42 PDFs from `dfr.oregon.gov/help/Documents/complaint-stats-{YEAR}/`. No Cloudflare; standard polite UA. |
| `scripts/02_parse.py` | Regex-based per-row parser handling both the "split-premium" PDF layout (most years) and the "clean-premium" layout (2024). |
| `interim/files/` | Raw PDFs. Gitignored. |
| `interim/manifest.json` | Discovery + fetch metadata (sha256 per file, source URL). |
| `METHODOLOGY.md` | DFR's complaint index, "Confirmed" definition, comparison with peer states. |
| `PROVENANCE.md` | Source URLs and PDF parsing notes. |
| `PLAN.md` | Open follow-ups. |

## How to load

```python
import polars as pl

# Worst confirmed-complaint rates for auto in 2025 (filter to companies with material premium):
c = pl.read_parquet("or_dfr/output/or_complaints_company_yearly.parquet")
(c
  .filter((pl.col("year") == 2025)
        & (pl.col("line") == "auto")
        & (pl.col("premium_written") > 1_000_000))
  .with_columns(confirmed_rate=pl.col("confirmed_complaints") / pl.col("total_complaints"))
  .sort("complaint_index", descending=True)
  .head(10)
)
```

## How to re-run

```sh
python3 or_dfr/scripts/01_download.py    # ~45s (42 PDFs, 1s sleep)
python3 or_dfr/scripts/02_parse.py        # < 10s
```

## Caveats — read before plotting

1. **"Confirmed Complaints" is OR's outcome metric.** DFR confirms a complaint when their investigation finds the insurer violated insurance code, contract terms, or industry standards. This is approximately equivalent to the canonical `regulator_finding_against_insurer` bucket. Confirmation rates typically run 10-20% of total complaints, varying by line.
2. **Complaint index is computed by DFR using NAIC-tradition methodology** — share-of-confirmed-complaints divided by share-of-premium. NOT the same as MO/IN/KS where the index uses share-of-*total*-complaints. OR's index thus weights the outcome dimension; a company with many filed but no confirmed complaints can have index = 0.
3. **6 lines, all personal lines:** Auto, Annuities, Health, Homeowners, Life, Long Term Care. No commercial lines, no workers' comp.
4. **7 years (2019-2025).** Pre-2019 reports may be archived elsewhere; not yet pursued.
5. **PDF layout varies year to year.** Most years render the premium with a split-digit artifact (`9 ,177,175` instead of `9,177,175`); 2024 renders cleanly. The parser handles both. If layouts change again, the regex may need updating.
6. **No NAIC code published.** Companies listed by name only; cross-state rollup requires fuzzy matching.
7. **No reason / nature-of-complaint breakdown** in the public PDFs. DFR has a "Complaint compare search tool" that may expose more dimensions per company; out of scope for v1.
