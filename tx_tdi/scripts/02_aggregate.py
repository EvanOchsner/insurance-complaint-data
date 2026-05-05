"""Parse the raw TDI pull, derive year_closed, write three aggregated outputs.

Inputs:
  tx_tdi/interim/jjc8-mxkg.parquet
Outputs:
  tx_tdi/output/tx_complaints_complaint_level.{parquet,csv}
  tx_tdi/output/tx_complaints_yearly.{parquet,csv}
  tx_tdi/output/tx_complaints_yearly_confirmed.{parquet,csv}
  tx_tdi/output/run_log.txt   (appended)
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import polars as pl

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INTERIM_PARQUET = PROJECT_ROOT / "tx_tdi" / "interim" / "jjc8-mxkg.parquet"
OUTPUT_DIR = PROJECT_ROOT / "tx_tdi" / "output"
LOG_PATH = OUTPUT_DIR / "run_log.txt"

VALID_FINDINGS = {"Confirmed", "Not Confirmed"}


def log(msg: str, fh) -> None:
    print(msg)
    fh.write(msg + "\n")


def main() -> int:
    if not INTERIM_PARQUET.exists():
        print(f"ERROR: {INTERIM_PARQUET} not found. Run 01_pull.py first.", file=sys.stderr)
        return 1
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    with LOG_PATH.open("a") as logf:
        run_started = datetime.now(timezone.utc).isoformat(timespec="seconds")
        log(f"\n=== run started {run_started} ===", logf)

        raw = pl.read_parquet(INTERIM_PARQUET)
        log(f"Loaded {len(raw):,} raw rows from {INTERIM_PARQUET.name}", logf)

        # Parse dates. Socrata serves ISO timestamps like '2012-06-12T00:00:00.000'.
        df = raw.with_columns(
            pl.col("received_date").str.to_datetime(strict=False).dt.date().alias("received_date"),
            pl.col("closed_date").str.to_datetime(strict=False).dt.date().alias("closed_date"),
            pl.col("complaint_number").cast(pl.Int64, strict=False),
        )

        # Drop rows where closed_date is null (open complaints — not in our scope).
        n_open = df.filter(pl.col("closed_date").is_null()).height
        log(f"Rows with null closed_date dropped (still-open complaints): {n_open:,}", logf)
        df = df.filter(pl.col("closed_date").is_not_null())

        # Drop rows where finding_type is null (one row in 281k).
        n_no_finding = df.filter(pl.col("finding_type").is_null()).height
        log(f"Rows with null finding_type dropped: {n_no_finding:,}", logf)
        df = df.filter(pl.col("finding_type").is_not_null())

        # Hard fail if a third finding_type value ever appears.
        finding_values = set(df["finding_type"].unique().to_list())
        unexpected = finding_values - VALID_FINDINGS
        if unexpected:
            log(f"HARD FAILURE: unexpected finding_type values {sorted(unexpected)} — TDI may have introduced a new disposition. Update VALID_FINDINGS in this script after review.", logf)
            return 2
        log(f"finding_type values: {sorted(finding_values)} (both expected)", logf)

        df = df.with_columns(
            year_closed=pl.col("closed_date").dt.year().cast(pl.Int32),
            is_confirmed=(pl.col("finding_type") == "Confirmed"),
        )

        # Hard sanity: complaint_number is unique in the spine.
        n_dup = df.height - df.unique(subset=["complaint_number"]).height
        if n_dup > 0:
            log(f"HARD FAILURE: {n_dup} duplicate complaint_number values — the 'spine' should be unique. Bailing.", logf)
            return 3
        log(f"complaint_number is unique across {df.height:,} rows.", logf)

        # ---- Output 1: complaint-level ----
        complaint_level = df.select([
            "complaint_number", "received_date", "closed_date", "year_closed",
            "complaint_filed_by", "complainant_type", "involved_party_type",
            "complaint_type", "coverage_type", "coverage_level",
            "finding_type", "is_confirmed", "keywords",
        ]).sort("complaint_number")
        cl_pq = OUTPUT_DIR / "tx_complaints_complaint_level.parquet"
        cl_csv = OUTPUT_DIR / "tx_complaints_complaint_level.csv"
        complaint_level.write_parquet(cl_pq)
        complaint_level.write_csv(cl_csv)
        log(f"Wrote {cl_pq.name} ({len(complaint_level):,} rows)", logf)

        # ---- Output 2: yearly multi-dim pivot ----
        yearly = (
            df.group_by(["year_closed", "coverage_type", "finding_type"])
            .agg(pl.len().alias("count"))
            .sort(["year_closed", "coverage_type", "finding_type"])
        )
        y_pq = OUTPUT_DIR / "tx_complaints_yearly.parquet"
        y_csv = OUTPUT_DIR / "tx_complaints_yearly.csv"
        yearly.write_parquet(y_pq)
        yearly.write_csv(y_csv)
        log(f"Wrote {y_pq.name} ({len(yearly):,} rows)", logf)

        # ---- Output 3: yearly Confirmed/Not-Confirmed (the headline) ----
        # By coverage:
        by_cov = (
            df.group_by(["year_closed", "coverage_type"])
            .agg(
                pl.len().alias("total"),
                pl.col("is_confirmed").sum().alias("confirmed"),
            )
            .with_columns(
                not_confirmed=(pl.col("total") - pl.col("confirmed")),
                confirmed_rate=(pl.col("confirmed") / pl.col("total")),
            )
            .select(["year_closed", "coverage_type", "total", "confirmed", "not_confirmed", "confirmed_rate"])
        )
        # Across all coverages — the "ALL" row per year:
        all_cov = (
            df.group_by("year_closed")
            .agg(
                pl.len().alias("total"),
                pl.col("is_confirmed").sum().alias("confirmed"),
            )
            .with_columns(
                coverage_type=pl.lit("ALL"),
                not_confirmed=(pl.col("total") - pl.col("confirmed")),
                confirmed_rate=(pl.col("confirmed") / pl.col("total")),
            )
            .select(["year_closed", "coverage_type", "total", "confirmed", "not_confirmed", "confirmed_rate"])
        )
        confirmed_yr = (
            pl.concat([all_cov, by_cov])
            .sort(["year_closed", "coverage_type"])
        )
        c_pq = OUTPUT_DIR / "tx_complaints_yearly_confirmed.parquet"
        c_csv = OUTPUT_DIR / "tx_complaints_yearly_confirmed.csv"
        confirmed_yr.write_parquet(c_pq)
        confirmed_yr.write_csv(c_csv)
        log(f"Wrote {c_pq.name} ({len(confirmed_yr):,} rows)", logf)

        # ---- Soft sanity / headline numbers ----
        max_closed = df["closed_date"].max()
        max_year = int(df["year_closed"].max())
        log(f"\nMax closed_date: {max_closed}", logf)
        log(f"Year {max_year} is partial; treat as preliminary.", logf)

        log("\n--- ALL coverages, by year ---", logf)
        all_yearly = all_cov.sort("year_closed")
        with pl.Config(tbl_rows=40):
            log(str(all_yearly), logf)

        log("\n--- by coverage_type, last 5 full years ---", logf)
        latest5 = sorted([y for y in df["year_closed"].unique().to_list() if y < max_year])[-5:]
        recent = (
            by_cov.filter(pl.col("year_closed").is_in(latest5))
            .pivot(index="coverage_type", on="year_closed", values="confirmed_rate")
            .sort("coverage_type")
        )
        with pl.Config(tbl_rows=20, tbl_cols=10, fmt_float="full"):
            log(str(recent), logf)

        log(f"=== run completed {datetime.now(timezone.utc).isoformat(timespec='seconds')} ===", logf)
    return 0


if __name__ == "__main__":
    sys.exit(main())
