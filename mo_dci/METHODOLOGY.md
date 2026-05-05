# Methodology — MO DCI Complaint Index

## DCI's complaint index, defined

The Missouri Department of Commerce & Insurance (DCI) computes a **per-company, per-line complaint index** that compares a company's share of complaints against its share of premium, expressed as a percentage:

```
                     (Company complaints)        (Industry-wide complaints)
Complaint Index = ─────────────────────────  ÷  ──────────────────────────────  × 100
                     (Company premium)           (Industry-wide premium)
```

- **100** = the company's complaint rate equals the industry average for that line.
- **< 100** = lower than industry average (good).
- **> 100** = higher than industry average (bad).
- **Cap of 9,999** is applied — capped rows usually indicate companies with very low premium volume and any non-zero complaint count.

This is the same NAIC-tradition methodology used by IN, KS, ID, and IL.

## Three-year rolling window

DCI pools three years of complaints and three years of premium for each report ("to ensure that data are statistically credible"). Each published report covers a different window:

| Report | Pooled window | First year IDRR aggregate ≈ data here |
|---|---|---|
| 2021 *Missouri Complaint Report* (Apr 2022) | 2018–2020 | 2018 |
| 2022 *Missouri Complaints Report* (Jul 2023) | 2020–2022 | 2020 |
| 2023 *Missouri Complaint Index* (Nov 2024) | 2021–2023 | 2021 |

Adjacent reports overlap on 2 years, so the per-company complaint counts cannot be analytically deconvolved into single-year figures (3 reports × 3-year windows × 7 lines × hundreds of companies → underdetermined).

## What's NOT pooled

Section 4 of each report ("Total Complaints by Line, Prior Five Years" and "Complaint Resolution by Line") is **per-year**, not 3-year-pooled — it shows the prior five years individually. So while per-company indices are pooled, per-line aggregates are clean per-year. The three reports together give:

| Year | In 2021 report | In 2022 report | In 2023 report |
|---|---|---|---|
| 2017 | ✓ | | |
| 2018 | ✓ | ✓ | |
| 2019 | ✓ | ✓ | ✓ |
| 2020 | ✓ | ✓ | ✓ |
| 2021 | ✓ | ✓ | ✓ |
| 2022 | | ✓ | ✓ |
| 2023 | | | ✓ |

For overlapping years, values typically agree exactly across reports; small (1–3 complaint) revisions occasionally appear and are preserved in the parquet for auditability.

## Lines of business

Seven lines, consistent across all three reports:

1. **Private Passenger Automobile** (`private_passenger_auto`)
2. **Homeowners** (`homeowners_farm_mh_fire`) — including farm, mobile home, and personal fire & allied lines
3. **Accident and Health** (excluding HMOs) (`accident_health`)
4. **Long Term Care** (`long_term_care`)
5. **Medicare Supplement** (`medicare_supplement`)
6. **Life Insurance and Annuities** (`life_annuities`)
7. **Health Maintenance Organizations** (`hmo`)

Section 4's per-year per-line aggregate table also has 4 derived/summary rows: `total_pc`, `total_ah`, `other_pc`, `all_other_ah`, `total`. These are kept in the parquet so totals can be cross-validated against the per-line breakdown.

## "% of Complaints Resolved with Consumer Relief"

Section 4's second table reports, per-line per-year, the percentage of complaints that closed with some form of relief to the consumer. This **approximates** the canonical `regulator_finding_against_insurer` outcome bucket in the cross-state taxonomy, but with caveats:

- "Consumer relief" includes both true regulator findings against the insurer AND voluntary remedies the insurer agreed to (similar to CA's "positive outcome" subset).
- It's a rate, not a count — the underlying counts can be reconstructed by multiplying by the per-line `complaints_total`.
- The HMO line in some years has too few complaints to compute a meaningful rate ("-" in source).

For canonical-taxonomy mapping: prefer the `pct_resolved_consumer_relief` rate as a soft analog of `regulator_finding_against_insurer / total`, with a methodology footnote.

## Comparison with peer states

| State | Index methodology | Per-year? | Outcome breakdown? |
|---|---|---|---|
| MO (this) | NAIC tradition (share-of-share × 100) | 3-yr pooled per-company; per-year for line aggregates | Yes (rate, "consumer relief") |
| IN | NAIC tradition | Per-year | No |
| KS | NAIC tradition | Per-year | No |
| ID | NAIC tradition | Per-year | No |
| IL | NAIC tradition (2018) → per-$1M-EP / per-10k-policies (2019+) | Per-year | No |

MO's pooled-per-company structure makes direct apples-to-apples comparison with IN/KS/ID/IL difficult. The per-year aggregate series in Section 4 is comparable to IDRR but adds line and outcome dimensions.

## Comparison with NAIC IDRR

IDRR (in `naic_idrr/`) reports an annual *complaints received* count per state, no line, no outcome. MO DCI's per-year aggregate is published per-line and includes the resolved-with-consumer-relief rate. Numbers are **not directly comparable**:

- IDRR for MO 2021: ~3,000 complaints received (rough, varies by year).
- MO DCI Section 4 total for 2021: 1,906 complaints (plus or minus a few across reports).

The discrepancy is because IDRR includes informal contacts and inquiries that DCI's published reports exclude. Treat MO DCI as the *authoritative per-line breakdown* and IDRR as the *broader workload count*.
