"""Parse Table II ("Complaints Filed By Type of Insurance") from each WIR.

Each report covers two data years (the report-year and the prior year). The
parser extracts both columns from each report; for each (data_year, line),
the value from the most recent report containing that data_year is the
canonical value (since the OCI sometimes revises prior-year numbers in
later reports).

Output: wi_oci/output/wi_complaints_yearly.{parquet,csv}
        — one row per (data_year, line) with complaint count.

The 13 expected lines (sub-line + total rows from Table II):
  Group Accident and Health
  Individual Accident and Health
  Medicare Supplement
  Long-Term Care
  Total Accident and Health
  Automobile
  Homeowners, Tenants, Farmowners
  Fire, Allied Lines, Other Property
  General Liability/Liability
  Worker's Compensation
  All Other Lines
  Total Property and Casualty
  Life, Including Credit and Annuities
  Grand Total
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import polars as pl

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INTERIM_DIR = PROJECT_ROOT / "wi_oci" / "interim"
FILES_DIR = INTERIM_DIR / "files"
MANIFEST_PATH = INTERIM_DIR / "manifest.json"
OUTPUT_DIR = PROJECT_ROOT / "wi_oci" / "output"
LOG_PATH = OUTPUT_DIR / "run_log.txt"

# Map raw labels (from PDF text) to canonical line slugs. Apostrophes and
# punctuation in source vary slightly; normalize on lowercase + strip.
LINE_NORMALIZE = {
    "group accident and health":           "group_health",
    "individual accident and health":      "individual_health",
    "medicare supplement":                 "medicare_supplement",
    "long-term care":                      "long_term_care",
    "total accident and health":           "total_accident_health",
    "automobile":                          "auto",
    "homeowners, tenants, farmowners":     "homeowners_tenants_farmowners",
    "fire, allied lines, other property":  "fire_allied_other_property",
    "general liability/liability":         "general_liability",
    "worker's compensation":               "workers_comp",
    "worker’s compensation":               "workers_comp",  # curly apostrophe
    "all other lines":                     "other_pc",
    "total property and casualty":         "total_property_casualty",
    "life, including credit and annuities": "life_credit_annuities",
    "grand total":                         "grand_total",
}

# Row regex: a label followed by exactly two integers (with optional thousands
# separator). The label is everything up to the first "<digit>" boundary.
ROW_RE = re.compile(
    r"^\s*(?P<label>.+?)\s+(?P<v1>[\d,]+)\s+(?P<v2>[\d,]+)\s*$"
)


def log(msg: str, fh) -> None:
    print(msg)
    fh.write(msg + "\n")


def parse_int(s: str) -> int:
    return int(s.replace(",", ""))


def find_table_ii_text(path: Path) -> str:
    """Locate the page with Table II header and return its full text plus the
    next page (in case the table wraps). The 2021 PDF has a stray space
    ('Fil ed' instead of 'Filed') so we match a looser pattern."""
    import pdfplumber
    pat = re.compile(r"Table\s+II\s*[-–—]\s*Complaints\s+Fil\s*ed\s+By\s+Type\s+of\s+Insurance",
                     re.IGNORECASE)
    with pdfplumber.open(path) as pdf:
        for i, p in enumerate(pdf.pages):
            t = p.extract_text() or ""
            if pat.search(t):
                next_t = pdf.pages[i + 1].extract_text() if i + 1 < len(pdf.pages) else ""
                return t + "\n" + (next_t or "")
    raise RuntimeError(f"{path.name}: Table II header not found")


def parse_table_ii(report_year: int, full_text: str, logf) -> list[dict]:
    """Extract per-line counts for both years shown in the table."""
    # Identify the two year columns by scanning the header. Lines like:
    #   "Type of Insurance 2022 2023" or "Accident and Health 2019 2020"
    # contain a 4-digit year pair we can use.
    years_seen: list[int] = []
    for m in re.finditer(r"\b(20\d{2})\s+(20\d{2})\b", full_text):
        y1, y2 = int(m.group(1)), int(m.group(2))
        if y2 == y1 + 1:
            years_seen = [y1, y2]
            break
    if not years_seen:
        # Fallback: the two columns are report_year - 1 and report_year.
        years_seen = [report_year - 1, report_year]
    log(f"  {report_year}: data years inferred as {years_seen}", logf)

    rows: list[dict] = []
    found_labels: set[str] = set()
    for raw in full_text.splitlines():
        ln = raw.strip()
        m = ROW_RE.match(ln)
        if not m:
            continue
        label = m.group("label").strip().lower()
        # Strip a year (e.g. line "Property and Casualty 2021 2022" — header).
        if re.match(r"^[a-z &/\-,'’]+\s+20\d{2}$", label):
            continue
        line_slug = LINE_NORMALIZE.get(label)
        if line_slug is None:
            # Skip unrecognized rows. They may be irrelevant table II surroundings.
            continue
        if line_slug in found_labels:
            # Duplicate match (table II copy elsewhere) — keep first occurrence.
            continue
        found_labels.add(line_slug)
        v1 = parse_int(m.group("v1"))
        v2 = parse_int(m.group("v2"))
        rows.append({
            "data_year": years_seen[0],
            "line": line_slug,
            "complaints": v1,
            "report_year": report_year,
            "source_file": f"WIR_{report_year}.pdf",
        })
        rows.append({
            "data_year": years_seen[1],
            "line": line_slug,
            "complaints": v2,
            "report_year": report_year,
            "source_file": f"WIR_{report_year}.pdf",
        })

    log(f"  {report_year}: parsed {len(rows)} (data_year × line) rows from Table II", logf)
    return rows


def main() -> int:
    if not MANIFEST_PATH.exists():
        print(f"ERROR: {MANIFEST_PATH} not found. Run 01_download.py first.", file=sys.stderr)
        return 1
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    manifest = json.loads(MANIFEST_PATH.read_text())
    files = manifest["files"]

    with LOG_PATH.open("a") as logf:
        log(f"\n=== run started {datetime.now(timezone.utc).isoformat(timespec='seconds')} ===", logf)

        all_rows: list[dict] = []
        for f in files:
            report_year = f["report_year"]
            path = FILES_DIR / f["filename"]
            try:
                full_text = find_table_ii_text(path)
                rows = parse_table_ii(report_year, full_text, logf)
            except Exception as e:
                log(f"  HARD FAILURE on {path.name}: {e}", logf)
                return 3
            all_rows.extend(rows)

        if not all_rows:
            log("HARD FAILURE: no rows parsed", logf)
            return 4

        df = pl.DataFrame(all_rows, schema={
            "data_year": pl.Int32,
            "line": pl.String,
            "complaints": pl.Int64,
            "report_year": pl.Int32,
            "source_file": pl.String,
        })

        # Canonicalize: for each (data_year, line), keep the row from the
        # latest report_year that includes it. OCI occasionally revises
        # prior-year values in later reports.
        canonical = (
            df.sort("report_year", descending=True)
              .unique(subset=["data_year", "line"], keep="first")
              .sort(["data_year", "line"])
        )

        out_pq = OUTPUT_DIR / "wi_complaints_yearly.parquet"
        out_csv = OUTPUT_DIR / "wi_complaints_yearly.csv"
        canonical.write_parquet(out_pq)
        canonical.write_csv(out_csv)
        log(f"Wrote {out_pq.name} ({len(canonical):,} rows; canonical / latest-revision)", logf)

        # Also write the full multi-version frame for audit.
        full_pq = OUTPUT_DIR / "wi_complaints_all_versions.parquet"
        full_csv = OUTPUT_DIR / "wi_complaints_all_versions.csv"
        df.sort(["data_year", "line", "report_year"]).write_parquet(full_pq)
        df.sort(["data_year", "line", "report_year"]).write_csv(full_csv)
        log(f"Wrote {full_pq.name} ({len(df):,} rows; all reports, for audit)", logf)

        log(f"\nData years: {sorted(canonical['data_year'].unique().to_list())}", logf)
        log(f"Lines: {sorted(canonical['line'].unique().to_list())}", logf)
        with pl.Config(tbl_rows=80, fmt_float="full"):
            log(f"\nGrand totals + Total P&C + Total A&H by year:\n"
                + str(canonical.filter(pl.col("line").is_in([
                    "grand_total", "total_property_casualty", "total_accident_health",
                    "life_credit_annuities"
                ])).sort(["line", "data_year"])), logf)

        log(f"=== run completed {datetime.now(timezone.utc).isoformat(timespec='seconds')} ===", logf)
    return 0


if __name__ == "__main__":
    sys.exit(main())
