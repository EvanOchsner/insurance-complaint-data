# Washington OIC: complaints + IFCA notices

Two streams from the Washington Office of the Insurance Commissioner:

1. **IFCA notices** (per-record, 2025-2026 only) — every plaintiff filing a 20-day pre-suit notice under Washington's Insurance Fair Conduct Act files with the OIC. The OIC publishes an annual log as a PDF. **Plaintiff-side allegations** — same conceptual category as FL CRN, *not* the same as TX/CA/MD/NY regulator findings.
2. **OIC consumer complaints** (annual scalars, 2020-2024) — the regulator's own count of "consumer complaints processed" per year, plus dollars recovered. Comparable to TX/CA/NY regulator-side metrics, though without the per-line or per-finding breakdown the others provide.

The headline framing: WA is the only state besides FL where we can see both pre-litigation pressure (IFCA) and regulator workload (AR) side-by-side. The cross-state visualization should keep IFCA on its own panel (with FL CRN), and put AR alongside TX/CA/NY.

## What's in this folder

| Path | What it is |
|---|---|
| `output/wa_ifca_notices.parquet` (and `.csv`) | One row per IFCA notice — 1,941 rows. All 10 source columns + derived `data_year`, `line_normalized`, `date_received_dt`. |
| `output/wa_ifca_notices_yearly.parquet` (and `.csv`) | Per-`(year, line)` totals + per-year `ALL` row. 26 rows. |
| `output/wa_complaints_state_yearly.parquet` (and `.csv`) | One row per AR year (2020-2024). `total_complaints, recoveries_millions`. |
| `output/run_log.txt` | Appended each run. |
| `scripts/01_download.py` | Pulls 2 IFCA + 5 AR PDFs into `interim/`. |
| `scripts/02_parse.py` | Extracts tables + scalars; writes outputs. |
| `interim/` | Raw PDFs + manifest. **Gitignored.** |
| `METHODOLOGY.md` | What IFCA measures vs what an AR complaint count measures; what's missing. |
| `PROVENANCE.md` | URLs, hashes, fetch times, run history. |

## How to load

```python
import polars as pl

# IFCA per-notice:
ifca = pl.read_parquet("wa_oic/output/wa_ifca_notices.parquet")
ifca.filter(pl.col("data_year") == 2025).select(
    "ifca_number", "date_received", "insurance_company", "complainant_attorney",
    "line_normalized", "rcw_wac_cited"
).head(20)

# IFCA yearly trend by line:
yr = pl.read_parquet("wa_oic/output/wa_ifca_notices_yearly.parquet")
yr.filter(pl.col("line").is_in(["Auto", "UIM", "Homeowners", "Property"])).sort(["year","line"])

# Regulator complaint volume:
ar = pl.read_parquet("wa_oic/output/wa_complaints_state_yearly.parquet")
ar.sort("year")
```

## How to re-run

```
python3 wa_oic/scripts/01_download.py    # ~10 sec, ~6.5 MB
python3 wa_oic/scripts/02_parse.py       # ~30 sec
```

## Headline caveats

1. **IFCA notices are plaintiff allegations, not regulator findings.** Same caveat as FL CRN — measures litigation pressure, not insurer wrongdoing. Document this every time you cite the data.
2. **IFCA coverage is 2025-2026 only.** The OIC removes older PDFs; only the most recent 2 years are online. 2008-2024 IFCA notices would require Wayback Machine retrieval or a public records request to OIC.
3. **2026 is partial.** The PDF was last updated in April 2026; only ~4 months of 2026 notices are included.
4. **Annual Reports don't print a per-line complaint breakdown.** Only a single narrative number per year. The five-year sequence is `(year, total_complaints, recoveries_millions)`.
5. **IFCA excludes health insurance.** The IFCA statute explicitly does not cover health insurance, so the IFCA dataset is implicitly P&C/Auto/Liability. Health complaints appear in the OIC AR aggregate but not in IFCA. Don't conflate.
6. **No per-company complaint history** in v1. The OIC's agent/company lookup tool would provide this; deferred.
7. **OIC complaint counts are a subset of all complaints** — many policyholders complain only to the insurer, never to the regulator.

## Headline numbers

From the 2026-05-04 build:

**IFCA notices by line of insurance, 2025 (n = 1,439):**

| Line | Count | Share |
|---|---:|---:|
| Property | 272 | 18.9% |
| Homeowners | 263 | 18.3% |
| Auto | 235 | 16.3% |
| UIM | 215 | 14.9% |
| Other | 174 | 12.1% |
| Liability | 113 | 7.9% |
| PIP | 49 | 3.4% |
| Unknown | 45 | 3.1% |
| UM | 32 | 2.2% |
| Health | 19 | 1.3% |
| Title | 13 | 0.9% |
| Life | 9 | 0.6% |

P&C lines (Property + Homeowners + Liability + Title) = 661 = 46%. Auto-related (Auto + UIM + UM + PIP) = 531 = 37%.

**OIC consumer complaints (state totals, all lines):**

| Year | Complaints | Recoveries ($M) |
|---:|---:|---:|
| 2020 | 6,678 | 45.4 |
| 2021 | 7,705 | 15.7 |
| 2022 | 8,603 | 26.9 |
| 2023 | 9,441 | 27.4 |
| 2024 | **10,127** | 27.4 |

A steady rise — 52% increase in complaint volume over 5 years, while recoveries have been roughly flat (volatile in 2020-2021 due to anomaly years).

**Sequence completeness check:** every IFCA # from 0001 through 1439 in 2025 and 0001 through 0502 in 2026 is present in the parsed data. No gaps.
