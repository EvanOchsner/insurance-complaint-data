# Methodology

## Two streams, two metric definitions

NY DFS publishes two separate per-company complaint datasets that we capture here:

### Stream 1 — Auto (Open Data NY, 2009-2024)

**The metric is a 2-year rolling complaint ratio** (DFS calls this the "Automobile Insurance Company Complaint Ranking"). For each `filing_year Y`, the row's underlying counts cover complaints closed in `Y-1` and `Y`, and premiums written in `Y-1` and `Y`. The ratio is `upheld_complaints / avg_annual_premiums_millions × ...`. This is per the rules originally codified in NY Insurance Law § 337 (now repealed but still followed by DFS as a courtesy publication).

Per the [DFS landing page](https://www.dfs.ny.gov/consumers/auto_insurance/auto_insurance_complaint_ranking):

> "Upheld" complaints occur when DFS agrees with a consumer that an auto insurer made an inappropriate decision; complaints not upheld by DFS or withdrawn by the consumer are not included in the final calculation.

`upheld_complaints` is therefore the **regulator's affirmative finding against the insurer** — the closest NY analogue to TX's `Confirmed`, CA's `Justified`, and MD's "in favor of insured."

**Important:** because the metric is 2-year rolling, summing per-year rows across years would double-count. For a comparable single-year metric, you'd need to difference adjacent years' counts. We don't do this in v1 because the published data has artifacts that prevent clean differencing (e.g., 2015 and 2016 rows are identical in the live API, suggesting a year was not separately published). The yearly aggregate file `ny_auto_complaints_yearly.parquet` therefore carries the rolling sum verbatim, with a column suffix `_2yr` to make the windowing explicit.

### Stream 2 — Health (Consumer Guide PDFs, data years 2015-2024)

**The metric is annual** — each year's Consumer Guide reports on the prior calendar year's complaints (e.g., the 2024 guide reports on 2023 data). Each plan-type table (HMO, EPO/PPO, Commercial) lists the top N plans by complaint ratio, with:

- `total_complaints_dfs` — total complaints received by DFS that year about this plan
- `upheld_complaints_dfs` — DFS upheld findings against this plan that year
- `premiums_millions` — total premium written that year
- `complaint_ratio_dfs` — `upheld_dfs / premiums_millions`
- For HMOs only: parallel `total_complaints_doh` / `upheld_complaints_doh` (NY Department of Health handles HMO quality-of-care complaints separately)

Per the [DFS landing page](https://www.dfs.ny.gov/consumers/health_insurance/health_insurance_complaint_rankings):

> "Each year, New York State (via the DFS and Department of Health) receives complaints about health insurance companies from consumers and health care providers... DFS determines if the health insurance company acted appropriately. If DFS determines that the health insurance company did not act in accordance with its statutory and contractual obligations, the health insurance company must resolve the issue."

`upheld_complaints_dfs` is the same regulator-finding-against-insurer concept as the auto metric.

## Why an "auto + health" v1 is enough

Together these cover the two largest consumer-facing lines in NY by both premium and complaint volume. P&C-non-auto, life, and surplus lines appear only in the unstructured DFS Annual Report PDFs (CPFED reports), which require year-by-year layout dispatch and are deferred to a v2.

## What's not in this dataset

| What | Why |
|---|---|
| Pre-2009 auto data | Earliest year on Open Data NY is 2009. |
| Pre-2015 health data | The earliest Consumer Guide currently online is the 2016 guide (reports 2015 data). |
| Single-year auto counts (vs 2-year rolling) | Data structure prevents clean differencing. |
| P&C-non-auto, life, surplus lines | Not in either source we use. CPFED Annual Report parses are deferred. |
| Workers' comp | Separate regulator (Workers' Comp Board). |
| Per-plan NAIC group rollup | Each subsidiary appears as its own row. Rollups happen at the comparison layer. |
| Prompt Pay complaint tables | Different metric (claim-payment timing). The Consumer Guide includes them but v1 captures only the main complaint tables. |
| External Appeals dataset | Separate Open Data NY resource; out of scope. |
| DFS Annual Report (CPFED) all-line totals | PDF prose; not structured for tabular extraction. |

## Year-mapping detail

- **Auto**: the `filing_year` column is preserved verbatim from Socrata. It represents the "as-of" year of a 2-year rolling window. We rename it to `year` only in the yearly rollup output.
- **Health**: the data year is extracted from each table's title text ("Complaints—HMOs 2023" → `data_year = 2023`), not inferred from the guide year. This is robust to any year-numbering inconsistencies in the guide URLs.

## Validation

- **Auto**: per-row sanity that `total_complaints ≈ upheld + question_of_fact + not_upheld` (within ±1). Soft-warned in the run log; not a hard fail because DFS occasionally has small reconciliation differences.
- **Auto**: every `filing_year` from 2009 to the max appears.
- **Health**: every guide-year PDF must produce ≥ 1 parsed data row; hard-fail otherwise.
- **Health**: each `(data_year, plan_type)` combination should have ≥ 5 plans (sanity check via the `n_plans` column in the yearly rollup).
- **Cross-check**: the per-table "Total" line printed in each PDF can be compared against the sum we compute. We do not enforce this as a hard check (it's logged for review).

## A note on the 2015/2016 auto anomaly

When pulled live, the Open Data NY auto dataset shows identical totals for `filing_year = 2015` and `filing_year = 2016` (`sum(upheld_complaints) = 281`, `sum(total_complaints) = 3,043` for both). This appears to be either a data-entry artifact or a year that wasn't separately published. The pipeline preserves both rows verbatim; downstream visualizations may want to treat one or both as a duplicate. Documented here so it's not mistaken for a pipeline bug.
