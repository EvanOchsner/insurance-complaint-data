# Methodology — Virginia SCC Bureau of Insurance

## What VA SCC publishes

Each fiscal year, the State Corporation Commission's Bureau of Insurance files a 2-page annual report (`{YYYY}BOI.pdf`) alongside the broader SCC umbrella annual report. The BOI report has a flat list of activity counts for the FY, including:

- Property & Casualty insurance complaints received (workload)
- Life & Health insurance complaints received (workload)
- Several non-complaint counts (market exams, ombudsman inquiries, agent licenses, etc.)
- An External Review block: for health-coverage appeals only, total requests reviewed broken into eligible/ineligible, with a 5-bucket disposition for the eligible cases.

Only the workload + ER blocks are extracted by this pipeline. The other activity counts are out of scope.

## Fiscal year semantics

Virginia state fiscal year runs July 1 – June 30. Year labels in the data refer to the FY-end calendar year (e.g. "FY 2025" = July 1, 2024 – June 30, 2025).

This differs from NAIC IDRR, which uses calendar years. So VA's FY 2022 total (P&C 2,322 + L&H 1,347 = 3,669) doesn't exactly match IDRR's calendar-year 2022 (3,795); the gap is the 6-month calendar-vs-fiscal misalignment plus minor definitional differences.

## External Review bucket mapping (canonical taxonomy)

The unified viewer's outcome taxonomy is `against_insurer / mixed / for_insurer / no_decision`. VA SCC's ER dispositions map as follows:

| Canonical bucket | VA SCC ER dispositions |
|---|---|
| `against_insurer` | Final Adverse Decision Overturned by Reviewer + Health Carrier Reversed Itself |
| `mixed` | Final Adverse Decision Modified or Partially Overturned |
| `for_insurer` | Final Adverse Decision Upheld by Reviewer |
| `no_decision` | Ineligible ER Requests + Terminated/withdrawn |

Rationale:

- **Reversed-Itself → against_insurer.** When the carrier reverses its denial mid-review (typically because the regulator's review prompted reconsideration), the consumer prevails. This is functionally a regulator-action-induced outcome favorable to the consumer; it belongs in the same bucket as Overturned.
- **Modified → mixed.** "Modified or Partially Overturned" is a partial finding for the consumer.
- **Ineligible → no_decision.** ER requests deemed ineligible for review never reach a merits decision.
- **Terminated/withdrawn → no_decision.** Cases pulled before a merits decision.

`on_merits = against_insurer + for_insurer + mixed` (the eligible-and-decided pool). `against_rate_of_decided = against_insurer / on_merits` is the headline rate, matching the project's universal definition.

## Workload buckets (no outcome breakdown)

The P&C and L&H complaints-received counts are workload signals. The viewer presents them in line-only mode with two series (P&C, L&H), no stacked-bar outcome breakout. They are *not* projected onto the canonical taxonomy because the source doesn't publish dispositions for them.

## Scope caveat for ER

The External Review process covers managed-care health-coverage appeals only. Eligible cases are those with an adverse coverage decision that's reviewable under VA Code §38.2-3463 (and federal ACA equivalents for self-funded plans operating in VA).

That makes the ER population **fundamentally different** from the broader complaint population:

- **Pre-filtered for adjudicability.** Only cases with a clear medical-necessity or coverage question reach the eligible pool. Frivolous or jurisdictionally-misplaced complaints are filtered out as ineligible.
- **High against-rate is normal.** External-review pools across states routinely run 40–60% against-insurer because the eligibility filter removes low-merit cases. VA's ~54% lifetime rate is in line with this; do not compare it directly against, e.g., MD MIA's 5.68% (which has a much broader denominator that includes settled/withdrawn/no-jurisdiction cases).

## Data filtering

The parser hard-fails if any of the fixed labels go missing on a future report (forces explicit handling of layout changes). OCR misreads where digits look like letters ("I" → 1, "O" → 0) are normalized inline.

## What's not in here

- **Per-line dispositions for non-health complaints.** The BOI reports do not publish dispositions for P&C or non-appeal L&H complaints.
- **Per-company breakdowns.** Out of scope for these reports.
- **Pre-FY 2022 coverage.** The BOI reports posted at the SCC annual-reports landing currently cover only FY 2022 onward. Earlier years would require either a public-records request or a Wayback Machine pull.
