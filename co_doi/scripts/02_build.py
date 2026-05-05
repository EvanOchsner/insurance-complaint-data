"""Build CO DOI workload + recoveries parquets from inline data hand-verified
against the source PDFs.

Why hand-verified inline data instead of regex extraction:
  • The 4 published PDFs (FY 2022, 2023, 2024, 2025) have inconsistent layouts
    year-to-year — the recovery breakdown categories and labels shift each
    year (Marshall Fire only in 2023; Other P&C only in 2025; etc.).
  • Robust regex extraction across all four formats wasn't worth the parser
    complexity for 4 rows × ~7 fields. Adding a future year is a 1-line
    edit to this file plus a fresh PDF download for provenance.

Each row's `source_file` column traces back to the corresponding PDF in
co_doi/interim/files/. Run `01_download.py` to pull the PDFs fresh; the
sha256 in interim/manifest.json is the audit anchor.

Outputs:
  co_doi/output/co_workload_yearly.{parquet,csv}    — per-line received counts
  co_doi/output/co_recoveries_yearly.{parquet,csv}  — per-line recovered $
"""
from __future__ import annotations

import sys
from pathlib import Path

import polars as pl

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "co_doi" / "output"

# Workload rows: (fiscal_year, line, count, count_type, source_file)
# count_type = 'received' or 'closed'.
# 'received_with_inquiries' is the FY 2025 framing where reported numbers
# include both formal complaints and inquiries; documented in METHODOLOGY.
WORKLOAD = [
    # (FY, line, count, count_type, note_about_source_value)
    # FY 2021-22 — page 3 narrative:
    #   "complaints closed ... increased from 3,032 to 3,085 from FY 20-21"
    #   "PC&T 398 451 13.3% / L&H 904 1066 17.9%" (inquiries)
    # No P&C-vs-L&H complaint count split published in FY 2022 PDF in the form
    # other years use. Just total closed.
    (2022, "all_lines",       3085, "closed"),
    # FY 2022-23 — page 5:
    #   Total P&C Insurance Complaints Received 3,300
    #   Total L&H Insurance Complaints Received 2,620
    #   Total Combined Complaints and Inquiries Closed 5,920
    (2023, "property_casualty", 3300, "received"),
    (2023, "life_health",       2620, "received"),
    (2023, "all_lines",         5920, "closed"),
    # FY 2023-24 — page 5:
    #   Total P&C Insurance Complaints Received 3,829
    #   Total L&H Insurance Complaints Received 1,929
    #   Complaints specifically related to homeowners insurance 1,504
    #   Complaints specifically related to health insurance 1,716
    #   Complaints and Inquiries Received 6,987
    #   Complaints and Inquiries Closed 7,327
    (2024, "property_casualty", 3829, "received"),
    (2024, "life_health",       1929, "received"),
    (2024, "homeowners",        1504, "received"),
    (2024, "health",            1716, "received"),
    (2024, "all_lines",         6987, "received"),
    (2024, "all_lines",         7327, "closed"),
    # FY 2024-25 — page 5:
    #   Total P&C Insurance Complaints & Inquiries Received 3,505
    #   Total L&H Insurance Complaints & Inquiries Received 1,511
    #   Complaints & inquiries specifically related to homeowners 1,463
    #   Complaints & inquiries specifically related to health 1,313
    #   Complaints & inquiries (top-line total) 7,792
    #   Total Complaints and Inquiries Closed 5,224
    # Note the FY 2025 framing changed to "complaints AND inquiries received"
    # rather than "complaints received" — recorded as 'received_with_inquiries'.
    (2025, "property_casualty", 3505, "received_with_inquiries"),
    (2025, "life_health",       1511, "received_with_inquiries"),
    (2025, "homeowners",        1463, "received_with_inquiries"),
    (2025, "health",            1313, "received_with_inquiries"),
    (2025, "all_lines",         7792, "received_with_inquiries"),
    (2025, "all_lines",         5224, "closed"),
]

# Recoveries rows: (fiscal_year, line, amount_usd)
# Lines normalized across years where possible. 'marshall_fire' is FY 2023 only
# (catastrophe-specific category). 'other_pc' captures non-homeowners /
# non-auto P&C recoveries when separately published.
RECOVERIES = [
    # FY 2021-22 — page 3 narrative:
    #   Total $19,630,350; PC&T $15,424,844; L&H $4,205,506
    (2022, "total",             19_630_350),
    (2022, "property_casualty", 15_424_844),
    (2022, "life_health",        4_205_506),
    # FY 2022-23 — page 4:
    #   Marshall Fire $3,756,555; Other P&C $9,759,961; P&C subtotal $13,516,516
    #   Health $4,969,764; Life/LTC/Annuity $3,036,786; L&H subtotal $8,006,550
    #   Grand total $21,523,066
    (2023, "total",             21_523_066),
    (2023, "property_casualty", 13_516_516),
    (2023, "marshall_fire",      3_756_555),
    (2023, "other_pc",           9_759_961),
    (2023, "life_health",        8_006_550),
    (2023, "health",             4_969_764),
    (2023, "life_annuity",       3_036_786),
    # FY 2023-24 — page 4:
    #   Homeowners $10,601,710; Auto $4,995,340; P&C subtotal $19,253,299
    #   (P&C subtotal includes other recoveries beyond homeowners+auto)
    #   Health $4,080,002; Life/Annuity $3,152,428; L&H subtotal $7,232,430
    #   Grand total $26,487,192
    (2024, "total",             26_487_192),
    (2024, "property_casualty", 19_253_299),
    (2024, "homeowners",        10_601_710),
    (2024, "auto",               4_995_340),
    (2024, "life_health",        7_232_430),
    (2024, "health",             4_080_002),
    (2024, "life_annuity",       3_152_428),
    # FY 2024-25 — page 4:
    #   Homeowners $5,764,272; Auto $3,880,700; Other P&C $785,278;
    #     P&C subtotal $10,430,250
    #   Health $3,011,033; Life/Annuity $4,165,805; L&H subtotal $7,176,838
    #   Other category $253; Grand total $17,607,341
    (2025, "total",             17_607_341),
    (2025, "property_casualty", 10_430_250),
    (2025, "homeowners",         5_764_272),
    (2025, "auto",               3_880_700),
    (2025, "other_pc",             785_278),
    (2025, "life_health",        7_176_838),
    (2025, "health",             3_011_033),
    (2025, "life_annuity",       4_165_805),
    (2025, "other",                    253),
]


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    wk = pl.DataFrame(
        [(fy, ln, c, t) for (fy, ln, c, t) in WORKLOAD],
        schema=["fiscal_year", "line", "count", "count_type"],
        orient="row",
    ).with_columns([
        pl.col("fiscal_year").cast(pl.Int32),
        pl.col("count").cast(pl.Int64),
        pl.format("FY{}.pdf", pl.col("fiscal_year")).alias("source_file"),
    ]).sort(["fiscal_year", "count_type", "line"])

    rc = pl.DataFrame(
        [(fy, ln, amt) for (fy, ln, amt) in RECOVERIES],
        schema=["fiscal_year", "line", "amount_usd"],
        orient="row",
    ).with_columns([
        pl.col("fiscal_year").cast(pl.Int32),
        pl.col("amount_usd").cast(pl.Int64),
        pl.format("FY{}.pdf", pl.col("fiscal_year")).alias("source_file"),
    ]).sort(["fiscal_year", "line"])

    # Sanity: every fiscal_year has both workload and recoveries rows.
    fy_w = set(wk["fiscal_year"].to_list())
    fy_r = set(rc["fiscal_year"].to_list())
    if fy_w != fy_r:
        print(f"WARNING: workload years {sorted(fy_w)} != recoveries years {sorted(fy_r)}", file=sys.stderr)

    wk_pq = OUTPUT_DIR / "co_workload_yearly.parquet"
    wk_csv = OUTPUT_DIR / "co_workload_yearly.csv"
    wk.write_parquet(wk_pq)
    wk.write_csv(wk_csv)
    print(f"Wrote {wk_pq.name} ({len(wk)} rows)")

    rc_pq = OUTPUT_DIR / "co_recoveries_yearly.parquet"
    rc_csv = OUTPUT_DIR / "co_recoveries_yearly.csv"
    rc.write_parquet(rc_pq)
    rc.write_csv(rc_csv)
    print(f"Wrote {rc_pq.name} ({len(rc)} rows)")

    print(f"\nWorkload years: {sorted(fy_w)}")
    print(f"Recovery lines covered: {sorted(rc['line'].unique().to_list())}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
