# Methodology — Maryland MIA §27-1001 bad-faith complaints

## What MIA publishes

Md. Insurance Article §27-1001(h) requires the Insurance Commissioner to file an annual report with the General Assembly summarizing the prior fiscal year's first-party bad-faith complaints, their dispositions, and any related enforcement actions. The 18 reports for FY 2008 – FY 2025 are in [`source_reports/`](source_reports/).

Each report's headline table ("Table 1" or, in later years, "Table 2") shows for each fiscal year:

- Total complaints filed
- Settled / withdrawn / dismissed (no merits decision)
- Decided on the merits, broken into:
  - **No violation** — regulator decided for the insurer
  - **Breach to pay only** — regulator found the insurer breached the duty to pay (insured prevailed on damages) but did *not* find absence of good faith (no fee-shifting under §27-1001). Broken out as a separate row starting with the FY 2022 report; appears in earlier reports only as footnotes.
  - **Absence of good faith** — regulator found bad faith (full insured win)

## Bucket mapping (canonical taxonomy)

The unified viewer uses a 4-bucket cross-state taxonomy. MD's MIA columns map directly:

| Canonical bucket | MD column | Color in viewer |
|---|---|---|
| `against_insurer` | `bad_faith` | red |
| `mixed` | `breach_pay_only` | gold |
| `for_insurer` | `no_violation` | blue |
| `no_decision` | `settled_wd_dismissed` | gray |

`on_merits = against_insurer + mixed + for_insurer` (= the denominator for the rate metric).

The headline rate is `bad_faith / on_merits` (matches MIA's own `pct_insured_wins`). An alternative rate `(bad_faith + breach_pay_only) / on_merits` is also computed but is only fractionally different (29/493 vs 28/493) since `breach_pay_only` has just 1 case across 18 years.

## Temporal anchor

Maryland fiscal year, ending June 30. Year labels in the data and the viewer refer to the year the FY *ends* (e.g., "FY 2025" = July 1, 2024 – June 30, 2025).

FY 2008 is a partial year (Oct 1, 2007 – Jun 30, 2008) because the statute took effect Oct 1, 2007. Annotated as `partial_year: 2008` in the viz manifest.

## Source selection across years

Each fiscal year's figures are taken from the most recent annual report that includes that year. The MIA's reports include retrospective tables (typically the prior 5–6 years) that occasionally update earlier figures as cases close on appeal. For each row, [`scripts/build.py`](scripts/build.py) records which report's table is the authoritative source in the `source` column of `data.csv`.

Two specific reconciliations:

1. **FY 2011** — original FY 2011 report had Settled=8 / Violation=2 / NoViol=16. By FY 2013 it was re-tabulated to 7/1/18. The retrospective figure is used.
2. **FY 2025** — Table 1 has an internal arithmetic discrepancy (27 settled + 30 on-merits ≠ 52 total). The on-merits decomposition is internally consistent and used verbatim; the settled bucket is recorded as 22 to reconcile to the report's headline 52.

## What's not in here

- **Per-line breakdown.** §27-1001 covers property/casualty first-party claims only; the annual reports do not split the four buckets by sub-line.
- **Per-insurer breakdown.** Same — not in the annual reports.
- **Commissioner-tenure overlay.** The supplied [`chart.png`](chart.png) shades calendar bands by MIA commissioner to test a specific hypothesis about Therese Goldsmith's tenure (FY 2012–2015 had a notably elevated against-rate). That's MD-specific hypothesis tooling; the unified viewer does not reproduce it.
- **Third-party / claim-handling complaints.** §27-1001 is the first-party bad-faith statute. Maryland's other complaint streams (e.g., MIA Consumer Complaint Forms for any line of insurance) are a separate workstream not in this dataset.
