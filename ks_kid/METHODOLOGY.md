# Methodology — Kansas KID Complaint Index Report

## What KID publishes

For each of five most-recent years (2020–2024 currently online), KID publishes an annual *Complaint Index Report* PDF covering ~6 lines: Automobile, Health (called "Accident & Health" pre-2023), Homeowners & Renters, Individual Annuity, Individual Life, Long-Term Care. Each per-line table reports for the top-20 premium-writing companies in the line (plus any with 10+ complaints):

- NAIC company code
- Company name
- Market share (%)
- Complaint count for the data year
- Complaint index for the data year
- 1–2 prior years' complaint indexes for trend context

## What the complaint index means

KID's complaint index follows the standard NAIC convention:

```
complaint_index = (company's share of all complaints in this line)
                / (company's share of all written premium in this line)
```

Normalized so 1.0 = parity (complaints proportional to market share); above 1.0 = more complaints than market share predicts; below 1.0 = fewer.

The ratio cannot be reconstructed from this dataset's published numbers alone (the denominator requires jurisdiction-wide totals across all premium-writing companies). We preserve KID's published index as-is.

## How KID's inclusion differs from IN's

KID and IN both publish "complaint index" data, but their inclusion rules differ in a way that affects per-company medians:

| | KS (KID) | IN (IDOI) |
|---|---|---|
| Inclusion rule | Top-20 premium writers in the line + any company with 10+ complaints | Only companies with **at least one complaint** |
| Zero-complaint companies in the report? | Yes (when in top-20 by premium) — `complaint_index = 0.00` | No (excluded entirely) |
| Effect on per-company median | Median is closer to the population median (~1.0) because zero-complaint top-20 writers pull it down | Median is biased above 1.0 because zero-complaint companies are excluded |

The two states' per-company files therefore are **not apples-to-apples** at the median or distribution level. The complaint-index *value for a given company* is comparable (both states use the same NAIC normalization), but you cannot directly compare e.g. "median KS auto complaint index = 0.70" to "median IN auto complaint index = 2.07" and conclude KS auto markets are healthier — the populations sampled are different.

## Why this is a different metric class than TX/CA/NY/CT

Same reasoning as IN IDOI ([`in_idoi/METHODOLOGY.md`](../in_idoi/METHODOLOGY.md)): a NAIC complaint index is a **ratio** normalized to market share, not an **absolute count of regulator findings**. The viz puts this dataset in a separate "Regulator complaint indexes" category to make the distinction visible.

## Temporal anchor

The temporal anchor is the **data year** (the year in the report's title, which is the calendar year the complaints were received). KID publishes year-N reports in year N+1.

## Data filtering

The parser hard-fails if a previously-unseen "Indexes by line: X" header appears in any PDF (forces explicit categorization rather than silent bucket-or-skip).

## What's not in here

- **Pre-2020 data.** KID does not appear to publish older years online (the publications page lists only 2020–2024 at first build).
- **Recovery dollars / outcome dispositions.** KID's report covers complaint counts and indexes, not the regulator's finding (insurer-improperly-handled vs not). KS does not publish a parallel "confirmed" dataset that would be comparable to TX or CT.
- **Subsidiary roll-up to NAIC group.** Companies are listed individually; group-level rollups are deferred to the comparison/viz layer.
- **The "% of total market share represented in this report" footer.** Captured in the per-(year × line) aggregate as `market_share_covered`.
