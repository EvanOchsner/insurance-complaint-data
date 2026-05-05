# Methodology — Indiana IDOI Company Complaint Index

## What IDOI publishes

For each calendar year and each of five lines (Annuity, Auto, Health, Homeowners, Life), IDOI publishes a one-PDF (or, in 2014, one-XLSX) report listing every insurer in Indiana **that received at least one complaint** in that line that year. For each such insurer, the report records:

- NAIC company code
- Company name
- Indiana written premium for that line that year
- Number of complaints filed against the company in Indiana
- A "complaint index" value (or `DNC` if premium is too small)

## What the complaint index means

IDOI's complaint index is a NAIC-tradition normalized ratio:

```
complaint_index = (company's share of all complaints in this line)
                / (company's share of all written premium in this line)
```

So a value of `1.0` means the company received complaints in exact proportion to its share of the Indiana market for that line. Above 1.0 = more complaints than market presence predicts; below 1.0 = fewer.

The ratio cannot be reconstructed from this dataset alone, because the numerator (jurisdiction-wide complaint count) and the denominator (jurisdiction-wide written premium) require all companies' contributions, not just complaint-having companies. We preserve IDOI's published index value as-is.

## Why this is a different metric class than TX/CA/NY/CT

The TX TDI, CA CDI, NY DFS, and CT CID datasets carry **counts of complaints with a regulator finding** — `Confirmed`, `Justified`, `upheld`, or `Company Position Overturned`. These are absolute counts of insurer-improperly-handled determinations.

IDOI's complaint index is **a relative ratio**. It does not include a regulator finding at all — every complaint counts, regardless of how the regulator ultimately resolved it. The denominator (premium) and the normalization to 1.0 mean a value of `1.50` is **not 1.5× as bad as the average insurer in absolute terms** — it's 1.5× the parity benchmark in market-share-relative terms.

In the unified viewer the IDOI dataset sits under a separate "Regulator complaint indexes" category to make this distinction visible.

## Coverage exclusion (the most important caveat)

Each IDOI per-(year × line) table includes only companies with at least one complaint. The bottom of each PDF prints:

> Subtotal Premium and Complaints: $X,XXX,XXX,XXX  N
> 405 Companies with Zero Complaints: $X,XXX,XXX,XXX
> Total Premium and Complaints: $X,XXX,XXX,XXX  N

So the per-company file in this repo represents the **complaint-having subset**, not the full premium-writing population. Two consequences:

1. **The median index in our file is biased upward.** A population median across all premium-writing companies — including zero-complaint companies — would be near the premium-weighted average (~1.0). Our per-line medians sit at 2–6 because the zero-complaint companies are excluded.
2. **The total complaint count in `in_complaints_yearly.parquet`** sums over only complaint-having companies. By IDOI's definition this equals the line-and-year total complaint count (zero-complaint companies contribute zero, by definition), so this aggregate is correct as a complaint-volume series.

## Temporal anchor

The temporal anchor is the **data year**, not the publication year. IDOI publishes year-N reports in year N+1 (occasionally N+2). The reports use the data year in the title, so `2024-Auto-Index.pdf` is for calendar-year 2024 complaints.

## Data filtering

The parser hard-fails if a previously-unseen line label appears on the IDOI landing page (forces explicit categorization). The five known lines map to canonical slugs `annuity`, `auto`, `health`, `homeowners`, `life`.

## What's not in here

- **Per-company per-year *across all lines*.** A given company appears in multiple (year × line) rows; we don't roll those up. The per-company-year-across-lines aggregation is straightforward but deferred.
- **NAIC group rollups.** IDOI lists individual subsidiaries (e.g. `Allstate Ind Co`, `Allstate Ins Co`, `Allstate Prop & Cas Ins Co`, `Allstate N Amer Ins Co`); the parquet preserves them. Rollups happen at the comparison/viz layer when warranted.
- **Cross-line totals or premium-weighted indexes.** Not derivable from IDOI's per-line tables alone (they exclude zero-complaint companies, so you can't reconstruct the population-wide weighted average).
- **The 2014 row-number column.** XLSX format; the parser ignores any leading row-number column.
