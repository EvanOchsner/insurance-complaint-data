"""Pivot mo_complaints_yearly into a wide format suitable for the unified viewer.

The native parquet (mo_complaints_yearly.parquet) is long-format with
`metric` ∈ {'complaints_total', 'pct_resolved_consumer_relief'} and one row per
(report_year, year, line, metric) so cross-report disagreements are auditable.
The viewer expects ONE row per (year, line) with metrics as columns.

This script:
  1. For each (year, line, metric) cell, picks the most recent report's value
     (because LDI's later reports supersede earlier ones, and overlapping
     values agree exactly except for occasional 1-3-complaint revisions).
  2. Pivots `metric` to columns.
  3. Derives outcome counts from `pct_resolved_consumer_relief`:
        against_insurer ≈ round(complaints_total * pct)
        for_insurer     = complaints_total - against_insurer
     This is a SOFT proxy — DCI's "consumer relief" is a different concept
     than TX's `Confirmed`; see METHODOLOGY.md.
  4. Writes mo_dci/output/mo_complaints_yearly_wide.parquet.

Run after 02_parse.py.
"""
from __future__ import annotations

from pathlib import Path

import polars as pl

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC = PROJECT_ROOT / "mo_dci" / "output" / "mo_complaints_yearly.parquet"
DST_PARQUET = PROJECT_ROOT / "mo_dci" / "output" / "mo_complaints_yearly_wide.parquet"
DST_CSV = PROJECT_ROOT / "mo_dci" / "output" / "mo_complaints_yearly_wide.csv"


def main() -> None:
    df = pl.read_parquet(SRC)
    # Pick the most-recent report's value per (year, line, metric)
    latest = (
        df.sort("report_year", descending=True)
        .group_by(["state", "year", "line", "metric"], maintain_order=True)
        .agg(pl.col("value").first())
    )
    # Pivot metric → columns
    wide = latest.pivot(
        values="value",
        index=["state", "year", "line"],
        on="metric",
    ).sort(["line", "year"])
    # Some lines may not have a relief % (e.g. HMO when zero complaints);
    # fill those with null and let derived columns be null too.
    if "complaints_total" not in wide.columns:
        raise RuntimeError("complaints_total missing from pivoted wide format")
    if "pct_resolved_consumer_relief" not in wide.columns:
        wide = wide.with_columns(pl.lit(None, dtype=pl.Float64).alias("pct_resolved_consumer_relief"))
    # Derive outcome counts. Round to int.
    wide = wide.with_columns([
        (pl.col("complaints_total") * pl.col("pct_resolved_consumer_relief"))
            .round(0).cast(pl.Int64, strict=False).alias("against_insurer"),
    ]).with_columns([
        (pl.col("complaints_total") - pl.col("against_insurer"))
            .cast(pl.Int64, strict=False).alias("for_insurer"),
    ])
    wide = wide.select([
        "state", "year", "line",
        "complaints_total",
        "pct_resolved_consumer_relief",
        "against_insurer",
        "for_insurer",
    ])
    wide.write_parquet(DST_PARQUET)
    wide.write_csv(DST_CSV)
    print(f"  wrote {DST_PARQUET} ({wide.height} rows)")
    # Spot-check the headline 'total' and 'private_passenger_auto' rows
    print(wide.filter(pl.col("line").is_in(["total", "private_passenger_auto"])).sort(["line", "year"]))


if __name__ == "__main__":
    main()
