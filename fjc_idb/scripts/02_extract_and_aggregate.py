"""Filter cv88on.txt to NoS=110 (Insurance) and aggregate to state-year counts.

Reads:
  fjc_idb/interim/cv88on.txt          (produced by 01_download.py)
  fjc_idb/scripts/districts.csv

Writes:
  fjc_idb/output/insurance_filings_by_state_year.{parquet,csv}
  fjc_idb/output/insurance_filings_by_state_year_origin.{parquet,csv}
  fjc_idb/output/run_log.txt          (appended each run)

Hard failures (no output written):
  - any DISTRICT in the filtered data missing from districts.csv
  - any state-year row appears more than once
  - state column has nulls after the join

Soft warnings (printed to log, do not block writes):
  - share of NoS=110 rows with null FILEDATE
  - trailing partial year flagged
"""
from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import polars as pl

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_TXT = PROJECT_ROOT / "fjc_idb" / "interim" / "cv88on.txt"
DISTRICTS_CSV = PROJECT_ROOT / "fjc_idb" / "scripts" / "districts.csv"
OUTPUT_DIR = PROJECT_ROOT / "fjc_idb" / "output"
LOG_PATH = OUTPUT_DIR / "run_log.txt"

# IDB ORIGIN codes. Labels for 1-6 are stable across codebook versions and
# documented in widely cited AOUSC sources. Codes 7+ and -8 appear in the data
# but the FJC civil codebook PDF was not obtainable at compile time (see
# PROVENANCE.md); their labels here are conservative and should be confirmed
# against the codebook before any analysis treats them as load-bearing.
ORIGIN_LABELS = {
    -8: "Missing / not coded",
    1: "Original",
    2: "Removed from state court",
    3: "Remanded from appellate",
    4: "Reinstated/reopened",
    5: "Transferred from another district (28 USC 1404)",
    6: "Multidistrict litigation transfer (28 USC 1407)",
    7: "Other / subsequent codebook variant",
    8: "Other / subsequent codebook variant",
    9: "Other / subsequent codebook variant",
    10: "Other / subsequent codebook variant",
    11: "Other / subsequent codebook variant",
    12: "Other / subsequent codebook variant",
    13: "Other / subsequent codebook variant",
}

NEEDED_COLS = ["CIRCUIT", "DISTRICT", "FILEDATE", "NOS", "ORIGIN"]


def log(msg: str, fh) -> None:
    print(msg)
    fh.write(msg + "\n")


def main() -> int:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    if not DATA_TXT.exists():
        print(f"ERROR: {DATA_TXT} not found. Run 01_download.py first.", file=sys.stderr)
        return 1
    if not DISTRICTS_CSV.exists():
        print(f"ERROR: {DISTRICTS_CSV} not found.", file=sys.stderr)
        return 1

    with LOG_PATH.open("a") as logf:
        run_started = datetime.now(timezone.utc).isoformat(timespec="seconds")
        log(f"\n=== run started {run_started} ===", logf)

        # Read everything as strings; cast on demand. Polars scan_csv with explicit
        # schema_overrides keeps us safe against type-inference surprises.
        all_string_schema = {
            "CIRCUIT": pl.String,
            "DISTRICT": pl.String,
            "OFFICE": pl.String,
            "DOCKET": pl.String,
            "ORIGIN": pl.String,
            "FILEDATE": pl.String,
            "NOS": pl.String,
            "TERMDATE": pl.String,
        }
        lf = pl.scan_csv(
            DATA_TXT,
            separator="\t",
            encoding="utf8-lossy",          # tolerates rare non-ASCII bytes
            has_header=True,
            infer_schema_length=0,
            schema_overrides=all_string_schema,
            null_values=[""],
            truncate_ragged_lines=True,
        )

        # Filter: NoS == 110 and FILEDATE not null and parseable.
        filtered = (
            lf.select(NEEDED_COLS)
            .with_columns(
                pl.col("NOS").cast(pl.Int32, strict=False),
                pl.col("ORIGIN").cast(pl.Int8, strict=False),
                pl.col("FILEDATE").str.to_date("%m/%d/%Y", strict=False).alias("filedate_dt"),
            )
            .filter(pl.col("NOS") == 110)
        )

        # Materialize once; we need multiple aggregations + sanity checks.
        df = filtered.collect()
        log(f"Total NoS=110 rows: {len(df):,}", logf)

        # Soft warning: null FILEDATE share among NoS=110.
        null_filedate = df.filter(pl.col("filedate_dt").is_null()).height
        log(f"NoS=110 rows with null FILEDATE: {null_filedate:,} ({100.0 * null_filedate / max(len(df), 1):.3f}%)", logf)

        df = df.filter(pl.col("filedate_dt").is_not_null()).with_columns(
            year=pl.col("filedate_dt").dt.year().cast(pl.Int32),
        )

        # Restrict to in-window filings: 1988-onward.
        # The cv88on file contains pre-1988 cases that were still active in 1988,
        # which makes pre-1988 counts a non-random sample. Drop them.
        pre_1988 = df.filter(pl.col("year") < 1988).height
        log(f"Pre-1988 NoS=110 rows dropped (cases filed before 1988 but pending in 1988): {pre_1988:,}", logf)
        df = df.filter(pl.col("year") >= 1988)

        # Build the join key: 4-char district code (CC + DD).
        df = df.with_columns(
            district_code=pl.concat_str([
                pl.col("CIRCUIT").str.zfill(2),
                pl.col("DISTRICT").str.zfill(2),
            ])
        )

        # Hard failure: every district code in the data must be in the mapping.
        districts = pl.read_csv(DISTRICTS_CSV)
        data_codes = set(df["district_code"].unique().to_list())
        map_codes = set(districts["district_code"].to_list())
        missing = data_codes - map_codes
        if missing:
            log(f"HARD FAILURE: district codes in data missing from districts.csv: {sorted(missing)}", logf)
            return 2
        log(f"All {len(data_codes)} district codes in NoS=110 data are mapped.", logf)

        joined = df.join(districts, on="district_code", how="left")
        null_state = joined.filter(pl.col("state_postal").is_null()).height
        if null_state:
            log(f"HARD FAILURE: {null_state} rows have null state after join.", logf)
            return 3

        # Trailing partial year warning.
        max_filedate = joined["filedate_dt"].max()
        max_year = int(joined["year"].max())
        log(f"Max FILEDATE in data: {max_filedate}", logf)
        log(f"Year {max_year} is incomplete relative to a calendar year (data through {max_filedate}); treat as partial.", logf)

        # Aggregation 1: state x year.
        agg_sy = (
            joined.group_by(["state_postal", "year"])
            .agg(pl.len().alias("count"))
            .sort(["state_postal", "year"])
            .rename({"state_postal": "state"})
        )
        # Hard failure: each (state, year) pair appears at most once.
        if agg_sy.group_by(["state", "year"]).len().filter(pl.col("len") > 1).height > 0:
            log("HARD FAILURE: duplicate (state, year) rows.", logf)
            return 4

        # Aggregation 2: state x year x origin.
        agg_syo = (
            joined.group_by(["state_postal", "year", "ORIGIN"])
            .agg(pl.len().alias("count"))
            .sort(["state_postal", "year", "ORIGIN"])
            .rename({"state_postal": "state", "ORIGIN": "origin_code"})
        )
        agg_syo = agg_syo.with_columns(
            origin_label=pl.col("origin_code").map_elements(
                lambda c: ORIGIN_LABELS.get(c, "Unknown") if c is not None else "Missing",
                return_dtype=pl.String,
            )
        ).select(["state", "year", "origin_code", "origin_label", "count"])

        # Write outputs.
        sy_pq = OUTPUT_DIR / "insurance_filings_by_state_year.parquet"
        sy_csv = OUTPUT_DIR / "insurance_filings_by_state_year.csv"
        syo_pq = OUTPUT_DIR / "insurance_filings_by_state_year_origin.parquet"
        syo_csv = OUTPUT_DIR / "insurance_filings_by_state_year_origin.csv"
        agg_sy.write_parquet(sy_pq)
        agg_sy.write_csv(sy_csv)
        agg_syo.write_parquet(syo_pq)
        agg_syo.write_csv(syo_csv)
        log(f"Wrote {sy_pq.name} ({len(agg_sy):,} rows)", logf)
        log(f"Wrote {syo_pq.name} ({len(agg_syo):,} rows)", logf)

        # ----- soft sanity checks -----
        log("\n--- global yearly totals ---", logf)
        yearly = agg_sy.group_by("year").agg(pl.col("count").sum().alias("us_total")).sort("year")
        for r in yearly.iter_rows(named=True):
            log(f"  {r['year']}: {r['us_total']:>7,}", logf)

        log("\n--- spot check: MD, CA, TX, FL last 6 years ---", logf)
        latest_years = sorted(agg_sy["year"].unique().to_list())[-6:]
        spot = (
            agg_sy.filter(
                pl.col("state").is_in(["MD", "CA", "TX", "FL"])
                & pl.col("year").is_in(latest_years)
            )
            .pivot(index="state", on="year", values="count")
            .sort("state")
        )
        log(str(spot), logf)

        log("\n--- ORIGIN breakdown nationwide, last 5 years ---", logf)
        latest5 = sorted(agg_syo["year"].unique().to_list())[-5:]
        origin_nat = (
            agg_syo.filter(pl.col("year").is_in(latest5))
            .group_by(["year", "origin_code", "origin_label"])
            .agg(pl.col("count").sum().alias("n"))
            .sort(["year", "origin_code"])
        )
        log(str(origin_nat), logf)

        log(f"=== run completed {datetime.now(timezone.utc).isoformat(timespec='seconds')} ===", logf)
    return 0


if __name__ == "__main__":
    sys.exit(main())
