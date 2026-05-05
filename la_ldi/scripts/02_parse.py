"""Parse the 40 Louisiana LDI Consumer Complaint Data Report PDFs into a tidy
per-company per-line per-year parquet plus a per-line per-year aggregate.

Inputs (from 01_download.py):
  la_ldi/interim/files/<line_slug>_<year>.pdf  (40 files: 4 lines × 10 years)
  la_ldi/interim/manifest.json

Outputs:
  la_ldi/output/la_complaints_company_yearly.{parquet,csv}
    Per-company per-line per-year. Columns:
    state, year, line, company_name_raw, premium_written, market_share,
    complaints, complaint_index, source_pdf.

  la_ldi/output/la_complaints_yearly.{parquet,csv}
    Per-line per-year aggregate. Columns:
    state, year, line, n_companies, total_complaints, total_premium.

  la_ldi/output/run_log.txt   appended.

Each LDI PDF lays out:
  Line 1-3: header (LDI / Tim Temple / Commissioner)
  Line 4:   "Consumer Complaint Data Report YYYY"
  Line 5:   "Displayed by Premium Written"
  Line 6:   <Line of Insurance>
  Line 7:   "Company Name Premium Written Market Share Number of Complaints Complaint Index"
  Lines 8+: <company rows>
  Final:   "Subtotal for Selection: $X 100.00% N <blank>"
           "Market Total: $X 100.00% N <blank>"

Each company row has the shape:
  <company name (multi-word)> <premium ($, possibly negative)> <share %> <complaints int> <index float>
"""
from __future__ import annotations

import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pdfplumber
import polars as pl

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INTERIM_DIR = PROJECT_ROOT / "la_ldi" / "interim" / "files"
MANIFEST_PATH = PROJECT_ROOT / "la_ldi" / "interim" / "manifest.json"
OUTPUT_DIR = PROJECT_ROOT / "la_ldi" / "output"
LOG_PATH = OUTPUT_DIR / "run_log.txt"

# Regex anchored to the END of a line. Premium can be negative
# accounting-style with parentheses ("($232.00)"), or a regular signed
# number ("-$50,594.00"), or a positive value ("$1,730,400,565").
ROW_RE = re.compile(
    r"^(?P<name>.+?)\s+"
    r"(?P<premium>-?\(?\$?-?[\d,]+(?:\.\d+)?\)?)\s+"
    r"(?P<share>-?[\d.]+)%\s+"
    r"(?P<complaints>\d+)\s+"
    r"(?P<index>-?[\d.]+)\s*$"
)
SUMMARY_PREFIXES = ("Subtotal for Selection:", "Market Total:")


def parse_premium(s: str) -> float | None:
    """Handle accounting-style negatives like '($232.00)' and signed values."""
    s = s.strip()
    if not s:
        return None
    neg = False
    if s.startswith("(") and s.endswith(")"):
        neg = True
        s = s[1:-1]
    s = s.replace("$", "").replace(",", "").strip()
    if not s:
        return None
    try:
        v = float(s)
    except ValueError:
        return None
    return -v if neg else v


def parse_one(path: Path) -> tuple[str, int, list[dict]]:
    """Return (line_label, year, rows) parsed from a single LDI report PDF."""
    rows: list[dict] = []
    line_label = None
    year = None
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            for raw in text.split("\n"):
                ln = raw.strip()
                if not ln:
                    continue
                # Capture the metadata from the first occurrence
                if line_label is None:
                    if ln in {
                        "Auto - Individual Private Passenger",
                        "Homeowners",
                        "Life & Annuity - Individual Life",
                        "Accident & Health - Individual",
                    }:
                        line_label = ln
                if year is None:
                    m = re.match(r"Consumer Complaint Data Report (20\d{2})", ln)
                    if m:
                        year = int(m.group(1))
                # Skip header rows and summary rows
                if ln.startswith("Company Name "):
                    continue
                if any(ln.startswith(p) for p in SUMMARY_PREFIXES):
                    continue
                if ln in {"Louisiana Department of Insurance", "Tim Temple", "Commissioner"}:
                    continue
                if ln.startswith("Consumer Complaint Data Report"):
                    continue
                if ln.startswith("Displayed by Premium Written"):
                    continue
                if line_label and ln == line_label:
                    continue

                m = ROW_RE.match(ln)
                if not m:
                    continue
                rows.append({
                    "company_name_raw": m["name"].strip(),
                    "premium_written": parse_premium(m["premium"]),
                    "market_share": float(m["share"]) / 100.0,
                    "complaints": int(m["complaints"]),
                    "complaint_index": float(m["index"]),
                })
    return line_label or "unknown", year or 0, rows


# Map LDI line label -> our canonical line slug.
LINE_TO_CANONICAL = {
    "Auto - Individual Private Passenger": "auto",
    "Homeowners": "homeowners",
    "Life & Annuity - Individual Life": "life",
    "Accident & Health - Individual": "accident_health",
}


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST_PATH.read_text())
    log = [f"\n### {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%MZ')} — parse run"]

    company_rows: list[dict] = []
    yearly_rows: list[dict] = []
    for entry in manifest["files"]:
        path = INTERIM_DIR / entry["filename"]
        label, parsed_year, rows = parse_one(path)
        canonical = LINE_TO_CANONICAL.get(label, "unknown")
        # Cross-check label vs filename
        if canonical != entry["line_canonical"]:
            log.append(f"  WARN: {entry['filename']} parsed line {label!r} (canonical {canonical}) "
                       f"but manifest says {entry['line_canonical']}")
        if parsed_year != entry["year"]:
            log.append(f"  WARN: {entry['filename']} parsed year {parsed_year} but manifest says {entry['year']}")

        for r in rows:
            company_rows.append({
                "state": "LA",
                "year": entry["year"],
                "line": entry["line_canonical"],
                "company_name_raw": r["company_name_raw"],
                "premium_written": r["premium_written"],
                "market_share": r["market_share"],
                "complaints": r["complaints"],
                "complaint_index": r["complaint_index"],
                "source_pdf": entry["filename"],
            })
        # Per-line per-year aggregates derived from the parsed rows.
        n = len(rows)
        total_c = sum(r["complaints"] or 0 for r in rows)
        total_p = sum(r["premium_written"] for r in rows if r["premium_written"] is not None)
        yearly_rows.append({
            "state": "LA",
            "year": entry["year"],
            "line": entry["line_canonical"],
            "n_companies": n,
            "total_complaints": total_c,
            "total_premium": total_p,
        })
        log.append(f"  {entry['filename']}: {n} companies, {total_c} complaints, ${total_p:,.0f} premium")

    company = pl.DataFrame(company_rows).select([
        "state", "year", "line", "company_name_raw",
        "premium_written", "market_share", "complaints", "complaint_index", "source_pdf",
    ]).sort(["year", "line", "company_name_raw"])
    company.write_parquet(OUTPUT_DIR / "la_complaints_company_yearly.parquet")
    company.write_csv(OUTPUT_DIR / "la_complaints_company_yearly.csv")
    log.append(f"  wrote la_complaints_company_yearly: {company.height} rows")

    yearly = pl.DataFrame(yearly_rows).select([
        "state", "year", "line", "n_companies", "total_complaints", "total_premium",
    ]).sort(["line", "year"])
    yearly.write_parquet(OUTPUT_DIR / "la_complaints_yearly.parquet")
    yearly.write_csv(OUTPUT_DIR / "la_complaints_yearly.csv")
    log.append(f"  wrote la_complaints_yearly: {yearly.height} rows")

    with LOG_PATH.open("a") as f:
        f.write("\n".join(log) + "\n")
    print("\n".join(log))


if __name__ == "__main__":
    main()
