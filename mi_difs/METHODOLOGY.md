# Methodology — MI DIFS Complaint Ratios

## DIFS's complaint ratio, defined

The Michigan Department of Insurance and Financial Services (DIFS) computes a per-company, per-line **complaint ratio** as:

```
Complaint Ratio = (Number of complaints filed) / (Direct premiums written, in $millions)
```

So a ratio of 0.19 means 0.19 complaints per $1M of premium written. A ratio of 1.99 means about 2 complaints per $1M.

DIFS's own description: "Complaint ratios are created by dividing the dollar amount (in millions) of written premium into the number of filed complaints. The resulting ratios provide complaint information that can be meaningfully compared across insurance companies, regardless of size."

This is **not** the NAIC-tradition share-of-share index used by MO, IN, KS, ID, IL. There's no normalization to an industry average; the ratio is a raw rate.

## Cross-state reconciliation

To compare MI ratios with MO/IN-style indices, you can compute the MI industry-average ratio for a line in a year, then express each company's ratio as a percentage of that average:

```
mi_industry_avg_ratio[line, year] = total_complaints / total_premium_millions
mi_company_index[line, year, company] = (mi_company_ratio / mi_industry_avg_ratio) * 100
```

The result is comparable to MO/IN's complaint index (100 = industry average for the line). Note that DIFS publishes raw ratios, not the index, so we compute the index downstream rather than store both forms in the parquet.

## Inclusion floor: $1M premium

DIFS excludes companies that wrote less than $1M in premium for the line in the report year, because "Complaint ratios which are based on less than $1,000,000 in premium are highly variable and may not be adequate measures of a company's performance." Per-company tables therefore undercount the per-line aggregate by the volume of complaints filed against sub-$1M companies.

The undercount diff per (year, line) is logged in `output/run_log.txt`. Typical magnitudes:

| Year | Line | Sum of company complaints | Line-of-Coverage total | Diff (excluded ≤$1M) |
|---|---|---:|---:|---:|
| 2024 | automobile | 1,775 | 1,864 | 89 |
| 2024 | accident_health | 1,933 | 1,991 | 58 |
| 2024 | homeowners | 906 | 925 | 19 |

## Lines of business

Five lines have per-company tables:

1. **Automobile** (`automobile`)
2. **Homeowners** (`homeowners`)
3. **Life** (`life`)
4. **Accident & Health** (`accident_health`) — excluding HMOs
5. **Annuity** (`annuity`)

Two additional lines appear in the Line-of-Coverage aggregate but **not** per-company:

6. **Fire, Allied Lines & CMP** (`fire_allied_cmp`)
7. **Liability** (`liability`)

DIFS doesn't publish per-company ratios for these two; only state-wide totals.

## HMOs are separate

The total complaint volume is split into three entity types:

- **Insurance Company** (the per-line tables cover this)
- **HMO** (no per-company breakdown published)
- **Other** (small bucket, mostly miscellaneous regulated entities)

Sum across all three to get the true total. The `mi_complaints_total_yearly` parquet exposes all three plus the `total` row that DIFS publishes.

## Reason categories

Four high-level reason buckets (each with sub-reasons that DIFS doesn't publish at the bucket-aggregate level):

1. **Claim Handling**
2. **Marketing & Sales**
3. **Customer Service**
4. **Underwriting**

Reasons are reported per-entity-type per-year (4 reasons × 3 entity types = 12 cells per year). Within each entity type, the percentages sum to ~100%; across entity types they don't (since each entity type's denominator differs).

DIFS notes that "a complaint may have more than one reason. Therefore the total number of complaint reasons may not match the total number of complaints." This is reflected in the data: the sum of reason counts across categories slightly exceeds the entity's complaint total. Treat reason counts as ordinal, not strictly additive.

## Comparison with peer states

| State | Metric | Per-year? | NAIC code? | Outcome breakdown? |
|---|---|---|---|---|
| MI (this) | Ratio per $1M premium | Yes (2022-2024) | No (DIFS internal company_id) | No |
| MO | NAIC share-of-share index (3-yr pooled) | Yes for line aggregates; pooled for per-company | Yes | Yes (`pct_resolved_consumer_relief`) |
| IN | NAIC share-of-share index | Per-year | Yes | No |
| KS | NAIC share-of-share index | Per-year | Yes | No |

MI's per-year coverage is shorter (3 years) but it's the only state in this batch with **publicly published per-reason breakouts**. MO has per-reason data inside its PDFs (Section 5) but those are not yet extracted (see `mo_dci/PLAN.md`).

## Comparison with NAIC IDRR

IDRR (in `naic_idrr/`) reports MI's annual *complaints received* count (no line, no entity, no outcome). For 2022, IDRR shows MI = ~7,440. DIFS's `mi_complaints_total_yearly` for 2022 = 5,992. The discrepancy is because IDRR includes informal contacts and inquiries that don't make it onto DIFS's published complaint pages.
