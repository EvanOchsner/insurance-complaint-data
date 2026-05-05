# Provenance — Virginia SCC Bureau of Insurance

## Source

- **Publisher:** Virginia State Corporation Commission, Bureau of Insurance.
- **Annual reports landing:** <https://www.scc.virginia.gov/about-the-scc/annual-reports/>
- **URL template:** `https://www.scc.virginia.gov/media/sccvirginiagov-home/about-the-scc/annual-reports/{YYYY}BOI.pdf`
- **Statutory basis:** SCC reports to the Virginia General Assembly under §12.1-19 (umbrella) and the BOI sub-report under §38.2-1318.

## First build (2026-05-04)

| Field | Value |
|---|---|
| `discovered_at` | 2026-05-05T02:41:25Z |
| Files downloaded | 4 (FY 2022, 2023, 2024, 2025) |
| Format | PDF, 2 pages each |
| Polite delay | 1 request / second |
| User-Agent | `insurance-complaint-rates/1.0 (research; contact: evan.ochsner@gmail.com)` |

Per-file SHA256 (first build):

```
FY2022.pdf   80,056 bytes  sha256=2fa5a745decf…
FY2023.pdf  195,629 bytes  sha256=0eb0372eb903…
FY2024.pdf  160,103 bytes  sha256=839181635ad4…
FY2025.pdf  161,249 bytes  sha256=3b7c98e03b0e…
```

## File schema (per row, after parse)

### `va_complaints_yearly.parquet`
| Field | Type | Notes |
|---|---|---|
| `fiscal_year` | i32 | FY-end year |
| `line` | str | `property_and_casualty` or `life_and_health` |
| `complaints_received` | i64 | Workload count |
| `source_file` | str | Source PDF filename |

### `va_external_review_yearly.parquet`
| Field | Type | Notes |
|---|---|---|
| `fiscal_year` | i32 | |
| `total_reviewed` | i64 | All ER requests reviewed |
| `eligible` | i64 | Eligible for ER review (the merits-pool) |
| `ineligible` | i64 | Ineligible (filtered out) |
| `upheld` | i64 | Carrier denial upheld by reviewer |
| `overturned` | i64 | Carrier denial overturned |
| `modified` | i64 | Modified or partially overturned |
| `reversed_self` | i64 | Carrier reversed before review completed |
| `terminated` | i64 | Withdrawn / terminated mid-review |
| `against_insurer` | i64 | Canonical = `overturned + reversed_self` |
| `for_insurer` | i64 | Canonical = `upheld` |
| `mixed` | i64 | Canonical = `modified` |
| `no_decision` | i64 | Canonical = `ineligible + terminated` |
| `on_merits` | i64 | `against_insurer + for_insurer + mixed` |
| `against_rate_of_decided` | f64 | `against_insurer / on_merits` |
| `source_file` | str | |

## OCR quirk

The FY 2023 report renders "Health Carrier Reversed Itself I" — the "1" was OCR-misread as a capital "I". The parser normalizes letter-for-digit misreads inline.

## Run log

The parser appends to `output/run_log.txt`. Sample first run:

```
=== run started 2026-05-05T02:42:56+00:00 ===
  FY2022: P&C=2,322 L&H=1,347 ER reviewed=524 (against=83, for=75, mixed=0, no_dec=366)
  FY2023: P&C=2,779 L&H=1,347 ER reviewed=585 (against=106, for=84, mixed=1, no_dec=394)
  FY2024: P&C=3,230 L&H=1,809 ER reviewed=543 (against=114, for=110, mixed=3, no_dec=326)
  FY2025: P&C=3,342 L&H=1,898 ER reviewed=459 (against=114, for=80, mixed=2, no_dec=263)
  WARNING FY2024: sum(dispositions)=228 vs eligible=218 (delta=10)
Wrote va_complaints_yearly.parquet (8 rows)
Wrote va_external_review_yearly.parquet (4 rows)
Lifetime ER aggregate: 417/772 = 54.02% against-insurer (of decided)
=== run completed 2026-05-05T02:43:03+00:00 ===
```
