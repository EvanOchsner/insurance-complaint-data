# Methodology

## What this dataset measures

> For each calendar year and each statutorily-defined line of insurance, how many Civil Remedy Notices (CRNs) were filed with the Florida Department of Financial Services?

The temporal anchor is the **Submission Date** of the CRN, as recorded by FDFS at filing time. Calendar year of submission is what FDFS itself uses to slice the data on its search form.

## What a CRN is

Florida Statute § 624.155 creates a private right of action against insurers for bad faith. As a *condition precedent* to bringing a bad-faith suit, the insured (or their attorney) must file a Civil Remedy Notice with FDFS at least 60 days before filing the lawsuit, naming the insurer and identifying the alleged statutory violations. FDFS publishes every CRN as a public record.

A CRN therefore captures a moment of **pre-litigation pressure** — when a plaintiff's attorney has decided the matter is serious enough to file a public allegation that the insurer has acted in bad faith, but before any court has weighed in. The 60-day window gives the insurer an opportunity to "cure" the alleged violation; if cured, no lawsuit follows. If not, suit may proceed.

## What "Confirmed" / "Justified" means in this dataset

It doesn't. A CRN is a one-sided allegation by the complainant or their counsel. **There is no regulator review.** FDFS's role is purely registrar: they record the CRN, give it a file number, and make it publicly searchable. They do not investigate, adjudicate, or classify it.

This is the most important difference between FL CRN data and the other states' datasets in this project:

| State | What's counted | Who decided it |
|---|---|---|
| MD MIA | "In favor of insured" complaints | The state regulator (after investigation) |
| TX TDI | `Confirmed` complaints | The state regulator (after investigation) |
| CA CDI | `Justified` complaints | The state regulator (after investigation) |
| **FL FDFS** | **CRN filings** | **A plaintiff's attorney (allegation only)** |

FL CRN counts therefore measure **litigation pressure**, not insurer wrongdoing per se. They cannot be put on the same axis as the other three.

## Aggregation rule

FDFS exposes the count of matching records in the search-result page header text ("Records 1 - X of N"). Our crawler:

1. Bootstraps a fresh ASP.NET WebForms session.
2. Submits a search filtered by date range (full calendar year) and `Type of Insurance`.
3. Parses N from the result page header.
4. Records `(year, type_of_insurance, count)`.

The same logic with no insurance-type filter gives the per-year total (`type_of_insurance = "ALL"`). The sum of per-line counts is logged side-by-side with the no-filter total for cross-validation; small deltas may occur if FDFS records have a null `type_of_insurance` field that's excluded from per-line filters.

## Year coverage

The FDFS search interface returns 0 records for years before ~2014 — earlier filings (if any) are not in the searchable digital system. The earliest year with non-zero counts is the de-facto lower bound for this dataset.

The most recent calendar year is partial (CRNs are filed throughout the year). Treat the trailing year as preliminary.

## What's not in this dataset

| What | Why |
|---|---|
| Pre-2014 CRNs | Not in the digital search system (FDFS may have older paper records). |
| Per-filing detail (insurer, statute, reason, attorney, response, outcome) | Requires either a public records request to FDFS (see `public_records_request.md`) or a multi-day per-filing scrape against `ViewFiling.aspx?fid=N`. v1 deliberately limits scope to counts. |
| § 627.70152 Intent-to-Initiate-Litigation notices (residential property breach-of-contract pre-suit, post-2021) | Separate FDFS system, separate URL, separate schema. Out of scope. |
| Insurer name normalization / NAIC group rollup | Not meaningful at counts-only granularity. |
| Whether a CRN was "cured" or proceeded to a lawsuit | Tracked inconsistently in the disposition field on detail pages; not in the search header. |
| Linkage to actual filed lawsuits | Would require matching CRNs to FL state-court filings (per-county) and federal filings (FJC IDB). |
| Florida regulator complaints (FL OIR receives consumer complaints) | A separate stream from CRNs; would be the FL analogue of TX TDI / MD MIA. Not in this folder. |

## Why hurricane-year and AOB-era spikes are real

Florida CRN volume is dominated by two structural drivers:

1. **Hurricanes.** Catastrophic events produce surges in property-damage claims, claim disputes, and CRN filings. Major events in our coverage window:
   - **Irma** (Sep 2017) — large 2017–2018 spike.
   - **Michael** (Oct 2018) — modest 2018–2019 contribution.
   - **Ian** (Sep 2022) — very large 2022–2023 spike, including assignment-of-benefits aftermath.
   - **Helene/Milton** (Sep–Oct 2024) — likely visible in 2024 totals.

2. **AOB litigation.** Florida's Assignment of Benefits ecosystem (roofers, plumbers, water-mitigation contractors taking assignment of homeowner claims and litigating directly) produced a wave of bad-faith CRN filings tied to AOB rather than to traditional policyholder disputes. House Bill 7065 (2019) curtailed this; SB 2A (2022) further restricted it. The post-2022 trajectory reflects these legal changes.

Treating these spikes as data quality issues would be wrong — they are the actual phenomenon. But comparing FL CRN volume to other states' regulator complaint counts without context is misleading; both effects are FL-specific structural features.

## Validation

- **Hard check:** every search response must contain a "Records X of N" header or a "no records" indicator. Anything else triggers up-to-3 retries with backoff; persistent failures abort the run.
- **Hard check:** the `(year, line)` cube must be complete. Missing combinations fail.
- **Soft check:** sum of per-line counts vs no-filter total. Small deltas are expected (rows with null line). Logged in `run_log.txt` for review.
- **External cross-check:** the crawler can be spot-verified against the live search UI at <https://apps.fldfs.com/civilremedy/SearchFiling.aspx>. Submit a date range manually; the "Records X of N" you see should match our parsed value.
