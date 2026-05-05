# Methodology — Connecticut CID consumer complaints

## What CID publishes

CID's open-data dataset `t64r-mt64` ("Insurance Company Complaints, Resolutions, Status, and Recoveries") is a complaint-level feed: one row per consumer complaint, with fields for company, line of business, nature of complaint, regulator's `disposition`, customer-side `conclusion`, recovery dollars, and complaint status.

## What "Confirmed" means in CT (and how we map it)

CT does not publish a clean Confirmed/Not-Confirmed binary like Texas TDI. The closest analog is the `disposition` column, which has ~14 distinct values describing the regulator's resolution of the complaint. We group these into three buckets, plus a fourth "no disposition" bucket for rows where the field is null.

### Bucket mapping (methodology contract)

| Canonical bucket | CID `disposition` values |
|---|---|
| **`against_insurer`** (regulator-side action favored consumer) | `Company Position Overturned`, `Claim Settled`, `Compromised Settlement/Resolution`, `Claim Reopened`, `Fine Assessed`, `Referred to Other Division for Possible Disciplinary Action` |
| **`for_insurer`** (regulator confirmed insurer position) | `Company Position Substantiated` |
| **`ambiguous`** (no clear regulator finding either way) | `Question of Fact/Contract/Provision/Legal Issue`, `No Jurisdiction`, `No Action Requested/Required`, `Insufficient Information`, `Complaint Withdrawn`, `Referred to Outside Agency/Dept`, `Referred to Another State's Dept of Insurance` |
| **null `disposition`** | tracked separately as `no_disposition`; excluded from `against_rate_of_decided` numerator and denominator |

The build hard-fails if `02_aggregate.py` encounters a previously-unseen `disposition` value. This forces every new label to be explicitly categorized rather than silently bucketed (which would systematically bias the headline rate).

### Why three buckets, not a binary

`Company Position Substantiated` (the FOR bucket) is unambiguously "regulator agrees with insurer" — analogous to TX TDI's `Not Confirmed`.

`Company Position Overturned` is the unambiguous mirror — regulator disagreed with insurer's handling. But CID also routinely codes outcomes as `Claim Settled` or `Compromised Settlement/Resolution` when the regulator's intervention triggered the company to settle or partially settle. Excluding those would massively understate the regulator-action-against-insurer signal in CT.

The remaining outcomes (`Question of Fact…`, `No Jurisdiction`, `Insufficient Information`, withdrawals, referrals) genuinely lack a regulator finding — neither for nor against. Lumping them with `for_insurer` would inflate the FOR side; lumping them with `against_insurer` would inflate the AGAINST side. They get their own bucket.

### Two rate metrics

Two derived rates are emitted:

- **`against_rate_of_decided`** = `against_insurer / (against_insurer + for_insurer)`. Cleanest for cross-state comparison: among complaints with a clear regulator finding, what share went against the insurer? This excludes ambiguous and no-disposition rows from both numerator and denominator.
- **`against_rate_of_total`** = `against_insurer / total_closed`. The headline rate including the dilution from ambiguous and no-disposition rows. Useful for trending volume-weighted regulator action over time.

## Temporal anchor

We use `closed` (calendar year of close) as the temporal anchor, matching how state regulators typically report. The `opened` date is preserved at the complaint-level grain for ad-hoc analysis (e.g., processing-time studies).

The most recent calendar year in the data is partial — typically through the date of the most recent build (here, 2026-05-01). Downstream consumers should drop the trailing year when computing year-over-year trends, or mark it visually.

## Data filtering

The headline outputs restrict to `status = 'Closed'`. CID's `status` enum has 20+ in-progress states (`Awaiting Decision`, `Sent to Company`, `Reopened`, etc.); only `Closed` represents a fully processed complaint with a final regulator disposition. ~75k of 77k rows are `Closed`.

## What's not in here

- **Per-company aggregations.** The complaint-level file has `company` and (where present) `naic_code`; aggregating to a per-company yearly is straightforward but deferred to v2.
- **Cross-state taxonomy normalization.** CT keeps its native `coverage` enum (`A & H`, `Group`, `Individual Private Passenger`, `Homeowners`, etc.). Cross-walking to a unified line-of-business taxonomy happens at the viz/comparison layer when more states warrant it.
- **NAIC group rollups.** Same — deferred until cross-state per-company analysis is attempted.
- **The `conclusion` column.** Preserved at the complaint-level grain but not used to derive headline buckets. CID's `conclusion` is the customer-side outcome (e.g., `Claim Paid`, `Furnished Information`, `Justified`); it's more sparsely populated than `disposition` and harder to fold into a clean against/for binary.
