# Methodology — Idaho DOI Consumer Complaint Comparison Tables

## What Idaho DOI publishes

A single page at <https://doi.idaho.gov/information/public/reports/complaint-index/> with a 7-column HTML table covering the top-20 premium-writing companies per line per year. Currently 3 years (2018–2020) × 4 lines × top-20 = 240 rows.

## Bucket mapping (canonical taxonomy)

Idaho's data is a complaint-index ratio, not a regulator finding. The unified viewer treats it the same as IN and KS (under `regulator_complaint_index` category, no outcome buckets).

## Line slugs

Idaho's category labels normalize as follows:

| Source label | Canonical slug |
|---|---|
| Auto | `auto` |
| Homeowner | `homeowners` |
| Group Accident/Health | `group_health` |
| Individual Accident/Health | `individual_health` |

We preserve the group-vs-individual health distinction. KS lumps all health into `health`; IN uses a single `health` slug. Cross-state rollups should account for this if needed.

## What the complaint index means

Idaho's definition (from the page):

> The complaint index shows the performance of a company relative to other companies in the same market. To calculate the complaint index, we take the company's annual complaint ratio, and divide it by the total number of complaints about all the companies in the same market. A company with a complaint index higher than 1 has more complaints than average.

Standard NAIC convention. Above 1.0 = more complaints than market share would predict.

## Inclusion rule and median caveat

Top-20 premium writers per line per year. Idaho is a small market: many top-20 entries had 0 complaints in any given year, so the median index per slice is often 0. Use the per-company file rather than the median for ranking.

## Source quirk: swapped columns in 2018 Individual Accident/Health

5 of the 20 rows in the 2018 Individual Accident/Health slice have the Complaints and Index columns swapped at source — the Complaints field holds a decimal index value (e.g. 0.33703) and the Index field holds an integer count (e.g. 2). This is a data-entry error, not a definitional issue.

The parser detects swap candidates per row (Complaints contains a `.` AND Index is integer-like) and corrects them inline. The run log records the count of corrections per build.

## Temporal anchor

Data year, calendar year. Idaho publishes year-N data the following year.

## What's not in here

- **Pre-2018 or post-2020 data.** The DOI page has not been refreshed since the 2020 data went up. Older years would require either a public-records request or Wayback Machine pull.
- **Companies outside the top-20 by premium.** Smaller carriers do not appear in the comparison tables.
- **NAIC group rollups.** Companies are listed as published.
