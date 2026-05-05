# Methodology — Wisconsin OCI Insurance Report

## What WI OCI publishes

An annual *Wisconsin Insurance Report* (WIR), a multi-section document covering insurer market operations, financial statements, and consumer-services activity. The complaint data lives in the "Division of Market Regulation and Enforcement" section, in:

- **Table I — Total Complaint Files** (multi-year history; received and closed counts).
- **Table II — Complaints Filed By Type of Insurance** (current year + prior year, broken into 11 sub-lines + 3 totals + grand total).
- **Table III — Reasons for Complaints** (Claim Handling / Policyholder Service / Marketing & Sales / Underwriting).
- **Table IV — Amounts Recovered for Complainants** (per-line × per-reason matrix of $ recovered).
- **Table V — Additional Reviews** (per-line counts).

This pipeline extracts only **Table II** for v1. The other tables are preserved in the source PDFs for later expansion.

## Bucket mapping (canonical taxonomy)

WI's Table II data is workload counts, not regulator findings. The unified viewer treats it as `regulator_finding` category but in line-only mode (no outcome buckets) — same as CO DOI workload, VA SCC workload, NAIC IDRR.

A complaint that involves more than one type of insurance is counted in multiple sub-line rows but **only once** in the per-section totals (Total A&H, Total P&C) and the Grand Total. So sub-lines + grand_total ≠ sum-of-sub-lines.

## Line slugs

| WIR label | Canonical slug |
|---|---|
| Group Accident and Health | `group_health` |
| Individual Accident and Health | `individual_health` |
| Medicare Supplement | `medicare_supplement` |
| Long-Term Care | `long_term_care` |
| Total Accident and Health | `total_accident_health` |
| Automobile | `auto` |
| Homeowners, Tenants, Farmowners | `homeowners_tenants_farmowners` |
| Fire, Allied Lines, Other Property | `fire_allied_other_property` |
| General Liability/Liability | `general_liability` |
| Worker's Compensation | `workers_comp` |
| All Other Lines | `other_pc` |
| Total Property and Casualty | `total_property_casualty` |
| Life, Including Credit and Annuities | `life_credit_annuities` |
| Grand Total | `grand_total` |

## Canonicalization rules

Each WIR contains Table II for the report year and the prior year. Across 5 consecutive reports, every (data_year, line) appears in 1–2 reports:

- The most recent year (2024 here) appears only in the 2024 WIR.
- The earliest year (2019 here) appears only in the 2020 WIR.
- Every middle year (2020-2023) appears in 2 reports.

For canonical output, when a value appears in multiple reports, the **latest** report's value wins. This handles late-arriving complaint reclassifications. The audit parquet `wi_complaints_all_versions.parquet` preserves every value for cross-checking.

## Source quirks

- **2021 PDF layout:** Table II is rendered side-by-side with Table I (Total Complaint Files history). pdfplumber's text extraction interleaves the two tables, so the 2021 report's Table II yields only 7 of 14 lines per year. Cross-fill from neighboring reports (2020 and 2022) means the canonical output is still complete.
- **Apostrophe variation:** "Worker's" appears with both straight (`'`) and curly (`'`) apostrophes across reports. `LINE_NORMALIZE` handles both.
- **Header text mangling:** the 2021 report renders the Table II header as "Complaints Fil ed By Type of Insurance" (extra space). The locator regex tolerates the variant.

## Temporal anchor

Calendar year. WI doesn't use fiscal-year reporting for complaint data.

## What's not in here

- **Per-company complaint counts or indexes.** OCI publishes per-company data via an interactive lookup tool at <https://oci.wi.gov/Pages/Consumers/CompanyComplaintHistory.aspx> (separate URL). Not in v1.
- **Reasons for complaints (Table III).** Could be added later as a separate parquet.
- **Amounts recovered (Table IV).** Per-line × per-reason matrix; deferred to v2.
- **Additional reviews (Table V).** Deferred to v2.
- **Pre-2019 data.** Earlier WIR PDFs use different formats and may need separate parser logic.
