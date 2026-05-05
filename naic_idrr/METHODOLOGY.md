# Methodology

How the NAIC IDRR consumer-complaint counts relate to the other state-level datasets in this repo, and how the parser reads the source PDFs.

## What NAIC publishes about consumer complaints

NAIC has multiple complaint-data products with overlapping names. They differ in *what* they count and *how publicly accessible* the underlying data is:

| Product | What it counts | Granularity | Public bulk access? |
|---|---|---|---|
| **IDRR Vol 1, Table "Consumer Complaints/Inquiries"** | Total consumer complaints + inquiries *received* by each state insurance department in calendar year *N* | State × year | ✅ PDF download (this dataset) |
| **CIS — by Reason** ([cis_agg_reason.htm](https://content.naic.org/cis_agg_reason.htm)) | Closed *confirmed* complaints, broken down by reason of complaint | National + per-state, last 3 years, by line | ❌ Tableau dashboard, no API |
| **CIS — by Disposition** ([cis_agg_disposition.htm](https://content.naic.org/cis_agg_disposition.htm)) | Closed confirmed complaints, broken down by how the complaint was resolved | Same | Same |
| **CIS — by Coverage Type** ([cis_agg_type.htm](https://content.naic.org/cis_agg_type.htm)) | Closed confirmed complaints, broken down by line of insurance | Same | Same |
| **CIS Refined Search** | Per-company "complaint index" (company complaint share ÷ company premium share) | Per-company | ❌ Lookup-only |
| **MCAS** | Claims/underwriting practices, not complaints | Per-company per-line | ✅ XLSX export |

The IDRR is the only NAIC source with **multi-year time depth** (1986–present in principle, 1998–2022 in our cleaned output) at state granularity. CIS is richer in breakdowns but capped at last 3 years and gated behind a Tableau session-bootstrap protocol that v1 does not implement.

## What "complaints" means here vs in the per-state datasets

NAIC IDRR complaints are *received counts*. They include everything that came in the door: a consumer calling the regulator about a delayed claim, a written complaint about a policy cancellation, a referral from a legislator, etc. Neither the consumer's claim nor the insurer's response have been adjudicated. Compare to:

| Dataset | Outcome metric | "In favor of insured" semantic |
|---|---|---|
| TX TDI ([tx_tdi/](../tx_tdi/)) | `confirmed_rate` | TDI agreed the insurer made a mistake |
| NY DFS ([ny_dfs/](../ny_dfs/)) | `upheld_complaints` | DFS agreed with the consumer (auto only); two-year-rolling ratio |
| CA CDI ([ca_cdi/](../ca_cdi/)) | `Justified Complaint` | CDI's per-line, per-company finding against the insurer |
| WA OIC ([wa_oic/](../wa_oic/)) | `total_complaints` | All complaints processed — comparable to NAIC IDRR's metric |
| **NAIC IDRR (this)** | `complaints` | Consumer complaints *received* — workload metric, no outcome adjudication |

So **NAIC IDRR complaints are the broadest possible count.** A state's "TDI confirmed rate × IDRR complaints received" should approximate "complaints the regulator agreed with"; in practice the count taxonomies vary and that calculation is informational only.

## Inquiries

NAIC distinguishes complaints from "inquiries" — a consumer calling to ask "what is replacement-cost coverage?" or "what's the deadline to file?" Inquiries are pre-complaint research questions, not bad-behavior signals. They're shipped in the dataset because (a) the IDRR table publishes them, and (b) they're useful workload context — but they should generally be **excluded** from any "insurer behavior" comparison plot.

The viewer's default metric is `complaints`; switch to `inquiries` only when the question is about regulator workload.

## Parsing strategy

The IDRR is a PDF report. The parser implementation is in [`scripts/02_parse.py`](scripts/02_parse.py). High-level approach:

1. **Locate the table page.** Each year's PDF has one page titled "Consumer Complaints/Inquiries - YYYY". The parser scans pages, requiring both the title regex AND ≥30 jurisdiction-named rows on the same page (so a table-of-contents reference doesn't false-positive).
2. **Extract the data year from the title.** This is the calendar year the data is *about* (NAIC publishes in year *N+1* with year *N*'s data). Used as the canonical year; the file's archive label is publication year and is ignored.
3. **For each text line beginning with a known jurisdiction name**, take the **last two integer-valued tokens** (after stripping a trailing Yes/No "Available to Public?") as `(complaints, inquiries)`. This handles both layout eras:
   - **2005–2022 (4-column):** `State <complaints> <inquiries> <Yes|No>`
   - **1998–2004 (7-column):** `State <Yes|No> <sites> <mobile_sites> <complaints> <inquiries> <Yes|No>` — sites/mobile-sites are integers BEFORE complaints/inquiries; the "last two" rule still works.
4. **Tolerance gate.** Each year's parsed sum is compared to the printed "Total" row from the same page. If the gap exceeds 5%, OR if fewer than 45 jurisdiction rows extract, the entire year is dropped from the output with a logged warning. This guards against the silent-loss failure mode that PDF parsers are notorious for.

Years rejected by the gate or skipped with a "no parseable table" warning: 1986–1997 (scanned bitmaps; poor OCR), 2003 (multi-column layout interleaves the table with another).

## Updating cadence

NAIC publishes a new IDRR Vol 1 each year, typically 6–9 months after the data year ends (so the 2022 data was published mid-2023). To pull a new year:

1. Re-run `python3 naic_idrr/scripts/01_download.py` — this re-fetches `publication-sta-bb-volume-one.pdf` from NAIC's canonical URL, which is overwritten each release. Hashes change; the manifest will reflect the new file.
2. Re-run `python3 naic_idrr/scripts/02_parse.py` — the new data year will appear in the output if the parser successfully extracts it.

If NAIC changes the table layout in a way that breaks the parser, the tolerance gate will reject the year and log it; investigate and add a parser-version branch.

## CIS Tableau v2 hint

If a future contributor wants to extract the CIS dashboard tables: the entry point is the page-scrape of the embed URL, then a POST to `https://tableau.naic.org/vizql/w/<workbook>/v/<view>/bootstrapSession/sessions/<session_id>` with a form-encoded body. The response is a length-prefixed concatenated JSON sequence; the data lives in the `vqlCmdResponse → cmdResultList → presModel → workbookPresModel → dashboardPresModel` tree, with column values referenced by integer pointers into a separate `dataDictionary` block. The Python library `tableauscraper` automates this end-to-end and is the recommended starting point. The three target views are recorded in [`PROVENANCE.md`](PROVENANCE.md#cis-tableau-dashboards-snapshots-only--data-not-extracted).
