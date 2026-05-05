# Methodology

## Two streams, two metric definitions

WA gives us two complementary datasets, each capturing a different stage of the bad-faith process:

### Stream 1 — IFCA notices (plaintiff-side, 2025-2026)

Per Washington's Insurance Fair Conduct Act (RCW 48.30.015), a plaintiff who wants to sue an insurer for unreasonable claim denial must file a **20-day notice** with both the insurer and the OIC. The OIC publishes an annual log of every notice it receives.

**A notice is not a finding.** It is one party's allegation that the insurer acted unreasonably, asserted as a precondition for suing under IFCA's treble-damages remedy. Some notices are cured by the insurer within the 20-day window (no lawsuit follows); some lawsuits proceed; some plaintiffs withdraw. The notice log measures **pre-litigation pressure**, not insurer wrongdoing per se.

This is the same conceptual category as the FL CRN dataset. Plotting IFCA notice counts on the same axis as TX `Confirmed` or CA `Justified` would be a category error. The cross-state visualization should keep IFCA + CRN on a separate panel.

**IFCA explicitly excludes health insurance** (RCW 48.30.015 limits to first-party property/auto disputes). Health claims sometimes appear in the IFCA log (when packaged with auto med-pay or a homeowners claim that includes medical components) but the bulk of health-coverage disputes in WA flow through different paths.

### Stream 2 — OIC consumer complaints (regulator-side, 2020-2024)

The OIC Annual Report includes a single bullet on the "Consumer protection" page: "Processed N consumer complaints, resulting in recovery of over $X million." That's the regulator workload count, capturing every formal complaint the OIC opened, investigated, and closed in the calendar year.

**This is the WA equivalent of TX TDI's complaint volume or CA CDI's `complaints_closed`** — a regulator-side workload metric. WA does not, however, publish a per-line breakdown or a "found in favor of insured" subset comparable to TX `Confirmed` / CA `Justified` / NY `upheld`. The `total_complaints` column is the only year-by-year regulator-side number we can extract from the AR.

A `recoveries_millions` column is captured alongside, also from the AR text. It's the dollar amount the OIC's intervention recovered for consumers — a different metric than complaint count, and informative on its own.

## Year mapping

- **IFCA**: each PDF is named for its calendar year (e.g., `2026-notices-of-potential-lawsuits.pdf` covers Jan 2026 onward). The IFCA # suffix (`.YY`) confirms the data year directly. Coverage in this build: 2025 + 2026 partial.
- **AR**: each AR is for the prior calendar year (e.g., the AR published in mid-2025 covers CY 2024). We extract the year from the URL/filename. Coverage: 2020-2024.

## Validation

- **Hard fail:** any IFCA PDF that produces 0 parsed rows.
- **Hard fail:** any AR PDF where the `Processed N consumer complaints` regex doesn't match.
- **Soft check (logged):** IFCA # sequence completeness per year. Both 2025 (1-1439) and 2026 (1-502) are gap-free in the 2026-05-04 build.
- **Soft check:** every IFCA row's `data_year` (extracted from the IFCA #) matches the source PDF's filename year.
- **Spot-check via PDF text:** the AR's "Processed N" sentence is the source of truth — we extract verbatim from the same sentence rather than from a separate table.

## Line-of-insurance normalization

The IFCA "Line of Insurance" column is free-text-ish (e.g. "Underinsured Motorist", "UIM", "Personal - auto", "Motor vehicle", "Homeowners Insurance -- Property" all coexist). `02_parse.py` normalizes via a small regex table to the canonical set:

| Canonical | Match patterns |
|---|---|
| UIM | `uim`, `under-insured motorist`, `underinsured motorist` |
| UM | `um`, `uninsured motorist` |
| PIP | `pip`, `personal injury protection` |
| Auto | `motor vehicle`, `automobile`, `auto` (when not "auto glass") |
| Homeowners | `homeowner`, `home owners` |
| Property | bare `property` |
| Liability | `liability` |
| Health | `health`, `medical` |
| Life | `life` |
| Title | `title` |
| Workers Comp | `workers comp` |
| Other | (any non-empty value not matched above) |
| Unknown | (empty) |

The order matters — UIM is checked before "auto" because UIM rows often also mention auto. The original raw value is preserved in `line_of_insurance` for any downstream re-classification.

## What's not in this dataset

| What | Why |
|---|---|
| IFCA notices for 2008-2024 | OIC removes old PDFs; only 2025+ are online. Wayback Machine or PRR required. |
| Per-line breakdown of OIC AR complaints | Not published in the AR text — only a single annual scalar. |
| Per-company complaint history | Available via the OIC agent/company lookup tool; deferred to v2. |
| Notice-to-lawsuit conversion rate | Would require linking IFCA notices to WA superior court filings. Out of scope. |
| Top-counsel concentration | Recoverable from the per-notice file (the `complainant_attorney` column) but not aggregated in v1 outputs. |
| RCW/WAC citation taxonomy | The `rcw_wac_cited` column is preserved verbatim; no taxonomy applied. |
| Workers' comp | Regulated by WA Department of Labor & Industries, not OIC. Not in either source. |
| Health insurance external appeals | Separate program; not in either source. |

## Notes on the OIC's User-Agent gate

The OIC's Varnish CDN cache returns HTTP 403 for unrecognized User-Agents (including the project's standard `insurance-complaint-rates/...` UA). The downloader uses a browser-like Chrome UA. We continue to identify ourselves transparently in the project's footer documentation and PROVENANCE.md; this is a workaround for the cache, not a stealth scrape.
