# Methodology

## What this dataset measures

> For each U.S. state (and DC + territories) and each year from 1988 to the most recent FJC release, how many federal civil cases with **Nature of Suit = 110 ("Insurance")** were filed?

"Filed" is defined by the case's `FILEDATE` field in the FJC Integrated Database. The temporal anchor is the **calendar year** of `FILEDATE`, regardless of which fiscal/statistical year the IDB itself groups the case under. Calendar year avoids the FJC's mid-1990s fiscal/statistical-year discontinuity entirely and matches the year basis used by other downstream sources we'll join against (e.g., NAIC IDRR complaint counts).

## Filter

A row from `cv88on.txt` is included iff:

- `NOS == 110` ("Insurance" — actions alleging breach of insurance contract, tort claim, or other cause arising from an insurance policy)
- `FILEDATE` is non-null and parseable as `MM/DD/YYYY`
- Calendar year of `FILEDATE` is `>= 1988`

## Source-file choice: combined civil, not "terminations"

The FJC IDB exposes the civil dataset as a single combined file (`cv88on.zip` → `cv88on.txt`) that contains every case filed in or after 1988, regardless of whether the case has terminated. We use this combined file.

An earlier draft of the plan suggested using "the terminations file." That choice would systematically undercount recent years: cases filed in (e.g.) 2024 are still pending in large numbers and would be missing from a terminations-only file. Using the combined file, keyed on `FILEDATE`, gives us a true filings count that doesn't shrink as you approach the present.

## What "calendar year" means here

The IDB's `FILEDATE` is a date stamp, so calendar year is straightforward: `year = FILEDATE.dt.year()`. We do not use:
- `FDATEUSE` (a derived field used by the IDB internally for stat-year aggregation)
- `TAPEYEAR` (the year the row was added to the cumulative file)
- The FJC statistical year or fiscal year

Pre-1988 filings that happen to appear in `cv88on.txt` (because the case was still pending in 1988) are dropped. Including them would imply a comprehensive census of pre-1988 federal insurance filings, which this file does not provide.

## State mapping

The IDB encodes the originating district as `CIRCUIT` (1-2 chars) + `DISTRICT` (2 chars), which together form the 4-character district code used by the FJC office-codes spreadsheet. For example:

| `CIRCUIT` | `DISTRICT` | Joined | District |
|---|---|---|---|
| `0` | `90` | `0090` | District of Columbia |
| `4` | `16` | `0416` | District of Maryland |
| `11` | `3C` | `113C` | Southern District of Florida |

`scripts/districts.csv` is the single source of truth for the 94 federal judicial districts → 2-letter state code mapping. It was hand-curated and cross-checked against the office locations listed in `reference/office-codes.xlsx` (e.g., the offices in district `0205` are Hartford, New Haven, etc., confirming Connecticut).

The script enforces a hard failure if any district code in the filtered NoS=110 data is not present in `districts.csv` — this is the most likely correctness bug (silent loss of a district), so it's checked, not assumed.

## Origin breakdown

`output/insurance_filings_by_state_year_origin.parquet` adds an `origin_code` and `origin_label` column. The IDB's `ORIGIN` field distinguishes how the case arrived in federal court:

| Code | Label (this dataset) | Notes |
|---|---|---|
| 1 | Original | Filed in federal court directly |
| 2 | Removed from state court | Defendant (typically the insurer) removed under 28 USC §1441 |
| 3 | Remanded from appellate | Sent back from a US Court of Appeals |
| 4 | Reinstated/reopened | Previously closed case reopened |
| 5 | Transferred from another district (28 USC 1404) | Venue transfer |
| 6 | Multidistrict litigation transfer (28 USC 1407) | Consolidated MDL transfer |
| 7-13 | Other / subsequent codebook variant | Rare; combined accounts for <1% of NoS=110 rows. The FJC civil codebook PDF was not obtainable at compile time (see PROVENANCE.md), so labels for these codes are conservative pending verification. |
| -8 | Missing / not coded | IDB sentinel for an uncoded value |

The `Original` (1) vs `Removed from state court` (2) split is independently interesting: a rising removal share suggests insurers are increasingly using federal removal as a tactic. Nationwide, the removal share has trended from ~38% in 1988 to ~58% in 2025.

## What's NOT in this dataset

| What | Why |
|---|---|
| Pre-1988 federal civil filings | Different schema (`cv70to87`); v1 doesn't include them |
| State-court filings of any kind | No national source; collected per-state in sibling datasets |
| Insurance-flavored cases under other NoS codes | NoS 110 is the strictly-coded "Insurance" line; ERISA-related cases (NoS 791), Other Contract (190), and Other Personal Injury (360) may contain insurance disputes but aren't included here |
| Case-level enrichment (party names, judge, complaint text) | Requires PACER/CourtListener; out of scope |
| Per-capita / per-premium normalization | Requires Census + NAIC IDRR Vol. II; downstream task |
| Bad-faith-specific filtering | Requires complaint-text analysis (RECAP/CourtListener); out of scope |

## Why the trailing year is "partial"

The IDB is updated quarterly with about a two-month lag. A calendar year `Y` is fully visible only after the IDB release that follows roughly March of `Y+1`. The script writes the max `FILEDATE` it observed and labels the trailing year as partial in `run_log.txt`; downstream visualizations should grey out or drop the trailing point unless `max(FILEDATE) >= Y-12-31` AND the IDB release happened well after that.

## Validation

Cross-validation against the AOUSC Judicial Business reports (Table C-2A or equivalent) was *not* performed as a hard CI gate for this one-shot collection. Soft sanity checks the script does run:

- Hard failure if any `(CIRCUIT, DISTRICT)` value in the filtered data is missing from `districts.csv`.
- Hard failure if any joined row has a null `state`.
- Hard failure if any `(state, year)` pair appears more than once in the headline aggregation.
- Soft warning: share of NoS=110 rows with null `FILEDATE` (observed: 0.000% on 2026-05-04 run).
- Soft check printed to log: yearly nationwide totals (observed: 7K–18K range; consistent with published AOUSC totals for NoS 110).
- Soft check printed to log: spot table for `MD`, `CA`, `TX`, `FL` for the trailing 6 years.

If headline numbers ever look implausible after a re-run, the first thing to compare against is AOUSC Judicial Business Table C-2A (filings by NoS by district) for the same year.
