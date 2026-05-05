# Provenance — Maryland MIA §27-1001 bad-faith complaints

## Source

- **Publisher:** Maryland Insurance Administration (MIA), Consumer Complaints / Appeals & Grievances unit.
- **Statutory authority:** Md. Insurance Article §27-1001(h) — annual report to the General Assembly.
- **Index of reports:** <https://insurance.maryland.gov/Consumer/Pages/Property-and-Casualty-Reports.aspx>

The 18 source PDFs (FY 2008 – FY 2025) were supplied with the curated dataset and live in [`source_reports/`](source_reports/). Each is referenced by URL in [`SUPPLIED_README.md`](SUPPLIED_README.md). Per-file SHA256 (first build, 2026-05-04):

```
FY2008.pdf      99522 bytes  sha256=4ad67f214d12476e…
FY2009.pdf     514359 bytes  sha256=dc1f8cb95eb6c123…
FY2010.pdf     452331 bytes  sha256=f4ea5503f0ccfdf1…
FY2011.pdf     368800 bytes  sha256=d0581c9a662a645f…
FY2012.pdf     449690 bytes  sha256=33e6c35c984dff54…
FY2013.pdf     359231 bytes  sha256=9ee1219bc67e58e2…
FY2014.pdf     108382 bytes  sha256=b1bbc1d1f8c07fa1…
FY2015.pdf     309659 bytes  sha256=67c256cf1e523a3b…
FY2016.pdf     180172 bytes  sha256=3dbe343398c72a1f…
FY2017.pdf     303762 bytes  sha256=381c1a365fb84967…
FY2018.pdf     304181 bytes  sha256=ddae8a7e49d29eee…
FY2019.pdf     433127 bytes  sha256=80f828063cf71c70…
FY2020.pdf     465266 bytes  sha256=a34db55390ca1007…
FY2021.pdf     298260 bytes  sha256=715ca6fdfe111fc5…
FY2022.pdf     353962 bytes  sha256=fdcece632d9cf944…
FY2023.pdf     615945 bytes  sha256=3d4e208615001fe2…
FY2024.pdf     505898 bytes  sha256=470594213a153158…
FY2025.pdf     541891 bytes  sha256=81d186ba1f99b4a9…
```

## How the data was produced

The figures were hand-extracted from each MIA annual report's headline disposition table by the curator. The extraction methodology, source-of-truth choices, and reconciliations are documented in [`SUPPLIED_README.md`](SUPPLIED_README.md). This pipeline does **not** re-extract from PDFs; the [`scripts/build.py`](scripts/build.py) inline data table is the canonical source of truth.

Cross-checks and reconciliations recorded in the `source` column of [`data.csv`](data.csv) and the parquet output:

- FY 2008: partial year (statute effective Oct 1, 2007).
- FY 2011: retrospectively revised in FY 2013 report (8/2/16 → 7/1/18).
- FY 2022: introduces the "breach to pay only" sub-row.
- FY 2025: settled bucket reconciled (27 → 22) to match report's headline total.

## File schema (per row, after build)

| Field | Type | Notes |
|---|---|---|
| `fy` | i32 | Fiscal year ending June 30 |
| `total` | i64 | Total complaints filed |
| `settled_wd_dismissed` | i64 | Settled / withdrawn / dismissed (no merits decision) |
| `bad_faith` | i64 | Absence-of-good-faith finding (regulator against insurer) |
| `no_violation` | i64 | No violation (regulator for insurer) |
| `breach_pay_only` | i64 | Breach to pay only (mixed; partial finding for insured) |
| `on_merits` | i64 | `bad_faith + no_violation + breach_pay_only` |
| `pct_insured_wins` | f64 | `bad_faith / on_merits * 100` |
| `pct_any_insured_finding` | f64 | `(bad_faith + breach_pay_only) / on_merits * 100` |
| `source` | str | Authoritative source (e.g. "FY2013 report Table 1 (retrospective)") |

## Run log

The build script is one-shot; no `run_log.txt`. Re-run by:

```
python3 md_mia/scripts/build.py
```

Output is deterministic given the inline data table.
