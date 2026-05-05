# Provenance

Source-of-record details for the FL FDFS Civil Remedy Notice counts dataset. Output files in `fl_crn/output/` are reproducible by re-running the crawler. Re-runs may show small deltas as FDFS records are added or amended.

## Primary data source

| Field | Value |
|---|---|
| Source | Florida Department of Financial Services, Civil Remedy Notice search |
| Search URL | <https://apps.fldfs.com/civilremedy/SearchFiling.aspx> |
| Detail URL pattern | `https://apps.fldfs.com/civilremedy/ViewFiling.aspx?fid=<NNN>` (not used in v1) |
| FDFS landing | <https://www.myfloridacfo.com/division/consumers/civilremedy> |
| Form revision | `DFS-10-363 Rev. 10/14/2008` |
| URL verified | 2026-05-04 |
| Authentication | Anonymous (ASP.NET WebForms session cookies) |
| User-Agent sent | `insurance-complaint-rates/1.0 (research; contact: evan.ochsner@gmail.com)` |
| Politeness | 2 second sleep between requests; up to 3 retries with exponential backoff on transient failures |

## Search-form schema (verified 2026-05-04)

The FDFS app is ASP.NET WebForms with `__VIEWSTATE`, `__EVENTVALIDATION` hidden state, and a `__doPostBack` JavaScript navigation model. Each search invocation:

1. GETs `SearchFiling.aspx` to bootstrap the session and capture hidden state.
2. POSTs back to `SearchFiling.aspx` with the date range, optional `ddlInsuranceType`, and `btnSearch=Search`.
3. Parses the result-page header text for `Records 1 - X of <total>`.

Form enums of interest:

**`ddlInsuranceType`** (9 values, 8-character padded codes):

| Label | Code |
|---|---|
| Accident & Health | `ACCHLTH ` |
| Life & Annuity | `LIFEANTY` |
| Medicare Supplement | `MEDICARE` |
| Auto | `AUTO    ` |
| Residential Property & Casualty | `RESIDENT` |
| Commercial Property & Casualty | `COMMERCE` |
| Professional Liability | `PROFLIAB` |
| Miscellaneous | `MISC    ` |
| Other | `OTHER   ` |

**`ddlReasonForNotice`** (7 values, not used in v1): Cancellation, Non-renewal, Claim Denial, Claim Delay, Unsatisfactory Settlement Offer, Unfair Trade Practice, Other.

**`ddlStatute`** (70 values, not used in v1): primarily § 624.155(1)(b)(1), § 624.155(1)(b)(2), § 624.155(1)(b)(3), and § 626.9541 unfair-trade-practice subsections.

## What was attempted but not used

- **`Export Results` button**: returned a complete CSV (Content-Type `application/vnd.ms-excel`, 30 fields including statute and policy language) on a single test of a 5-record search, but failed to trigger on subsequent attempts of the same shape — returned the search-results HTML instead. Cause unclear; possibly session-bound state. Not relied on in v1. Worth re-testing if a future iteration wants per-filing data without scraping.
- **Pagination through result list**: feasible (each page of 100 list rows includes File#, Date, Complainant, Insured, Insurer with stable `ViewFiling.aspx?fid=N` links) but adds enough request volume that a full 2014–2025 list-scrape would take an hour-plus. Not done in v1.
- **Per-filing detail-page scrape**: ~600K filings × 1 request each = ~14 days at 2-second pacing. Out of scope; deferred to PRR.

## First-run snapshot — 2026-05-04

| Field | Value |
|---|---|
| Crawl started | 2026-05-04T18:55-ish (see run_log.txt) |
| Year range | 2003 – 2026 |
| Lines | 9 (per `ddlInsuranceType`) |
| Total HTTP requests | 240 (24 years × 9 lines + 24 no-filter "ALL" totals) |
| Polite sleep | 2.0 s between requests |
| Retries triggered | 0 |
| Hard failures | 0 |

## Output files

After a successful run, `output/` contains:

| File | Rows | What |
|---|---:|---|
| `fl_crn_yearly_total.parquet` | 24 | `(year, count)` totals from no-filter searches |
| `fl_crn_yearly_counts.parquet` | 216 | `(year, type_of_insurance, count)` for 9 lines × 24 years |
| `run_log.txt` | (append-only) | Per-run timestamps and per-cell counts |

## Run history

### 2026-05-04 (first run)

- 240 requests over ~9 minutes, 0 retries, 0 hard failures.
- Pre-2014: all years return 0 (digital archive doesn't reach earlier).
- 2014: first non-zero year (16,249).
- Peak: 2021 with 69,203 (pre-Ian, AOB litigation era apex).
- 2022: dropped to 60,525 (Ian hit Sep 2022, AOB SB 2A reform same year).
- Sum-of-lines vs no-filter total: matched exactly for every year except 2020 (delta = -1; one row with a null `type_of_insurance` field).
- Auto consistently 60–75% of yearly total; Residential P&C 20–30%; everything else combined under 3%.

Append future runs below this line.
