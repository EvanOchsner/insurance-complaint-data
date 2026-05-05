# Provenance — Connecticut CID consumer complaints

## Source

- **Dataset name:** *Insurance Company Complaints, Resolutions, Status, and Recoveries*
- **Catalog landing:** <https://data.ct.gov/widgets/t64r-mt64>
- **Resource API:** `https://data.ct.gov/resource/t64r-mt64.json`
- **Metadata API:** `https://data.ct.gov/api/views/t64r-mt64.json`
- **Publisher:** Connecticut Insurance Department (CID), via `data.ct.gov` (Socrata).
- **Cross-validation source (PDF reports):** <https://portal.ct.gov/cid/department-resources/cid-reports>

## First build (2026-05-04)

| Field | Value |
|---|---|
| `pulled_at` | 2026-05-04T23:31:28Z |
| `rowsUpdatedAt` (server) | 2026-05-02T10:30:29Z (epoch 1777717829) |
| Rows pulled | 77,461 |
| Page size | 50,000 |
| HTTP requests | 2 (anonymous) |
| Interim parquet sha256 | `01026c6bd9a364fdf60c05e1cb8fa29e0ef62002e028a6b8449f9c135287179b` |
| User-Agent | `insurance-complaint-rates/1.0 (research; contact: evan.ochsner@gmail.com)` |

## Schema as observed

Per the Socrata metadata, the dataset has 12 columns. Column names below are the API field names; types are Socrata-side dataTypeNames.

| Field | Type | Notes |
|---|---|---|
| `company` | text | Insurer name as filed |
| `file_no` | number | Complaint file number (unique) |
| `opened` | calendar_date | Date complaint opened |
| `closed` | calendar_date | Date complaint closed (null if still open) |
| `coverage` | text | Line of business (e.g. `A & H`, `Individual Private Passenger`, `Homeowners`) |
| `subcoverage` | text | Line of business sub-classification |
| `reason` | text | Nature-of-complaint top-level |
| `subreason` | text | Nature-of-complaint sub-level |
| `disposition` | text | Regulator's resolution (the headline metric) |
| `conclusion` | text | Customer-side outcome label |
| `recovery` | number | Dollar recovery for consumer (USD) |
| `status` | text | Workflow status (`Closed`, `Awaiting Decision`, etc.) |

The pull script forces every column to `pl.String` to avoid Polars schema-inference races on rows that omit optional fields (Socrata serves sparse JSON).

## Run log

The script appends to `output/run_log.txt` on every aggregate run. Sample first run:

```
=== run started 2026-05-04T23:31:32+00:00 ===
Loaded 77,461 raw rows from t64r-mt64.parquet
Filtered to status='Closed': 75,045 of 77,461 rows
Disposition values seen: 14 (all mapped)
file_no is unique across 75,045 closed rows.
Wrote ct_complaints_complaint_level.parquet (75,045 rows)
Wrote ct_complaints_yearly.parquet (924 rows)
Wrote ct_complaints_yearly_confirmed.parquet (234 rows)

Max closed date: 2026-05-01
Year 2026 is partial; treat as preliminary.
=== run completed 2026-05-04T23:31:32+00:00 ===
```
