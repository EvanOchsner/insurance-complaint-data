# Methodology

## What this dataset measures

Two questions, two output streams:

1. **State-level complaint volume.** For each year 2020-2024, how many consumer complaints did CDI close, open, and recover dollars on?
2. **Per-line "Justified" complaint intensity.** For each `(year, line)` covered by a CDI Consumer Complaint Study, how many of the regulator's Justified findings were issued against the top-50 insurers in that line, and at what rate per 100,000 exposures?

These are *two different denominators*. State-level volume includes all lines and all dispositions; the per-line "Justified" series is a subset.

## Source publications

### Annual Report of the Insurance Commissioner

A long PDF (200+ pages) published each spring covering the prior calendar year. We extract two structured tables:

- **CSMCB Results table** — printed once per AR, gives the year's `Complaint Cases Opened`, `Complaint Cases Closed`, `Total Amount of Consumer Dollars Recovered`, etc. for the AR's calendar year.
- **Percentage of Complaints by Lines of Coverage** — a 4-column table showing the trailing 4 years' breakdown across 8 CDI coverage labels (Automobile, Accident & Health, Homeowners, Misc./Other, Life & Annuity, Fire/Allied/CMP, Liability, Earthquake).

The CSMCB table gives one row per AR; combining 5 ARs gives 5 rows in `state_yearly`.

The line-percentage table overlaps across ARs (each AR re-prints prior years' percentages). Our pipeline keeps **the most recent AR's value** for each `(year, coverage_type)` — CDI's own latest reclassification wins.

### Consumer Complaint Study

A short PDF (1-2 pages) published each summer for each line (Auto, Home, Life). Each study reports the trailing 3 years' data (e.g., the 2025 study covers 2024, 2023, 2022). For each of the top-50 insurers in that line, the study lists:

- Approximate exposure count (single value, snapshotted at study publication)
- Justified Complaint Ratio per 100k exposures, separately for each of the 3 trailing years
- Number of Justified Complaints, separately for each of the 3 trailing years

Per the **California Code of Regulations Title 10, Subchapter 7.4**, a complaint is **Justified** if the regulator determined the licensee acted in contravention of statute, regulation, or contract. This is a stable definition across years.

## What "Justified" is NOT

- **Not a finding of bad faith.** Bad faith is a legal term of art determined by a court, not a regulator.
- **Not a count of lawsuits.** Justified findings are administrative.
- **Not exhaustive.** Disputes resolved without a CDI complaint (private settlement, arbitration, court-only) never enter this dataset.
- **Not the same as "won by consumer."** A complaint can be Justified without producing any monetary or contractual remedy; CDI also tracks "Positive Outcome" and "Compromised Settlement" categories that aren't in our v1 outputs.

## Year mapping

Each Consumer Complaint Study is named for its publication year, but its data covers the three calendar years *before* publication. Our parser hardcodes:

```
data_year = study_year - 1 - column_offset      # offset 0, 1, 2 → most-recent, mid, oldest
```

So:
- 2025 study → 2024, 2023, 2022
- 2024 study → 2023, 2022, 2021
- 2023 study → 2022, 2021, 2020

A given data year may be reported by 1-3 studies. When studies disagree (CDI sometimes re-issues prior numbers as data is updated), the **most recent study's** value wins.

## Aggregation rule for the headline

`ca_complaints_yearly_justified.parquet` answers: *"For year Y in line L, summing across the top-50 insurers in CDI's most recent assessment, how many Justified complaints were found?"*

- For each `(year, line)`, we identify the **most recent study covering that year**, and sum the 50 companies listed in *that* study only.
- This avoids the trap of unioning top-50 lists across studies, which would inflate the company count and double-count companies that ranked top-50 in multiple studies.
- The trade-off: companies that drop out of the top-50 between studies stop contributing in older years. Net effect: the headline measures "*today's* top-50, in *that* year" — a moving target by construction, but the most defensible single-number summary.

The per-company panel `ca_complaints_company_yearly.parquet` keeps the union view (any company that ever ranked top-50 in any study covering year Y), with each company's value coming from the most recent study that included it. Use that file if you want to ask "how did Company X trend?" rather than "what did the headline look like?".

## Year coverage

| Stream | Years | Notes |
|---|---|---|
| `state_yearly` | 2020 – 2024 | Limited by AR archive availability online. |
| `state_by_line_pct` | 2017 – 2024 | Earliest covered by 2020 AR's trailing 4-year table. |
| `company_yearly` | 2020 – 2024 | 2020 from 2023 study only; 2024 from 2025 study only. |
| `yearly_justified` | 2020 – 2024 | Same. |

The 2024 calendar year is fully closed (the 2024 AR was published in 2025 and the 2025 study covers 2022-2024); no partial-year flag is needed. **2025 data will become available** when CDI publishes its 2026 study and 2025 Annual Report — the pipeline can be re-run then with no code changes.

## What's not in this dataset

| What | Why |
|---|---|
| Pre-2020 data | CDI removes older PDFs as new ones publish. Earlier years would require Wayback Machine, FOIA, or a long-running snapshot strategy. |
| Health managed-care complaints | DMHC handles those; CDII consolidates across agencies — out of scope for v1. |
| All CA complaints by Justified/Not split | CDI does not publish a state-wide percentage justified. The per-line top-50 figures we have are partial. |
| Per-company NAIC group rollup | Each subsidiary appears as its own row; combining (e.g., all State Farm subsidiaries) is left to downstream consumers. |
| Workers' compensation | Regulated by DWC, separate agency. |
| Independent Medical Reviews (IMR) | A separate program in the same AR; out of v1 scope. |
| The CIC § 1858.35 disposition tables | A rate/underwriting subset only; we capture the broader percentage-by-line table instead. |

## Validation

- **Hard check (in script):** every Annual Report parses successfully and yields a non-null `complaints_closed`. The 5 expected values (44,535 / 41,181 / 44,712 / 56,827 / 62,002) match the AR executive summary text on each PDF's first ~10 pages.
- **Hard check:** every Consumer Complaint Study yields ~50 company rows × 3 data years = 150 raw rows. Soft warning if `n_companies < 45` per study.
- **Soft check:** `n_companies = 50` for every `(year, line)` in the headline `yearly_justified`. Anything else means the most-recent-study has fewer top-50 entries than expected.
- **External cross-check available:** the live composite landing pages (e.g., <https://www.insurance.ca.gov/01-consumers/120-company/03-concmplt/autocomposite.cfm>) show the same data extracted here. The published Justified Complaint Ratio per company should match `justified_count / exposure × 100,000` to ±0.05 (rounding tolerance).
