# Tail states — NAIC-only coverage

Phase 4 of [`multi_state_acquisition_plan.md`](multi_state_acquisition_plan.md). This document describes the 30 jurisdictions for which the project's only complaint data source is the NAIC IDRR per-state, per-year volume series — no per-line, no per-company, no outcome breakouts. Acquiring richer state-specific data for these jurisdictions was deliberately out of scope per §8 of the parent plan.

The IDRR baseline for these states lives in [`naic_idrr/output/idrr_complaints_yearly.parquet`](naic_idrr/output/idrr_complaints_yearly.parquet) (canonical aggregate schema) and the per-state coverage table in [`naic_idrr/output/tail_states_coverage.csv`](naic_idrr/output/tail_states_coverage.csv).

## What's *not* in this list

Jurisdictions also currently NAIC-only but tracked elsewhere in the parent plan:

- **PRR-blocked (Phase 2):** Missouri, Michigan, Ohio. Public-records requests queued; see §6.6 + §9.5 of the parent plan.
- **Phase 3 dropped:** Pennsylvania, New Jersey, North Carolina. See §7.4 recon notes — PA reprints IDRR, NJ stops at 2013, NC has no public DOI annual report.
- **Phase 3 deferred:** Massachusetts. mass.gov edge-blocks UA-based fetches; needs browser automation. See §7.4.

Anyone needing "every state where IDRR is the only data" should union §6 + §7 + this list.

## Coverage of every tail state

All 30 jurisdictions below have continuous IDRR coverage 1998–2022 (24 data years) with one project-wide gap at 2003 (parser issue documented in [`naic_idrr/PROVENANCE.md`](naic_idrr/PROVENANCE.md)). No state-specific gaps were found. Mean annual complaint counts shown for context.

The five jurisdictions tagged **(Phase-5 candidate)** — LA, MN, OR, TN, VT — were called out in §8.2 as states with annual reports that may be worth pulling later. Reserved for a possible Phase 5; out of scope here.

| State | IDRR years | Mean annual complaints | Notes |
|---|---|---:|---|
| Alabama (AL) | 1998–2022 | 3,902 | ALDOI publishes only narrative annual reports; no machine-readable complaint breakout. |
| Alaska (AK) | 1998–2022 | 324 | Small market; AK DOI annual reports are PDFs without per-line tables. |
| Arkansas (AR) | 1998–2022 | 2,614 | AID consumer services data not published in extractable form. |
| Arizona (AZ) | 1998–2022 | 2,838 | AZ DIFI publishes annual reports without consistent per-line complaint tables. |
| Delaware (DE) | 1998–2022 | 3,154 | Small market; DOI annual reports are narrative. |
| Dist. of Columbia (DC) | 1998–2022 | 731 | DISB does not publish a per-line complaint dataset. |
| Georgia (GA) | 1998–2022 | 11,526 | Large market; OCI does not publish a public per-line or per-company complaint series. |
| Hawaii (HI) | 1998–2022 | 723 | Small market; ICA reports do not contain extractable complaint tables. |
| Iowa (IA) | 1998–2022 | 1,945 | IID annual reports are narrative-style. |
| Kentucky (KY) | 1998–2022 | 4,530 | KY DOI does not publish a public complaint breakout. |
| ~~Louisiana (LA)~~ | (graduated to `la_ldi/` 2026-05-05) | — | **No longer NAIC-only.** LDI publishes per-company NAIC-tradition complaint indices for 4 personal lines × 10 years (2015-2024). See [`la_ldi/`](la_ldi/README.md). |
| Maine (ME) | 1998–2022 | 1,081 | Small market; BOI annual reports are narrative. |
| Minnesota (MN) | 1998–2022 | 3,067 | Recon 2026-05-05: Phase-5 candidate **dropped**. MN Commerce's Policy Data & Reports surface contains only Fraud Bureau reports and legislative health-mandate evaluations — no published consumer complaint statistics. Real data would require a PRR. |
| Mississippi (MS) | 1998–2022 | 6,227 | MID does not publish a public complaint breakout. |
| Montana (MT) | 1998–2022 | 1,555 | Small market; CSI annual reports are narrative. |
| Nebraska (NE) | 1998–2022 | 1,610 | NDOI does not publish a public per-line complaint series. |
| Nevada (NV) | 1998–2022 | 2,776 | NV DOI does not publish a per-line public complaint series. |
| New Hampshire (NH) | 1998–2022 | 1,163 | Small market; NHID annual reports are narrative. |
| New Mexico (NM) | 1998–2022 | 1,334 | OSI publishes annual reports but no per-line complaint table. |
| North Dakota (ND) | 1998–2022 | 241 | Smallest market in this set; NDID has no machine-readable complaint dataset. |
| Oklahoma (OK) | 1998–2022 | 4,396 | OID does not publish a public per-line complaint series. |
| ~~Oregon (OR)~~ | (graduated to `or_dfr/` 2026-05-05) | — | **No longer NAIC-only.** DFR publishes per-company per-line indices PLUS Confirmed-Complaint counts (true outcome data) for 6 lines × 7 years (2019-2025). See [`or_dfr/`](or_dfr/README.md). |
| Rhode Island (RI) | 1998–2022 | 504 | Small market; DBR annual reports are narrative. |
| South Carolina (SC) | 1998–2022 | 3,292 | SC DOI does not publish a public per-line complaint series. |
| South Dakota (SD) | 1998–2022 | 883 | Small market; SD DOI has no machine-readable complaint breakout. |
| Tennessee (TN) | 1998–2022 | 3,358 | Recon 2026-05-05: Phase-5 candidate **dropped**. TDCI publishes only narrative press releases (e.g., "$15.67M returned to consumers in 2025; top-3 reasons: claim delays, claim denials, unsatisfactory settlement"). No per-line, per-company, or annual report with extractable tables. Real data would require a PRR. |
| Utah (UT) | 1998–2022 | 1,068 | UID does not publish a public per-line complaint dataset. |
| Vermont (VT) | 1998–2022 | 587 | Recon 2026-05-05: Phase-5 candidate **dropped**. VT DFR's "Legislative Reports" cover niche topics (virtual currency kiosks, workers'-comp-for-firefighters-with-cancer, prior-authorization, medical wait times). No published consumer complaint statistics, no per-line or per-company data. Smallest market in the project; real data would require a PRR. |
| West Virginia (WV) | 1998–2022 | 2,210 | WV OIC does not publish a public per-line complaint breakout. |
| Wyoming (WY) | 1998–2022 | 493 | Smallest non-DC market here; no machine-readable complaint dataset. |

The "Notes" column reflects the parent plan's working assumption that each tail state's regulator either does not publish a complaint breakout, publishes only narrative annual reports without a consistent per-line table, or — for the Phase-5 candidates — publishes something that may be extractable but was deferred. State-by-state web reconnaissance was not performed for this document; each note is the parent plan's stated rationale for excluding the state from Phases 1–3, not a fresh recon finding. Anyone planning Phase 5 should re-verify before scoping work.

## Reproducing this

```sh
python3 naic_idrr/scripts/03_canonicalize.py
# → naic_idrr/output/idrr_complaints_yearly.{parquet,csv}
# → naic_idrr/output/tail_states_coverage.csv
```

The coverage table above is generated from `tail_states_coverage.csv`; mean values come from the same script's per-state aggregation.
