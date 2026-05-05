"""Parse every KID Complaint Index Report PDF into a single per-(year, line,
company) parquet.

Reads from `ks_kid/interim/files/{year}.pdf`. Writes to
`ks_kid/output/ks_complaints_company_yearly.parquet` plus aggregates.

KS PDFs come in two structural variants:
  • 2020–2022: "Cocode" header, 3 trailing complaint-index columns
    (current year + 2 prior years).
  • 2023–2024: "NAIC Code" header, 2 trailing complaint-index columns
    (current year + 1 prior year).

The current-year index is always the first of the trailing index values.
The lines covered also vary year-to-year (Auto + A&H/Health is constant;
Homeowners/Renters, Individual Life, Annuity, Long-Term Care add or rename
between years). We enumerate every "INDEXES BY LINE: X" / "Indexes by
line: X" header and parse the rows that follow it on the same page.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import polars as pl

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INTERIM_DIR = PROJECT_ROOT / "ks_kid" / "interim"
FILES_DIR = INTERIM_DIR / "files"
MANIFEST_PATH = INTERIM_DIR / "manifest.json"
OUTPUT_DIR = PROJECT_ROOT / "ks_kid" / "output"
LOG_PATH = OUTPUT_DIR / "run_log.txt"

# Match a section header like "Indexes by line: Automobile" or
# "INDEXES BY LINE: HOMEOWNERS & RENTERS". Restrict the label to letters,
# spaces, '&' and '-' to avoid matching the multi-line "Indexes by line:
# Automobile | Accident & Health 05" entries in the table of contents.
LINE_HEADER_RE = re.compile(
    r"^\s*Indexes\s+by\s+line:\s*(?P<line_label>[A-Za-z &\-]+?)\s*$",
    re.IGNORECASE,
)

# Each data row: COCODE Company Name MARKET_SHARE% COMPLAINTS INDEX [INDEX [INDEX]]
# Index values: float, "0.00", or "-" (no data prior year).
DATA_ROW_RE = re.compile(
    r"^\s*"
    r"(?P<cocode>\d{4,5})\s+"
    r"(?P<name>.+?)\s+"
    r"(?P<market_share>\d+(?:\.\d+)?%)\s+"
    r"(?P<complaints>\d+)\s+"
    r"(?P<index1>[\d.]+|-)\s*"
    r"(?:(?P<index2>[\d.]+|-)\s*)?"
    r"(?:(?P<index3>[\d.]+|-)\s*)?"
    r"$"
)

# Map raw KID line labels → canonical line slug.
LINE_NORMALIZE = {
    "automobile": "auto",
    # KID renamed "Accident & Health" → "Health" between 2022 and 2023.
    # Both refer to the same line; we map them to the same slug.
    "accident & health": "health",
    "health": "health",
    "homeowners": "homeowners",
    "homeowners & renters": "homeowners",
    "individual life": "life",
    "life": "life",
    "individual annuity": "annuity",
    "annuity": "annuity",
    "long-term care": "long_term_care",
    "long-term care insurance": "long_term_care",
}


def log(msg: str, fh) -> None:
    print(msg)
    fh.write(msg + "\n")


def parse_index(s: str | None) -> float | None:
    if s is None:
        return None
    s = s.strip()
    if not s or s == "-":
        return None
    return float(s)


def parse_market_share(s: str) -> float | None:
    if s is None:
        return None
    s = s.strip().rstrip("%")
    if not s:
        return None
    return float(s) / 100.0


def parse_pdf(path: Path, year: int) -> tuple[list[dict], list[str]]:
    """Walk every page; track the current 'Indexes by line: X' header; parse
    any data rows that follow on the same page."""
    import pdfplumber

    rows: list[dict] = []
    skipped: list[str] = []

    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            current_line: str | None = None
            for raw in text.splitlines():
                line_text = raw.strip()
                if not line_text:
                    continue

                # New "Indexes by line: X" section?
                m = LINE_HEADER_RE.match(line_text)
                if m:
                    label = m.group("line_label").strip().lower()
                    line_slug = LINE_NORMALIZE.get(label)
                    if line_slug is None:
                        # Unknown line label → fail loud rather than silently
                        # bucket. Recovery: add the label to LINE_NORMALIZE.
                        raise RuntimeError(
                            f"Unknown KID line label '{label}' in {path.name}; "
                            f"add to LINE_NORMALIZE in 02_parse.py"
                        )
                    current_line = line_slug
                    continue

                if current_line is None:
                    # Pre-table content (cover, TOC, narrative). Skip silently.
                    continue

                # Header rows for the table itself.
                if line_text.startswith("Cocode") or line_text.startswith("NAIC"):
                    continue
                if line_text.startswith("Index Index Index"):
                    continue
                if line_text.startswith("Index Index"):
                    continue
                if line_text.startswith("Code"):
                    continue
                # Continuation header lines split across two physical lines:
                # "Cocode Company Name 2020 Market Share 2020 Complaints" and
                # "Index Index Index" or "2020 Complaint 2019 Complaint 2018 Complaint".
                if "Complaint Index" in line_text and not DATA_ROW_RE.match(line_text):
                    continue
                if line_text.lower().startswith("company name"):
                    continue

                # Trailing footer note per table.
                if line_text.startswith("% of total market share"):
                    continue

                m = DATA_ROW_RE.match(line_text)
                if not m:
                    # Not a data row — could be wrapped narrative or a row
                    # that overflowed onto two lines. Skip but keep for log.
                    skipped.append(f"({current_line}) {line_text}")
                    continue

                # Some 2024 rows have a stray trailing 'vvv' or other glyph
                # appended; normalize the company name by stripping that.
                name = m.group("name").strip()
                # Remove an 'Incorporated' that wraps oddly.
                rows.append({
                    "year": year,
                    "line": current_line,
                    "naic_code": m.group("cocode"),
                    "company_name": name,
                    "market_share": parse_market_share(m.group("market_share")),
                    "complaints": int(m.group("complaints")),
                    "complaint_index": parse_index(m.group("index1")),
                    "complaint_index_prior_1": parse_index(m.group("index2")),
                    "complaint_index_prior_2": parse_index(m.group("index3")),
                    "source_file": path.name,
                })
    return rows, skipped


def main() -> int:
    if not MANIFEST_PATH.exists():
        print(f"ERROR: {MANIFEST_PATH} not found. Run 01_download.py first.", file=sys.stderr)
        return 1
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    manifest = json.loads(MANIFEST_PATH.read_text())
    files = manifest["files"]

    with LOG_PATH.open("a") as logf:
        log(f"\n=== run started {datetime.now(timezone.utc).isoformat(timespec='seconds')} ===", logf)
        log(f"Parsing {len(files)} source files", logf)

        all_rows: list[dict] = []
        for f in files:
            path = FILES_DIR / f["filename"]
            year = f["year"]
            try:
                rows, skipped = parse_pdf(path, year)
            except Exception as e:
                log(f"  HARD FAILURE parsing {path.name}: {e}", logf)
                return 3
            all_rows.extend(rows)
            log(f"  {path.name}: {len(rows)} rows  ({len(skipped)} skipped)", logf)
            if skipped and len(skipped) < 8:
                for s in skipped:
                    log(f"      skip: {s[:140]}", logf)

        if not all_rows:
            log("HARD FAILURE: no rows parsed", logf)
            return 4

        df = pl.DataFrame(all_rows, schema={
            "year": pl.Int32,
            "line": pl.String,
            "naic_code": pl.String,
            "company_name": pl.String,
            "market_share": pl.Float64,
            "complaints": pl.Int64,
            "complaint_index": pl.Float64,
            "complaint_index_prior_1": pl.Float64,
            "complaint_index_prior_2": pl.Float64,
            "source_file": pl.String,
        })

        # Sanity stats.
        idx_stats = df.select(
            pl.col("complaint_index").drop_nulls().median().alias("median"),
            pl.col("complaint_index").drop_nulls().mean().alias("mean"),
            pl.col("complaint_index").drop_nulls().min().alias("min"),
            pl.col("complaint_index").drop_nulls().max().alias("max"),
            pl.col("complaint_index").is_null().sum().alias("n_null"),
            pl.col("complaint_index").is_not_null().sum().alias("n_present"),
        )
        log(f"\nComplaint-index stats:\n{idx_stats}", logf)

        # ---- Output 1: per-company per-year per-line ----
        per_company = df.sort(["year", "line", "company_name"])
        cy_pq = OUTPUT_DIR / "ks_complaints_company_yearly.parquet"
        cy_csv = OUTPUT_DIR / "ks_complaints_company_yearly.csv"
        per_company.write_parquet(cy_pq)
        per_company.write_csv(cy_csv)
        log(f"Wrote {cy_pq.name} ({len(per_company):,} rows)", logf)

        # ---- Output 2: per-(year × line) aggregate ----
        yearly = (
            df.group_by(["year", "line"])
            .agg(
                pl.col("complaints").sum().alias("total_complaints"),
                pl.len().alias("n_companies"),
                pl.col("complaint_index").drop_nulls().median().alias("median_index"),
                pl.col("market_share").sum().alias("market_share_covered"),
            )
            .sort(["year", "line"])
        )
        y_pq = OUTPUT_DIR / "ks_complaints_yearly.parquet"
        y_csv = OUTPUT_DIR / "ks_complaints_yearly.csv"
        yearly.write_parquet(y_pq)
        yearly.write_csv(y_csv)
        log(f"Wrote {y_pq.name} ({len(yearly):,} rows)", logf)

        log(f"\nDistinct (year × line) slices: {len(yearly)}", logf)
        log(f"Years: {sorted(df['year'].unique().to_list())}", logf)
        log(f"Lines: {sorted(df['line'].unique().to_list())}", logf)
        with pl.Config(tbl_rows=40, fmt_float="full"):
            log(f"\nYearly aggregate:\n{yearly}", logf)

        log(f"=== run completed {datetime.now(timezone.utc).isoformat(timespec='seconds')} ===", logf)
    return 0


if __name__ == "__main__":
    sys.exit(main())
