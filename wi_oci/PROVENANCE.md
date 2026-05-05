# Provenance — Wisconsin OCI Insurance Report

## Source

- **Publisher:** Wisconsin Office of the Commissioner of Insurance (OCI), Division of Market Regulation and Enforcement.
- **Landing:** <https://oci.wi.gov/Pages/AboutOCI/WisconsinInsuranceReport.aspx>

## URLs (filename inconsistency across years)

OCI doesn't use a stable filename convention. Each year's URL is hardcoded in `01_download.py`:

```
WIR 2020  → WIR_2020_FINAL_Web.pdf
WIR 2021  → 2021_WisconsinInsuranceReport.pdf
WIR 2022  → 2022_WisconsinInsuranceReport-Web.pdf
WIR 2023  → 2023_WIR_Final_Web.pdf
WIR 2024  → 2024_WIR.pdf
```

Earlier years (2016–2019) use yet other naming patterns, accessible via the archived-reports landing page.

## First build (2026-05-04)

| Field | Value |
|---|---|
| `discovered_at` | 2026-05-05T04:27:45Z |
| Files | 5 PDFs (WIR 2020–2024) |
| Polite delay | 1 request / second |
| User-Agent | `insurance-complaint-rates/1.0 (research; contact: evan.ochsner@gmail.com)` |
| Total bytes | ~82 MB across 5 files |

Per-file SHA-256:

```
WIR_2020.pdf  19,411,381 bytes  sha256=79476a992761…
WIR_2021.pdf   3,100,868 bytes  sha256=306aab03ab41…
WIR_2022.pdf   7,032,636 bytes  sha256=40cc8060e7f6…
WIR_2023.pdf   6,803,054 bytes  sha256=b2fe809323b1…
WIR_2024.pdf  46,073,745 bytes  sha256=1c9b3f213502…
```

The 2024 WIR is unusually large (44 MB) due to embedded fonts/images in the redesigned layout.

## Table II page numbers per report

| Report | Table II page |
|---|---|
| WIR 2020 | p. 53 |
| WIR 2021 | p. 68 |
| WIR 2022 | p. 103 |
| WIR 2023 | p. 95 |
| WIR 2024 | p. 89 |

The parser locates Table II by header regex (tolerant of OCR/layout quirks), not by hardcoded page number.

## File schema

### `wi_complaints_yearly.parquet` (canonical)
| Field | Type | Notes |
|---|---|---|
| `data_year` | i32 | Calendar year of the data |
| `line` | str | Canonical line slug (see METHODOLOGY) |
| `complaints` | i64 | Complaint count from Table II |
| `report_year` | i32 | Year of the WIR that produced this canonical row |
| `source_file` | str | `WIR_{report_year}.pdf` |

### `wi_complaints_all_versions.parquet` (audit)
Same schema. May contain multiple rows per (data_year, line) when OCI revised the value across reports.

## Source quirks

- **2021 PDF Table II layout:** rendered beside Table I (Total Complaint Files history); pdfplumber text extraction interleaves rows. The 2021 report contributes only 7 of 14 lines per year cleanly. The canonical output cross-fills from adjacent reports.
- **2021 PDF header text:** "Table II - Complaints Fil ed By Type of Insurance" (stray space in "Filed"). The locator regex accommodates this.
- **Apostrophe variation:** "Worker's Compensation" rendered with straight or curly apostrophe; both forms in `LINE_NORMALIZE`.

## Run log

The parser appends to `output/run_log.txt`. Sample first run:

```
=== run started 2026-05-05T04:29:03+00:00 ===
  2020: data years inferred as [2019, 2020]
  2020: parsed 28 (data_year × line) rows from Table II
  2021: data years inferred as [2020, 2021]
  2021: parsed 14 (data_year × line) rows from Table II   (← side-by-side layout quirk)
  2022: data years inferred as [2021, 2022]
  2022: parsed 28 (data_year × line) rows from Table II
  2023: data years inferred as [2022, 2023]
  2023: parsed 28 (data_year × line) rows from Table II
  2024: data years inferred as [2023, 2024]
  2024: parsed 28 (data_year × line) rows from Table II
Wrote wi_complaints_yearly.parquet (84 rows; canonical / latest-revision)
Wrote wi_complaints_all_versions.parquet (126 rows; all reports, for audit)
=== run completed 2026-05-05T04:31:34+00:00 ===
```
