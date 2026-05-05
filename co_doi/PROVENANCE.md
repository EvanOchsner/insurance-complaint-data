# Provenance — Colorado DOI Annual Complaint and Recoveries Reports

## Source

- **Publisher:** Colorado Division of Insurance (DOI), within the Department of Regulatory Agencies (DORA).
- **Landing:** <https://doi.colorado.gov/for-consumers/consumer-resources/insurance-complaint-reports>

## URLs (filename inconsistency across years)

CO doesn't use a stable filename convention; each PDF is hardcoded in `01_download.py`:

```
FY 2021-22  → FY%202021-22%20Annual%20Complaint%20and%20Inquiry%20Report.pdf
FY 2022-23  → FY%202022-23%20Colorado%20DOI%20Annual%20Complaint%20and%20Recoveries%20Report.pdf
FY 2023-24  → FY%202023-24%20Colorado%20DOI%20Annual%20Complaint%20and%20Recoveries%20Report.pdf
FY 2024-25  → 2025%20Colorado%20Division%20of%20Insurance%20Annual%20Complaint%20and%20Recoveries%20Report.pdf
```

Note the FY 2024-25 file drops the "FY" prefix and the "Colorado DOI" stem becomes "Colorado Division of Insurance."

## CO origin requires browser-style User-Agent

`doi.colorado.gov` returns a CloudFront error ("ERROR: The request could not be satisfied") for unfamiliar User-Agents. The downloader uses a Chrome 120 UA. Same workaround as KS KID. Documented as a known origin behavior; not a workaround for any access-control purpose.

## First build (2026-05-04)

| Field | Value |
|---|---|
| `discovered_at` | 2026-05-05T04:16:55Z |
| Files | 4 PDFs (FY 2022, 2023, 2024, 2025) |
| Polite delay | 1 request / second |
| User-Agent | `Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36` |

Per-file SHA-256:

```
FY2022.pdf   1,022,716 bytes  sha256=ba965094b891…
FY2023.pdf   1,740,928 bytes  sha256=8a0a308e125f…
FY2024.pdf   5,903,153 bytes  sha256=eb9bf13ed93c…
FY2025.pdf  18,761,117 bytes  sha256=68e2ddd7efb6…
```

The FY2025.pdf is unusually large (18MB) due to embedded fonts/images in the FY 2024-25 report's redesigned layout.

## Hand-verified inline values

`02_build.py` contains the canonical data table. Each row's source value is cited inline with a comment naming the source PDF page and the published label. Verifying any row's correctness:

1. Open `co_doi/interim/files/FY{YYYY}.pdf`.
2. Navigate to the cited page (typically page 4 for recoveries, page 5 for workload).
3. Confirm the labeled value matches the inline data.

## File schema (per row, after build)

### `co_workload_yearly.parquet`
| Field | Type | Notes |
|---|---|---|
| `fiscal_year` | i32 | FY-end year |
| `line` | str | Canonical line slug (see METHODOLOGY) |
| `count` | i64 | The published count |
| `count_type` | str | `received` / `closed` / `received_with_inquiries` |
| `source_file` | str | Source PDF filename (e.g. `FY2024.pdf`) |

### `co_recoveries_yearly.parquet`
| Field | Type | Notes |
|---|---|---|
| `fiscal_year` | i32 | FY-end year |
| `line` | str | Canonical line slug |
| `amount_usd` | i64 | Money recovered in USD |
| `source_file` | str | Source PDF filename |

## No run log

The build script is fully deterministic from the inline data; no per-run logging is needed. If a future year is added or values change, the parquet hashes will shift and re-running `02_build.py` re-emits.
