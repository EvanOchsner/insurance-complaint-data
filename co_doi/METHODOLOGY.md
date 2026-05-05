# Methodology — Colorado DOI Annual Complaint and Recoveries Reports

## What CO DOI publishes

A short PDF report each fiscal year (CO FY ends June 30) covering:

1. **Money recovered for Colorado consumers** — dollar amounts the DOI's Consumer Services Section extracted from carriers, broken into a few line-of-business categories. The categories shift each year.
2. **Workload counts** — total P&C complaints received, total L&H complaints received, total complaints + inquiries received, total complaints + inquiries closed. From FY 2024 onward, sub-line breakdowns for homeowners and health.

Plus narrative pages on specific consumer cases (not extracted).

## What the recovery $ means

Per the FY 2024-25 PDF page 4:

> This is money restored to consumers in situations where the DOI finds that an insurance company improperly denied a claim or did not initially pay the correct claim amount. Recoveries can also come about when a company is delaying payment on a claim or has not followed state insurance law and regulations.

So recoveries combine: (a) reversed denials after DOI intervention, (b) improperly-low payments corrected, (c) delayed payments expedited, (d) statute-violation refunds. It's a directional indicator of regulator-required carrier action, but not a per-complaint disposition count.

The DOI does not publish a parallel "complaint count by disposition" series with the same breakdown.

## Why this isn't projected onto the canonical 4-bucket outcome taxonomy

The canonical taxonomy (`against_insurer / mixed / for_insurer / no_decision`) requires per-complaint-disposition counts, which CO doesn't publish in this report. Rolling up dollar amounts into "against_insurer" wouldn't be apples-to-apples with TX/CT/MD's complaint counts. So CO renders in line-only mode without outcome buckets.

## Workload count_type distinctions

Three values:

- **`received`** — formal complaints received (FY 2023 and earlier, FY 2024).
- **`closed`** — complaints + inquiries closed during the FY.
- **`received_with_inquiries`** — FY 2025 reframed the metric to include both complaints and inquiries in the "received" totals. Recorded as a separate count_type so cross-year comparisons don't silently mix scopes.

## Line slugs

| CO category | Canonical slug |
|---|---|
| Property & Casualty | `property_casualty` |
| Life & Health | `life_health` |
| Homeowners | `homeowners` |
| Auto | `auto` |
| Health | `health` |
| Life and Annuity / Life, LTC, Annuity | `life_annuity` |
| Marshall Fire (catastrophe-specific, FY 2023 only) | `marshall_fire` |
| Other Property & Casualty | `other_pc` |
| Other (non-line catch-all, FY 2025) | `other` |
| All-lines aggregate | `all_lines` |
| Statewide grand total | `total` |

Some lines are subsets of others (homeowners ⊂ property_casualty, health ⊂ life_health). Don't sum sub-lines + parent — you'll double-count.

## Why hand-verified inline data instead of parser

The 4 PDFs have inconsistent layouts:

- FY 2022 narrative-style ("In FY 21-22 the Division recovered a total of $X").
- FY 2023 catastrophe-tinged categories (Marshall Fire).
- FY 2024 introduces homeowners + auto sub-line splits.
- FY 2025 adds Other P&C; reframes received counts to include inquiries.

A robust regex extractor across all four formats wasn't worth the complexity for 4 rows × ~7 fields. Hand-verifying inline values against the source PDFs is faster, more reliable, and trivially extensible. The PDFs themselves are downloaded with sha256 anchors so any future audit can verify values against the canonical source.

Each row in `02_build.py` carries an inline comment citing the page and the labeled value in the source PDF.

## What's not in here

- **Per-company complaint indexes.** CO publishes these via an Oracle-backed interactive tool at <http://www.dora.state.co.us/pls/real/ins_comp_ratio_report.std_report_page>. URL-form scraping is out of scope for v1.
- **Pre-FY 2022 reports.** Only 4 fiscal years are currently posted on the landing page.
- **Reason-code or coverage-type breakdowns** that appear in narrative form on later pages of each PDF.
- **The "Consumers' Stories" narrative cases** — not structured data.
