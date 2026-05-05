# Provenance

This file records exactly where the data and reference materials came from, when they were fetched, and what they hash to. The contents of `output/` should be reproducible bit-for-bit (subject to FJC IDB updates between runs) by re-running the two scripts.

## Primary data source

| Field | Value |
|---|---|
| Source | Federal Judicial Center, Integrated Database (IDB), Civil Cases Since 1988 |
| Landing page | <https://www.fjc.gov/research/idb/interactive/IDB-civil-since-1988> |
| Direct download URL | <https://www.fjc.gov/sites/default/files/idb/textfiles/cv88on.zip> |
| URL verified | 2026-05-04 |
| Verified by | HEAD request returned `200 OK`, `Content-Type: application/zip`, `Content-Length: 323874710` |
| Server `Last-Modified` | Thu, 19 Feb 2026 23:47:55 GMT |
| Server `ETag` | `"134def96-64b35ef05c965"` |
| Fetched at | 2026-05-04T16:38:49+00:00 |
| Local zip path | `interim/cv88on.zip` |
| Zip size | 323,874,710 bytes |
| **Zip SHA-256** | `e13c3f473a5da6ed0a18ed4e0626447a29e6efb947cf5af66093e6a014951b56` |
| Zip contents | `cv88on.txt` (single tab-delimited ASCII file, CRLF line endings, 46 columns, 10,760,871 rows incl. header) |
| User-Agent sent | `insurance-complaint-rates/1.0 (research; contact: evan.ochsner@gmail.com)` |

The authoritative manifest is `interim/manifest.json` — the table above is a human-readable copy.

## Reference materials (committed under `reference/`)

| File | Source URL | SHA-256 |
|---|---|---|
| `IDB-Research-Guide.pdf` | <https://www.fjc.gov/sites/default/files/IDB-Research-Guide.pdf> | `b07e7199917feb338c403910b452984528ca911aae55ebcb0c14c5bb95ffdb50` |
| `nos_code_descriptions_js044.pdf` | <https://www.uscourts.gov/sites/default/files/js_044_code_descriptions.pdf> | `aeaff2476c8cc926191466ff571e91b0f0896858f4f00deed1117c1aa33daa95` |
| `office-codes.xlsx` | <https://free.law/xlsx/fjc/integrated-database/office-codes.xlsx> | `83a0e0f6e0b87236559aedf19b3bae3868b66cfa8304d31610e610d30eaeb6f6` |
| `cv88on-field-lengths.xlsx` | <https://free.law/xlsx/fjc/integrated-database/cv88on-field-lengths.xlsx> | `b906356b43b1cb984210a49579f539f5284e640c8ad3aeabf5fc8e21ed05e7b1` |

All four fetched 2026-05-04 with the same User-Agent string.

## Codebook gap (recorded for future re-runs)

The FJC civil-IDB codebook PDF was **not obtainable** at a guessable URL on 2026-05-04. The FJC research/idb pages link to "associated codebooks" but the rendered HTML doesn't expose direct codebook URLs (the page is JS-driven), and probing common path patterns (`/sites/default/files/idb/codebooks/...` with several name variants) returned 404. The codebook is reportedly distributed on the IDB landing page after a click-through; resolving it likely requires a real browser session.

This affects the dataset only at the margin:
- Field structure was recovered from the data file's own header line (46 named columns).
- NoS code 110 = "Insurance" is documented in the AOUSC `js_044_code_descriptions.pdf` (committed in `reference/`).
- District-to-state mapping was derived from `office-codes.xlsx` (committed in `reference/`) cross-checked with the office cities in each district code.
- ORIGIN code labels for codes 1–6 are stable across all FJC documentation. Codes 7–13 are rare (combined < 1% of NoS=110 rows) and labeled conservatively in `02_extract_and_aggregate.py` pending codebook verification.

A future run that does retrieve the codebook should:
1. Save it to `reference/cv88on_codebook.pdf` with a fetched-at note added below.
2. Verify the ORIGIN code labels for 7-13 in `02_extract_and_aggregate.py` and update.
3. Verify there have been no NoS=110 reclassifications since 1988.

## Output files (produced by the two scripts)

After a successful run, `output/` contains:

| File | What |
|---|---|
| `insurance_filings_by_state_year.parquet` (and `.csv`) | Headline `(state, year, count)` table |
| `insurance_filings_by_state_year_origin.parquet` (and `.csv`) | Same with `origin_code, origin_label` breakout |
| `run_log.txt` | Append-only log: timestamps, row counts, sanity tables |

## Run history

### 2026-05-04T16:43:42Z

- Source zip sha256: `e13c3f473a5da6ed0a18ed4e0626447a29e6efb947cf5af66093e6a014951b56`
- Total `cv88on.txt` rows: 10,760,871 (incl. header)
- NoS=110 rows: 384,432
- After dropping pre-1988 filings: 372,547
- After dropping null `FILEDATE`: 372,547 (no nulls observed)
- District-mapping coverage: 94/94 codes mapped
- `(state, year)` rows written: 2,051
- `(state, year, origin)` rows written: 7,601
- Years covered: 1988–2025 (2025 partial; max `FILEDATE` = 2025-12-31)
- Top 5 states by total NoS=110 since 1988: `LA` 46,082 · `TX` 41,896 · `CA` 32,984 · `FL` 30,051 · `PA` 22,033
- Removal share (origin=2 / total) trend: ~0.38 in 1988 → ~0.58 in 2025

Append future runs below this line.
