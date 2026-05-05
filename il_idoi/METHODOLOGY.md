# Methodology — Illinois IDOI Consumer Complaint Ratio Reports

## What IL IDOI publishes

A single consolidated Consumer Complaint Ratio PDF per year, listing per-company complaint counts, a denominator (premium / policies / members depending on line), and a complaint ratio.

## Two ratio definitions (`ratio_type` column)

### 2018: `share_of_share` (NAIC standard)

```
ratio = (company's share of total complaints in line) / (company's share of total premium in line)
```

Normalized so 1.0 = parity. Above 1.0 = more complaints than market share predicts. This is the NAIC-tradition complaint index used by IN, KS, ID.

### 2019+: `per_million_ep` (per-million-earned-premium for P&C; per-10k for Life/HMO)

P&C lines (auto, homeowners):
```
ratio = (number of complaints) / (earned premium in $1,000,000)
```

So a value of 0.40 means "0.4 complaints per $1M earned premium." NOT comparable to the 2018 share-of-share ratio without recalculation.

Life lines:
```
ratio = (number of complaints) / (policies in force / 10,000)
```

HMO / Group Health lines:
```
ratio = (number of complaints) / (members / 10,000)
```

Each line's ratio is on its own scale. **Cross-line ratio comparisons within IL are not meaningful**; cross-year comparisons are valid only within a single line and within a single ratio_type.

## Line slugs

| IL label | Canonical slug |
|---|---|
| Private Passenger Automobile / Auto / Private Passenger Auto | `auto` |
| Homeowner's / Homeowners | `homeowners` |
| Individual Life / Life | `life` |
| Individual Annuity / Annuity | `annuity` |
| Individual Accident & Health | `individual_health` |
| Group Accident & Health | `group_health` |
| Health Maintenance Organizations / HMO | `hmo` |
| Health (2023+) | `health` |

Note: 2018–2020 published Individual A&H and Group A&H separately; 2023–2024 collapse them into a single "Health" category. Cross-year health rollups should account for this.

## Reason codes (not extracted in v1)

The 2019+ reports include 4–6 columns breaking down complaints by reason: Underwriting, Marketing/Sales, Claims Handling, Policyholder Service (and in 2019–2020, "Reason Other" and "Reason Not Indicated"). The column count is inconsistent across years and the parsing complexity isn't worth the value for v1. If needed later, the source PDFs are preserved in `interim/files/`.

## Coverage gaps

- **2021, 2022:** No consolidated ratio report posted. IL appears to have only published "summary" PDFs (state-level counts, no per-company) for these years. The ratio series jumps from 2020 → 2023.
- **Pre-2018:** Older reports use various per-line / per-format split files (see the [IL DOI consumer-complaint reports landing](https://idoi.illinois.gov/reports/consumer-complaint.html) for the catalog). Out of scope for v1.

## What's not in here

- **Pre-2018 data.** Multiple PDFs per year, varying schemas. Can be added later if value justifies the parser work.
- **2017 and 2015 layouts** with separate "by Company Name" / "by Ratio" / per-line PDFs. Same as above.
- **Reason-code columns.** Skipped in v1; preserved in source PDFs.
- **NAIC group rollups.** Companies listed individually.
