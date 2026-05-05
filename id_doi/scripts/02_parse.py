"""Parse the Idaho DOI Consumer Complaint Comparison Tables HTML page into
per-company per-year per-line parquet outputs.

Inputs:
  id_doi/interim/landing.html
Outputs:
  id_doi/output/id_complaints_company_yearly.{parquet,csv}
  id_doi/output/id_complaints_yearly.{parquet,csv}
  id_doi/output/run_log.txt
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import polars as pl

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INTERIM_DIR = PROJECT_ROOT / "id_doi" / "interim"
LANDING_HTML = INTERIM_DIR / "landing.html"
MANIFEST_PATH = INTERIM_DIR / "manifest.json"
OUTPUT_DIR = PROJECT_ROOT / "id_doi" / "output"
LOG_PATH = OUTPUT_DIR / "run_log.txt"

# Idaho's category labels → canonical line slugs. We preserve the
# group-vs-individual split as separate slugs since Idaho explicitly
# distinguishes them; KS lumps them as "health".
LINE_NORMALIZE = {
    "auto": "auto",
    "homeowner": "homeowners",
    "group accident/health": "group_health",
    "individual accident/health": "individual_health",
}


def log(msg: str, fh) -> None:
    print(msg)
    fh.write(msg + "\n")


def parse_premium(s: str) -> float | None:
    if s is None:
        return None
    s = s.strip().lstrip("$").replace(",", "")
    if not s or s.lower() in ("none", "n/a"):
        return None
    return float(s)


def parse_market_share(s: str) -> float | None:
    if s is None:
        return None
    s = s.strip().rstrip("%")
    if not s or s.lower() in ("none", "n/a"):
        return None
    return float(s) / 100.0


def parse_int(s: str) -> int | None:
    if s is None:
        return None
    s = s.strip().replace(",", "")
    if not s or s.lower() in ("none", "n/a"):
        return None
    return int(s)


def parse_index(s: str) -> float | None:
    if s is None:
        return None
    s = s.strip()
    if not s or s.upper() in ("DNC", "N/A"):
        return None
    return float(s)


def main() -> int:
    if not LANDING_HTML.exists():
        print(f"ERROR: {LANDING_HTML} not found. Run 01_download.py first.", file=sys.stderr)
        return 1
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    from bs4 import BeautifulSoup
    html = LANDING_HTML.read_text()
    soup = BeautifulSoup(html, "html.parser")
    tables = soup.find_all("table")
    if len(tables) != 1:
        print(f"HARD FAILURE: expected 1 <table>, found {len(tables)}", file=sys.stderr)
        return 2
    table = tables[0]

    rows = []
    expected_header = ["Year", "Category", "Company Name", "Premium",
                       "Market Share", "# of Complaints", "Index"]
    header_seen = None
    for r in table.find_all("tr"):
        cells = [c.get_text(strip=True) for c in r.find_all(["td", "th"])]
        if header_seen is None:
            header_seen = cells
            continue
        if len(cells) != 7:
            continue
        rows.append(cells)

    if header_seen != expected_header:
        print(f"HARD FAILURE: unexpected table header {header_seen!r}", file=sys.stderr)
        return 3

    with LOG_PATH.open("a") as logf:
        log(f"\n=== run started {datetime.now(timezone.utc).isoformat(timespec='seconds')} ===", logf)
        log(f"Parsed {len(rows)} data rows from {LANDING_HTML.name}", logf)

        records: list[dict] = []
        unknown_cats: set[str] = set()
        n_swapped = 0
        for cells in rows:
            yr_s, cat_s, name, prem, share, comps, idx = cells
            line_slug = LINE_NORMALIZE.get(cat_s.lower())
            if line_slug is None:
                unknown_cats.add(cat_s)
                continue
            # Per-row data-entry quirk: 5 rows in 2018 Individual Accident/Health
            # have the Complaints and Index columns swapped (Complaints holds a
            # decimal index value, Index holds an integer count). Detect and fix.
            comps_field, idx_field = comps, idx
            if "." in comps and (idx.strip().isdigit() or idx.strip() in ("0", "")):
                comps_field, idx_field = idx, comps
                n_swapped += 1
            records.append({
                "year": int(yr_s),
                "line": line_slug,
                "company_name": name,
                "premium": parse_premium(prem),
                "market_share": parse_market_share(share),
                "complaints": parse_int(comps_field),
                "complaint_index": parse_index(idx_field),
            })
        if n_swapped:
            log(f"NOTE: corrected {n_swapped} rows where Complaints/Index columns were swapped at source", logf)

        if unknown_cats:
            log(f"HARD FAILURE: unknown category labels {sorted(unknown_cats)}", logf)
            return 4
        if not records:
            log("HARD FAILURE: no rows parsed", logf)
            return 5

        df = pl.DataFrame(records, schema={
            "year": pl.Int32,
            "line": pl.String,
            "company_name": pl.String,
            "premium": pl.Float64,
            "market_share": pl.Float64,
            "complaints": pl.Int64,
            "complaint_index": pl.Float64,
        }).sort(["year", "line", "company_name"])

        # ---- Output 1: per-company per-year per-line ----
        cy_pq = OUTPUT_DIR / "id_complaints_company_yearly.parquet"
        cy_csv = OUTPUT_DIR / "id_complaints_company_yearly.csv"
        df.write_parquet(cy_pq)
        df.write_csv(cy_csv)
        log(f"Wrote {cy_pq.name} ({len(df):,} rows)", logf)

        # ---- Output 2: per-(year × line) aggregate ----
        yearly = (
            df.group_by(["year", "line"])
            .agg(
                pl.col("complaints").sum().alias("total_complaints"),
                pl.len().alias("n_companies"),
                pl.col("complaint_index").drop_nulls().median().alias("median_index"),
                pl.col("market_share").sum().alias("market_share_covered"),
                pl.col("premium").sum().alias("total_premium"),
            )
            .sort(["year", "line"])
        )
        y_pq = OUTPUT_DIR / "id_complaints_yearly.parquet"
        y_csv = OUTPUT_DIR / "id_complaints_yearly.csv"
        yearly.write_parquet(y_pq)
        yearly.write_csv(y_csv)
        log(f"Wrote {y_pq.name} ({len(yearly):,} rows)", logf)

        log(f"\nYears: {sorted(df['year'].unique().to_list())}", logf)
        log(f"Lines: {sorted(df['line'].unique().to_list())}", logf)
        with pl.Config(tbl_rows=20, fmt_float="full"):
            log(f"\nYearly aggregate:\n{yearly}", logf)

        log(f"=== run completed {datetime.now(timezone.utc).isoformat(timespec='seconds')} ===", logf)
    return 0


if __name__ == "__main__":
    sys.exit(main())
