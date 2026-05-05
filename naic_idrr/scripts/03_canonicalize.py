"""Reshape NAIC IDRR per-state yearly complaints into the cross-state
aggregate schema defined in multi_state_acquisition_plan.md §4.2.

Input:
  naic_idrr/output/naic_idrr_complaints_state_yearly.parquet
    Columns: year, jurisdiction, jurisdiction_name, complaints, inquiries
    Coverage: 1998-2022 (no 2003), 56 jurisdictions (50 states + DC + 5 territories)

Outputs:
  naic_idrr/output/idrr_complaints_yearly.parquet
  naic_idrr/output/idrr_complaints_yearly.csv
    Columns: state, year, line, outcome_category, count, source_type,
             is_partial_year, notes
    Coverage: 1998-2022 (no 2003), 51 jurisdictions (50 states + DC; territories dropped)
  naic_idrr/output/tail_states_coverage.csv
    Per-tail-state IDRR coverage summary for the 30 jurisdictions in §8.2.

Also appends a Phase 4 verification block to naic_idrr/output/run_log.txt.

Phase 4 of multi_state_acquisition_plan.md (§8). Idempotent: re-running with
unchanged inputs yields byte-identical parquet output (we control row order
and dtypes; polars writes deterministic parquet for a fixed input).
"""
from __future__ import annotations

import csv
import hashlib
from datetime import datetime, timezone
from pathlib import Path

import polars as pl

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_ROOT = PROJECT_ROOT / "naic_idrr"
OUTPUT = DATASET_ROOT / "output"
IN_PARQUET = OUTPUT / "naic_idrr_complaints_state_yearly.parquet"
OUT_PARQUET = OUTPUT / "idrr_complaints_yearly.parquet"
OUT_CSV = OUTPUT / "idrr_complaints_yearly.csv"
TAIL_COVERAGE_CSV = OUTPUT / "tail_states_coverage.csv"
LOG_PATH = OUTPUT / "run_log.txt"

# 5 territories to drop. Output is restricted to 50 states + DC per
# the plan's "every state + DC" acceptance criterion.
TERRITORIES = {"AS", "GU", "MP", "PR", "VI"}

# §8.2 of the plan: 30 tail jurisdictions (NAIC-only coverage).
TAIL_STATES = [
    "AL", "AK", "AR", "AZ", "DE", "DC", "GA", "HI", "IA", "KY",
    "LA", "ME", "MN", "MS", "MT", "NE", "NV", "NH", "NM", "ND",
    "OK", "OR", "RI", "SC", "SD", "TN", "UT", "VT", "WV", "WY",
]

# §8.2 calls these out as "arguably worth pulling later as Phase 5":
PHASE5_CANDIDATES = {"LA", "MN", "OR", "TN", "VT"}

# 50 USPS state codes + DC (the universe of canonical-output jurisdictions).
US_STATES_PLUS_DC = {
    "AL", "AK", "AZ", "AR", "CA", "CO", "CT", "DE", "DC", "FL",
    "GA", "HI", "ID", "IL", "IN", "IA", "KS", "KY", "LA", "ME",
    "MD", "MA", "MI", "MN", "MS", "MO", "MT", "NE", "NV", "NH",
    "NJ", "NM", "NY", "NC", "ND", "OH", "OK", "OR", "PA", "RI",
    "SC", "SD", "TN", "TX", "UT", "VT", "VA", "WA", "WV", "WI", "WY",
}

CANONICAL_COLUMNS = [
    "state", "year", "line", "outcome_category", "count",
    "source_type", "is_partial_year", "notes",
]


def canonicalize(df: pl.DataFrame) -> pl.DataFrame:
    out = (
        df.filter(~pl.col("jurisdiction").is_in(list(TERRITORIES)))
        .select(
            pl.col("jurisdiction").alias("state"),
            pl.col("year"),
            pl.lit("all_lines").alias("line"),
            pl.lit(None, dtype=pl.String).alias("outcome_category"),
            pl.col("complaints").alias("count"),
            pl.lit("idrr").alias("source_type"),
            pl.lit(False).alias("is_partial_year"),
            (pl.lit("NAIC IDRR Vol 1, data year ") + pl.col("year").cast(pl.String)
             + pl.lit("; complaints received, not closed")).alias("notes"),
        )
        .sort(["state", "year"])
    )
    assert out.columns == CANONICAL_COLUMNS, out.columns
    return out


def build_tail_coverage(df_canonical: pl.DataFrame, all_years: list[int]) -> list[dict]:
    rows = []
    for st in TAIL_STATES:
        sub = df_canonical.filter(pl.col("state") == st).sort("year")
        years_present = sub["year"].to_list()
        non_null = sub.filter(pl.col("count").is_not_null())
        years_with_count = non_null["year"].to_list()
        if years_with_count:
            first = min(years_with_count)
            last = max(years_with_count)
        else:
            first = last = None
        # Within the in-range span, which years lack a count row?
        in_range = [y for y in all_years if first is not None and first <= y <= last]
        missing = sorted(set(in_range) - set(years_with_count))
        null_rows = sub.filter(pl.col("count").is_null())["year"].to_list()
        mean_count = (
            float(non_null["count"].mean()) if non_null.height else None
        )
        rows.append(
            {
                "state": st,
                "first_year": first if first is not None else "",
                "last_year": last if last is not None else "",
                "years_present": len(years_with_count),
                "missing_years_in_range": ";".join(str(y) for y in missing),
                "null_count_years": ";".join(str(y) for y in null_rows),
                "mean_complaints": f"{mean_count:.1f}" if mean_count is not None else "",
                "phase5_candidate": "yes" if st in PHASE5_CANDIDATES else "no",
            }
        )
    return rows


def write_csv_dicts(path: Path, rows: list[dict]) -> None:
    if not rows:
        path.write_text("")
        return
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    df = pl.read_parquet(IN_PARQUET)
    out = canonicalize(df)

    # Sanity assertions: the canonical output should be 50 states + DC, no others.
    states = set(out["state"].unique().to_list())
    extra = states - US_STATES_PLUS_DC
    missing = US_STATES_PLUS_DC - states
    assert not extra, f"unexpected non-state codes in output: {sorted(extra)}"
    if missing:
        # Don't fail — IDRR coverage may legitimately omit a jurisdiction in some years —
        # but record it.
        print(f"WARN: jurisdictions absent from IDRR canonical output entirely: {sorted(missing)}")

    OUT_PARQUET.parent.mkdir(parents=True, exist_ok=True)
    out.write_parquet(OUT_PARQUET)
    out.write_csv(OUT_CSV)

    # Tail-state cross-walk.
    all_years = sorted(out["year"].unique().to_list())
    tail_rows = build_tail_coverage(out, all_years)
    write_csv_dicts(TAIL_COVERAGE_CSV, tail_rows)

    # Append run-log block.
    now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%MZ")
    lines = []
    lines.append("")
    lines.append(f"### {now} — phase 4 canonicalize")
    lines.append("")
    lines.append(f"- input rows: {df.height}")
    lines.append(f"- output rows: {out.height}  (territories AS/GU/MP/PR/VI dropped)")
    lines.append(f"- output years: {min(all_years)}–{max(all_years)} "
                 f"(missing in-range: {sorted(set(range(min(all_years), max(all_years)+1)) - set(all_years))})")
    lines.append(f"- output jurisdictions: {len(states)} (expected 51)")
    lines.append(f"- output sha256: {sha256_file(OUT_PARQUET)}")
    lines.append("")
    lines.append("Tail-state coverage (30 jurisdictions per §8.2):")
    anomalies = [r for r in tail_rows
                 if (r["missing_years_in_range"] and r["missing_years_in_range"] != "2003")
                 or r["null_count_years"]
                 or not r["first_year"]]
    if anomalies:
        for r in anomalies:
            lines.append(f"  - {r['state']}: missing_in_range={r['missing_years_in_range']!r} "
                         f"null_count={r['null_count_years']!r} first={r['first_year']} last={r['last_year']}")
    else:
        lines.append("  - no anomalies; every tail state has continuous IDRR coverage 1998–2022 except 2003 (parser gap, project-wide)")
    lines.append("")

    with LOG_PATH.open("a") as f:
        f.write("\n".join(lines) + "\n")

    print(f"wrote {OUT_PARQUET} ({out.height} rows)")
    print(f"wrote {OUT_CSV}")
    print(f"wrote {TAIL_COVERAGE_CSV}")
    print(f"appended run-log block to {LOG_PATH}")


if __name__ == "__main__":
    main()
