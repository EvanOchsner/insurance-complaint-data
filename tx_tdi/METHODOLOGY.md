# Methodology

## What this dataset measures

> For each calendar year, how many consumer complaints did the Texas Department of Insurance close, and what fraction of those did TDI determine were `Confirmed` (the insurer violated a statute, rule, or policy provision)?

The temporal anchor is the **calendar year of `closed_date`**. This matches TDI's own reporting cadence — when TDI publishes complaint statistics, the unit is always "complaints closed in year Y." Receipts can lag closures by months to years, so anchoring on receipt would distort recent-year totals.

## Filter

A row from `data.texas.gov/resource/jjc8-mxkg.json` is included iff:

- `closed_date` is non-null and parseable.
- `finding_type` is non-null. (One row in 281k has a null finding; it's dropped.)
- `finding_type ∈ {"Confirmed", "Not Confirmed"}`. Any third value would be a hard failure — see below.

## What "Confirmed" means

TDI itself classifies every closed complaint as either `Confirmed` or `Not Confirmed`. Per TDI's published consumer guide ("Ways We Can Help"):

- **Confirmed** — TDI's complaint-handling staff determined the insurer (or other regulated entity) violated a statute, rule, or policy provision. The regulator's intervention typically resulted in a changed outcome (claim reopened, additional payment, refund, position overturned, coverage extended, etc.).
- **Not Confirmed** — TDI did not find a violation. This includes cases where the insurer's position was substantiated, the dispute was a pure question of fact, the policy contract clearly addressed the issue, or TDI lacked jurisdiction.

The original implementation plan assumed TDI would expose raw disposition codes that we'd have to map to a "Confirmed" boolean ourselves. In practice TDI does the classification themselves and exposes it in the `finding_type` field — no mapping CSV is needed. If TDI ever introduces a third `finding_type` value, `02_aggregate.py` hard-fails and the operator must review TDI's documentation before continuing.

## What "Confirmed" is NOT

- **Not a finding of bad faith.** "Bad faith" is a legal term of art typically determined by a court, not a regulator. A `Confirmed` complaint may represent any TDI-recognized violation — pricing, claims handling, marketing materials, policy form, agent licensing, etc.
- **Not a count of lawsuits.** TDI complaints are administrative; they do not necessarily proceed to litigation, and many bad-faith lawsuits never appear here.
- **Not exhaustive.** Disputes resolved by the parties themselves, by independent appraisal, or in court without a TDI complaint never enter this dataset.

## What's not in this dataset

| What | Why |
|---|---|
| Pre-2012 complaints | Dataset starts 2012-05-21. Earlier complaints are not on data.texas.gov. |
| Workers' comp indemnity disputes | Handled by TDI's Division of Workers' Compensation through a different complaint flow. About 1,800 WC-related rows do appear under `complaint_type = "Workers Compensation Network"` / `"Workers' Compensation"`, but full DWC complaint volume isn't here. |
| Per-respondent (multi-row-per-complaint) detail | That's the `ubdr-4uff` "All Data" dataset; out of scope for v1. |
| Per-company indexes (counts normalized by policies in force) | The "Complaint indexes and policy counts" dataset; out of scope. |
| Cross-walk to Maryland MIA's coverage taxonomy | Coverage labels stay TDI-native (`Accident and Health`, `Automobile`, `Homeowners`, etc.). MD ↔ TX cross-walks happen at the comparison/viz layer, not in this raw collection. |
| Reason-code analysis (claims handling vs underwriting vs marketing) | The `complaint_type` field holds this and is preserved in the complaint-level output, but no aggregations split on it. Trivial to add later. |

## Why the trailing year is "partial"

`closed_date` only includes complaints already finalized. The most recent year in the data extends only through the maximum `closed_date` observed at fetch time. Downstream visualizations should either drop the trailing year or render it visually distinct, just like the FJC pipeline does.

## Validation

- **Hard failure**: any new `finding_type` value beyond `{"Confirmed", "Not Confirmed"}` aborts the build.
- **Hard failure**: duplicate `complaint_number` in the supposedly-unique spine dataset.
- **Soft warnings printed to log**: rows dropped for null `closed_date`, rows dropped for null `finding_type`, max `closed_date` (used to identify the partial year).
- **Spot check**: the live API can be queried directly to confirm the per-year totals match what we wrote:
  ```
  curl 'https://data.texas.gov/resource/jjc8-mxkg.json?$select=date_extract_y(closed_date)+as+yr,finding_type,count(*)&$group=yr,finding_type&$order=yr,finding_type'
  ```
  Numbers in `output/tx_complaints_yearly.parquet` should equal these for every year.

## Cross-validation deferred

The TDI "Insurance complaint totals" Socrata dataset is a pre-aggregated view of the same source. Cross-checking our yearly totals against it would be a useful belt-and-suspenders step, but is not currently part of the pipeline. It can be added later if a discrepancy is ever suspected.
