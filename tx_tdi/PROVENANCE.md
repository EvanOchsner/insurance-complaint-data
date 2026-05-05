# Provenance

Source-of-record details for the TX TDI complaints dataset. Output files in `tx_tdi/output/` are reproducible by re-running the two scripts; differences across runs reflect upstream TDI updates and will be visible in the manifest.

## Primary data source

| Field | Value |
|---|---|
| Source | Texas Department of Insurance, via data.texas.gov (Socrata) |
| Dataset name | Insurance complaints: One record / complaint |
| Dataset 4×4 ID | `jjc8-mxkg` |
| Landing page | <https://data.texas.gov/dataset/Insurance-complaints-One-record-complaint/jjc8-mxkg> |
| Metadata API | <https://data.texas.gov/api/views/jjc8-mxkg.json> |
| Resource API | <https://data.texas.gov/resource/jjc8-mxkg.json> |
| URL verified | 2026-05-04 |
| Authentication | Anonymous (no app token; ~6 paginated requests at 50k page size) |
| User-Agent sent | `insurance-complaint-rates/1.0 (research; contact: evan.ochsner@gmail.com)` |

The authoritative manifest is `interim/manifest.json` — the table below is a human-readable copy.

## First-run snapshot — 2026-05-04T17:55:41Z

| Field | Value |
|---|---|
| Pulled at | 2026-05-04T17:55:41+00:00 |
| Server `rowsUpdatedAt` (epoch) | 1777885277 |
| Server `viewLastModified` (epoch) | 1733413115 |
| Rows pulled | 281,398 |
| Rows expected (live `count(*)`) | 281,398 |
| Page size | 50,000 |
| Pages | 6 |

Schema at fetch time (11 columns):

| Column | Socrata type |
|---|---|
| `complaint_number` | number |
| `complaint_filed_by` | text |
| `received_date` | calendar_date |
| `closed_date` | calendar_date |
| `complaint_type` | text |
| `coverage_type` | text |
| `coverage_level` | text |
| `involved_party_type` | text |
| `complainant_type` | text |
| `finding_type` | text |
| `keywords` | text |

Distinct `finding_type` values observed (live, 2026-05-04):

| Value | Count | Share |
|---|---:|---:|
| `Not Confirmed` | 228,675 | 81.3% |
| `Confirmed` | 52,722 | 18.7% |
| (null) | 1 | <0.001% |

Distinct `coverage_type` values observed:

| Value | Count |
|---:|---:|
| Accident and Health | 114,706 |
| Automobile | 95,708 |
| Homeowners | 40,590 |
| Life & Annuity | 15,228 |
| Miscellaneous | 9,300 |
| Liability | 3,549 |
| Fire, Allied Lines & CMP | 2,275 |
| (null) | 42 |

## Output files

After a successful run, `output/` contains:

| File | What |
|---|---|
| `tx_complaints_complaint_level.parquet` (and `.csv`) | One row per complaint, all 11 fields, parsed dates plus `year_closed` and `is_confirmed`. |
| `tx_complaints_yearly.parquet` (and `.csv`) | `(year_closed, coverage_type, finding_type, count)`. |
| `tx_complaints_yearly_confirmed.parquet` (and `.csv`) | `(year_closed, coverage_type, total, confirmed, not_confirmed, confirmed_rate)`. The `coverage_type = "ALL"` row per year is the headline. |
| `run_log.txt` | Append-only log: timestamps, row counts, sanity tables. |

## Run history

### 2026-05-04T17:56:22Z

- Source rows: 281,398
- Dropped 1 row (null `finding_type`); 0 rows had null `closed_date`.
- After cleaning: 281,397 unique `complaint_number`s.
- `closed_date` range: 2012-05-21 → 2026-05-01.
- `year_closed` partial: 2026 (data through 2026-05-01).
- Output row counts: complaint-level 281,397 · yearly 217 · yearly_confirmed 124.
- Confirmed rate by year (ALL coverages):
  | Year | Total | Confirmed | Rate |
  |---:|---:|---:|---:|
  | 2012 | 7,684 | 1,255 | 16.3% |
  | 2013 | 20,151 | 2,959 | 14.7% |
  | 2014 | 19,453 | 4,314 | 22.2% |
  | 2015 | 20,273 | 3,902 | 19.2% |
  | 2016 | 21,090 | 3,444 | 16.3% |
  | 2017 | 21,655 | 3,868 | 17.9% |
  | 2018 | 21,296 | 3,553 | 16.7% |
  | 2019 | 30,878 | 4,319 | 14.0% |
  | 2020 | 18,998 | 2,999 | 15.8% |
  | 2021 | 15,972 | 2,042 | 12.8% |
  | 2022 | 14,476 | 2,189 | 15.1% |
  | 2023 | 19,256 | 3,469 | 18.0% |
  | 2024 | 17,369 | 4,734 | 27.3% |
  | 2025 | 22,562 | 7,057 | 31.3% |
  | 2026 (partial) | 10,284 | 2,618 | 25.5% |

Append future runs below this line.
