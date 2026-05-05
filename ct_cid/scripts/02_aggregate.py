"""Parse the raw CT CID pull, derive year_closed + a 3-bucket
against/for/ambiguous classification of `disposition`, and write three
aggregated outputs.

Inputs:
  ct_cid/interim/t64r-mt64.parquet
Outputs:
  ct_cid/output/ct_complaints_complaint_level.{parquet,csv}
  ct_cid/output/ct_complaints_yearly.{parquet,csv}
  ct_cid/output/ct_complaints_yearly_confirmed.{parquet,csv}
  ct_cid/output/run_log.txt   (appended)

CT does not publish a clean Confirmed/Not-Confirmed binary like TX. The
closest analog is `disposition`, which we group into three buckets:

  AGAINST INSURER (regulator-side action favored consumer):
    - Company Position Overturned
    - Claim Settled
    - Compromised Settlement/Resolution
    - Claim Reopened
    - Fine Assessed
    - Referred to Other Division for Possible Disciplinary Action

  FOR INSURER (regulator confirmed insurer position):
    - Company Position Substantiated

  AMBIGUOUS (no clear regulator finding either way):
    - Question of Fact/Contract/Provision/Legal Issue
    - No Jurisdiction
    - No Action Requested/Required
    - Insufficient Information
    - Complaint Withdrawn
    - Referred to Outside Agency/Dept
    - Referred to Another State's Dept of Insurance

Rows where `disposition` is null are kept in the `total` tally but excluded
from the bucket counts (analogous to TX's handling of null `finding_type`).
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import polars as pl

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INTERIM_PARQUET = PROJECT_ROOT / "ct_cid" / "interim" / "t64r-mt64.parquet"
OUTPUT_DIR = PROJECT_ROOT / "ct_cid" / "output"
LOG_PATH = OUTPUT_DIR / "run_log.txt"

DISPOSITION_AGAINST_INSURER = {
    "Company Position Overturned",
    "Claim Settled",
    "Compromised Settlement/Resolution",
    "Claim Reopened",
    "Fine Assessed",
    "Referred to Other Division for Possible Disciplinary Action",
}
DISPOSITION_FOR_INSURER = {
    "Company Position Substantiated",
}
DISPOSITION_AMBIGUOUS = {
    "Question of Fact/Contract/Provision/Legal Issue",
    "No Jurisdiction",
    "No Action Requested/Required",
    "Insufficient Information",
    "Complaint Withdrawn",
    "Referred to Outside Agency/Dept",
    "Referred to Another State’s Dept of Insurance",
}
KNOWN_DISPOSITIONS = (
    DISPOSITION_AGAINST_INSURER
    | DISPOSITION_FOR_INSURER
    | DISPOSITION_AMBIGUOUS
)


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

        df = raw.with_columns(
            pl.col("opened").str.to_datetime(strict=False).dt.date().alias("opened"),
            pl.col("closed").str.to_datetime(strict=False).dt.date().alias("closed"),
            pl.col("recovery").cast(pl.Float64, strict=False).alias("recovery"),
        )

        # Restrict the headline dataset to closed complaints. CT's `status`
        # has 20+ in-progress states; only `Closed` represents a fully
        # processed complaint with a final regulator handling.
        n_total = df.height
        df = df.filter(pl.col("status") == "Closed")
        log(f"Filtered to status='Closed': {df.height:,} of {n_total:,} rows", logf)

        # Drop rows where closed date is null (defensive — should not happen
        # for status='Closed').
        n_no_close = df.filter(pl.col("closed").is_null()).height
        if n_no_close > 0:
            log(f"WARNING: {n_no_close} 'Closed' rows have null closed date — dropping", logf)
            df = df.filter(pl.col("closed").is_not_null())

        # Hard fail if a previously-unseen disposition appears (forces the
        # mapping in this script to be updated explicitly rather than
        # silently miscategorizing). Null disposition is allowed and tracked.
        seen_dispositions = {
            v for v in df["disposition"].unique().to_list() if v is not None
        }
        unexpected = seen_dispositions - KNOWN_DISPOSITIONS
        if unexpected:
            log(
                f"HARD FAILURE: unexpected disposition values {sorted(unexpected)} — "
                f"CID has introduced new categories. Update DISPOSITION_* sets in "
                f"this script after reviewing whether each maps to "
                f"AGAINST/FOR/AMBIGUOUS.",
                logf,
            )
            return 2
        log(f"Disposition values seen: {len(seen_dispositions)} (all mapped)", logf)

        df = df.with_columns(
            year_closed=pl.col("closed").dt.year().cast(pl.Int32),
            disposition_bucket=(
                pl.when(pl.col("disposition").is_in(list(DISPOSITION_AGAINST_INSURER)))
                .then(pl.lit("against_insurer"))
                .when(pl.col("disposition").is_in(list(DISPOSITION_FOR_INSURER)))
                .then(pl.lit("for_insurer"))
                .when(pl.col("disposition").is_in(list(DISPOSITION_AMBIGUOUS)))
                .then(pl.lit("ambiguous"))
                .otherwise(pl.lit(None, dtype=pl.String))
            ),
        )
        df = df.with_columns(
            is_against_insurer=(pl.col("disposition_bucket") == "against_insurer"),
            is_for_insurer=(pl.col("disposition_bucket") == "for_insurer"),
            is_ambiguous=(pl.col("disposition_bucket") == "ambiguous"),
            has_disposition=pl.col("disposition").is_not_null(),
        )

        # Hard sanity: file_no is unique across closed complaints.
        n_dup = df.height - df.unique(subset=["file_no"]).height
        if n_dup > 0:
            log(f"WARNING: {n_dup} duplicate file_no values among closed complaints", logf)
        else:
            log(f"file_no is unique across {df.height:,} closed rows.", logf)

        # ---- Output 1: complaint-level ----
        complaint_level = df.select([
            "file_no", "opened", "closed", "year_closed",
            "company", "coverage", "subcoverage",
            "reason", "subreason",
            "disposition", "disposition_bucket",
            "is_against_insurer", "is_for_insurer", "is_ambiguous",
            "conclusion", "recovery", "status",
        ]).sort(["year_closed", "file_no"])
        cl_pq = OUTPUT_DIR / "ct_complaints_complaint_level.parquet"
        cl_csv = OUTPUT_DIR / "ct_complaints_complaint_level.csv"
        complaint_level.write_parquet(cl_pq)
        complaint_level.write_csv(cl_csv)
        log(f"Wrote {cl_pq.name} ({len(complaint_level):,} rows)", logf)

        # ---- Output 2: yearly multi-dim pivot (year × coverage × disposition) ----
        yearly = (
            df.group_by(["year_closed", "coverage", "disposition"])
            .agg(pl.len().alias("count"))
            .sort(["year_closed", "coverage", "disposition"])
        )
        y_pq = OUTPUT_DIR / "ct_complaints_yearly.parquet"
        y_csv = OUTPUT_DIR / "ct_complaints_yearly.csv"
        yearly.write_parquet(y_pq)
        yearly.write_csv(y_csv)
        log(f"Wrote {y_pq.name} ({len(yearly):,} rows)", logf)

        # ---- Output 3: yearly headline (against/for/ambiguous + null) ----
        # By coverage:
        by_cov = (
            df.group_by(["year_closed", "coverage"])
            .agg(
                pl.len().alias("total"),
                pl.col("is_against_insurer").sum().alias("against_insurer"),
                pl.col("is_for_insurer").sum().alias("for_insurer"),
                pl.col("is_ambiguous").sum().alias("ambiguous"),
                pl.col("has_disposition").sum().alias("with_disposition"),
            )
            .with_columns(
                no_disposition=(pl.col("total") - pl.col("with_disposition")),
                against_rate_of_decided=(
                    pl.col("against_insurer")
                    / (pl.col("against_insurer") + pl.col("for_insurer"))
                ),
                against_rate_of_total=(
                    pl.col("against_insurer") / pl.col("total")
                ),
            )
            .with_columns(
                # Canonical cross-state "no_decision" = ambiguous + null disposition.
                # Both buckets mean "no clean for/against finding"; the unified
                # viewer treats them as one.
                no_decision=(pl.col("ambiguous") + pl.col("no_disposition")),
            )
            .select([
                "year_closed", "coverage",
                "total", "against_insurer", "for_insurer", "ambiguous",
                "no_disposition", "no_decision",
                "against_rate_of_decided", "against_rate_of_total",
            ])
        )
        # Across all coverages — the "ALL" row per year:
        all_cov = (
            df.group_by("year_closed")
            .agg(
                pl.len().alias("total"),
                pl.col("is_against_insurer").sum().alias("against_insurer"),
                pl.col("is_for_insurer").sum().alias("for_insurer"),
                pl.col("is_ambiguous").sum().alias("ambiguous"),
                pl.col("has_disposition").sum().alias("with_disposition"),
            )
            .with_columns(
                coverage=pl.lit("ALL"),
                no_disposition=(pl.col("total") - pl.col("with_disposition")),
                against_rate_of_decided=(
                    pl.col("against_insurer")
                    / (pl.col("against_insurer") + pl.col("for_insurer"))
                ),
                against_rate_of_total=(
                    pl.col("against_insurer") / pl.col("total")
                ),
            )
            .with_columns(
                no_decision=(pl.col("ambiguous") + pl.col("no_disposition")),
            )
            .select([
                "year_closed", "coverage",
                "total", "against_insurer", "for_insurer", "ambiguous",
                "no_disposition", "no_decision",
                "against_rate_of_decided", "against_rate_of_total",
            ])
        )
        confirmed_yr = (
            pl.concat([all_cov, by_cov])
            .sort(["year_closed", "coverage"])
        )
        c_pq = OUTPUT_DIR / "ct_complaints_yearly_confirmed.parquet"
        c_csv = OUTPUT_DIR / "ct_complaints_yearly_confirmed.csv"
        confirmed_yr.write_parquet(c_pq)
        confirmed_yr.write_csv(c_csv)
        log(f"Wrote {c_pq.name} ({len(confirmed_yr):,} rows)", logf)

        # ---- Soft sanity / headline numbers ----
        max_closed = df["closed"].max()
        max_year = int(df["year_closed"].max())
        log(f"\nMax closed date: {max_closed}", logf)
        log(f"Year {max_year} is partial; treat as preliminary.", logf)

        log("\n--- ALL coverages, by year ---", logf)
        all_yearly = all_cov.sort("year_closed")
        with pl.Config(tbl_rows=40, fmt_float="full"):
            log(str(all_yearly), logf)

        log(f"=== run completed {datetime.now(timezone.utc).isoformat(timespec='seconds')} ===", logf)
    return 0


if __name__ == "__main__":
    sys.exit(main())
