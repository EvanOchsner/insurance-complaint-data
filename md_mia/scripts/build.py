"""Build the MD MIA §27-1001 bad-faith dataset (FY 2008–FY 2025) parquet.

The data table below was hand-extracted from the 18 MIA annual reports under
Md. Insurance Article §27-1001(h). The source PDFs are in `md_mia/source_reports/`.
The supplied `md_mia/data.csv` is the same content as a flat CSV; this script is
the canonical builder that emits the per-project parquet output under
`md_mia/output/md_complaints_yearly.{parquet,csv}`.

Sources (each row's authoritative source):
  FY 2008          → FY 2008 report (Table 1; partial year Oct 1 2007 – Jun 30 2008)
  FY 2009 – 2013   → FY 2013 report's Table 1 (covers FY 2009–2013, retrospectively updated)
  FY 2014 – 2018   → FY 2019 report's Table 1
  FY 2019 – 2023   → FY 2023 report's Table 2
  FY 2024          → FY 2024 report's Table 1
  FY 2025          → FY 2025 report's Table 1 (with one reconciliation noted in source col)

See `md_mia/SUPPLIED_README.md` for the full methodology notes (FY 2008 partial
year handling; FY 2011 retrospective revision; FY 2022 introduction of the
"breach to pay only" sub-category; FY 2025 internal arithmetic discrepancy).
"""
from __future__ import annotations

import sys
from pathlib import Path

import polars as pl

PROJECT_ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = PROJECT_ROOT / "md_mia" / "output"

# fmt: off
DATA = [
    # FY,  total, settled, bad_faith, no_violation, breach_pay_only, source
    (2008,  40,     14,        1,           25,            0,        "FY2008 report (partial year, some pending at publication)"),
    (2009,  52,     21,        3,           28,            0,        "FY2013 report Table 1 (retrospective)"),
    (2010,  33,     14,        1,           18,            0,        "FY2013 report Table 1 (retrospective)"),
    (2011,  26,      7,        1,           18,            0,        "FY2013 report Table 1 (retrospective; FY2011 own report had 8/2/16)"),
    (2012,  20,      9,        3,            8,            0,        "FY2013 report Table 1"),
    (2013,  34,     14,        4,           16,            0,        "FY2013 report Table 1"),
    (2014,  26,     10,        3,           13,            0,        "FY2019 report Table 1"),
    (2015,  18,      3,        3,           12,            0,        "FY2019 report Table 1"),
    (2016,  25,     10,        1,           14,            0,        "FY2019 report Table 1"),
    (2017,  28,      6,        1,           21,            0,        "FY2019 report Table 1"),
    (2018,  26,      8,        0,           18,            0,        "FY2019 report Table 1"),
    (2019,  30,      2,        1,           27,            0,        "FY2023 report Table 2"),
    (2020,  28,      9,        1,           18,            0,        "FY2023 report Table 2"),
    (2021,  58,     18,        3,           37,            0,        "FY2023 report Table 2"),
    (2022,  85,     25,        0,           59,            1,        "FY2023 report Table 2"),
    (2023,  87,     11,        0,           76,            0,        "FY2023 report Table 1+2"),
    (2024,  43,     15,        0,           28,            0,        "FY2024 report Table 1"),
    # FY2025 settled adjusted from 27→22 to reconcile to total=52 (see methodology).
    (2025,  52,     22,        2,           28,            0,        "FY2025 report Table 1 (settled adjusted from 27→22 to reconcile to total=52)"),
]
# fmt: on


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    df = pl.DataFrame(
        DATA,
        schema=[
            "fy", "total", "settled_wd_dismissed", "bad_faith",
            "no_violation", "breach_pay_only", "source",
        ],
        orient="row",
    ).with_columns([
        (pl.col("bad_faith") + pl.col("no_violation") + pl.col("breach_pay_only"))
            .alias("on_merits"),
    ]).with_columns([
        (pl.col("bad_faith") / pl.col("on_merits") * 100).alias("pct_insured_wins"),
        ((pl.col("bad_faith") + pl.col("breach_pay_only")) / pl.col("on_merits") * 100)
            .alias("pct_any_insured_finding"),
    ]).with_columns([
        pl.col("fy").cast(pl.Int32).alias("fy"),
    ])

    # Sanity: total == settled + on_merits, every row.
    chk = df.with_columns(
        (pl.col("settled_wd_dismissed") + pl.col("on_merits") - pl.col("total")).alias("delta")
    )
    if not (chk["delta"] == 0).all():
        print("HARD FAILURE: total != settled + on_merits", file=sys.stderr)
        print(chk.filter(pl.col("delta") != 0))
        return 2

    # Sanity: bad_faith + breach_pay_only ≤ on_merits.
    if not (df["bad_faith"] + df["breach_pay_only"] <= df["on_merits"]).all():
        print("HARD FAILURE: bad_faith + breach_pay_only > on_merits", file=sys.stderr)
        return 3

    out_pq = OUTPUT_DIR / "md_complaints_yearly.parquet"
    out_csv = OUTPUT_DIR / "md_complaints_yearly.csv"
    df.write_parquet(out_pq)
    df.write_csv(out_csv)
    print(f"Wrote {out_pq.name} ({len(df)} rows)")
    print(f"Wrote {out_csv.name}")

    bf_total = df["bad_faith"].sum()
    om_total = df["on_merits"].sum()
    bp_total = df["breach_pay_only"].sum()
    print(f"\nLifetime aggregate:")
    print(f"  bad-faith / on-merits          = {bf_total} / {om_total} = {bf_total/om_total*100:.2f}%")
    print(f"  any-insured-finding / on-merits = {bf_total + bp_total} / {om_total} = "
          f"{(bf_total + bp_total)/om_total*100:.2f}%")
    return 0


if __name__ == "__main__":
    sys.exit(main())
