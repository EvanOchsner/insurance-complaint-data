"""Parse the 42 Oregon DFR Insurance Complaint Reports into tidy parquet.

Inputs (from 01_download.py):
  or_dfr/interim/files/<line>_<year>.pdf  (42 files: 6 lines × 7 years)
  or_dfr/interim/manifest.json

Outputs:
  or_dfr/output/or_complaints_company_yearly.{parquet,csv}
    Per-company per-line per-year. Columns:
    state, year, line, company_name_raw, premium_written, total_complaints,
    confirmed_complaints, complaint_index, source_pdf.

  or_dfr/output/or_complaints_yearly.{parquet,csv}
    Per-line per-year aggregate. Columns:
    state, year, line, n_companies, total_complaints, total_confirmed,
    total_premium.

  or_dfr/output/run_log.txt   appended.

Each OR PDF has rows of the form:
  <company name (multi-word)> <leading digit of premium> <rest of premium with commas> <total> <confirmed> <index>
The leading digit + rest split is a PDF-text-extraction artifact from
right-aligned numeric columns; the parser stitches them back together.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import pdfplumber
import polars as pl

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INTERIM_DIR = PROJECT_ROOT / "or_dfr" / "interim" / "files"
MANIFEST_PATH = PROJECT_ROOT / "or_dfr" / "interim" / "manifest.json"
OUTPUT_DIR = PROJECT_ROOT / "or_dfr" / "output"
LOG_PATH = OUTPUT_DIR / "run_log.txt"

# Row pattern: <name> [<prem_lead> ]<prem_main> <total_int> <conf_int> <index_float>
# The <prem_lead> single digit + space is a PDF-text-extraction artifact present
# in some years (2019, 2020, 2023, 2025) but absent in others (2024 — premium is
# rendered as a single token). Make the leading-digit segment optional so the
# regex handles both layouts.
ROW_RE = re.compile(
    r"^(?P<name>.+?)\s+"
    r"(?:(?P<prem_lead>-?\d)\s+)?"
    r"(?P<prem_main>[\d,]+)\s+"
    r"(?P<total>\d+)\s+"
    r"(?P<conf>\d+)\s+"
    r"(?P<index>-?[\d.]+)\s*$"
)
# Header / banner lines to skip
SKIP_PREFIXES = (
    "Companies Premium Complaints",
    "Companies premium Complaints",
    "Total Confirmed Complaint",
    "Auto Companies",
    "Annuities Companies",
    "Health Companies",
    "Homeowners Companies",
    "Life Companies",
    "LTC Companies",
    "Total: ",
    "Total ",
    "Grand Total",
)


def parse_premium(lead: str | None, main: str) -> int | None:
    """Stitch the split premium digits back together when present. lead is an
    optional single leading digit (split format); main is the remainder with
    comma separators (or the full premium in clean format)."""
    s = ((lead or "") + main).replace(",", "")
    if not s or s in {"-"}:
        return None
    try:
        return int(s)
    except ValueError:
        return None


def parse_one(path: Path) -> tuple[str | None, int | None, list[dict]]:
    line_label = None
    year = None
    rows: list[dict] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            for raw in text.split("\n"):
                ln = raw.strip()
                if not ln:
                    continue
                # Capture metadata (line label and year) from the top banner
                m = re.match(r"^(20\d{2})\s+Total\s+Confirmed\s+Complaint", ln)
                if m and year is None:
                    year = int(m.group(1))
                    continue
                m = re.match(r"^(Auto|Annuities|Health|Homeowners|Life|LTC)\s+Companies\s+Premium", ln)
                if m and line_label is None:
                    line_label = m.group(1)
                    continue
                # Skip headers / totals / banners
                if any(ln.startswith(p) for p in SKIP_PREFIXES):
                    continue
                # The data rows
                m = ROW_RE.match(ln)
                if not m:
                    continue
                rows.append({
                    "company_name_raw": m["name"].strip(),
                    "premium_written": parse_premium(m["prem_lead"], m["prem_main"]),
                    "total_complaints": int(m["total"]),
                    "confirmed_complaints": int(m["conf"]),
                    "complaint_index": float(m["index"]),
                })
    return line_label, year, rows


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST_PATH.read_text())
    log = [f"\n### {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%MZ')} — parse run"]

    company_rows: list[dict] = []
    yearly_rows: list[dict] = []
    for entry in manifest["files"]:
        path = INTERIM_DIR / entry["filename"]
        label, parsed_year, rows = parse_one(path)
        if parsed_year != entry["year"]:
            log.append(f"  WARN: {entry['filename']} parsed year {parsed_year} but manifest says {entry['year']}")

        n = len(rows)
        sum_total = sum(r["total_complaints"] for r in rows)
        sum_conf = sum(r["confirmed_complaints"] for r in rows)
        sum_prem = sum(r["premium_written"] for r in rows if r["premium_written"] is not None)

        for r in rows:
            company_rows.append({
                "state": "OR",
                "year": entry["year"],
                "line": entry["line_canonical"],
                "company_name_raw": r["company_name_raw"],
                "premium_written": r["premium_written"],
                "total_complaints": r["total_complaints"],
                "confirmed_complaints": r["confirmed_complaints"],
                "complaint_index": r["complaint_index"],
                "source_pdf": entry["filename"],
            })

        yearly_rows.append({
            "state": "OR",
            "year": entry["year"],
            "line": entry["line_canonical"],
            "n_companies": n,
            "total_complaints": sum_total,
            "total_confirmed": sum_conf,
            "total_premium": sum_prem,
        })
        log.append(f"  {entry['filename']}: {n} companies, {sum_total} complaints, "
                   f"{sum_conf} confirmed, ${sum_prem:,.0f} premium")

    company = pl.DataFrame(company_rows).select([
        "state", "year", "line", "company_name_raw",
        "premium_written", "total_complaints", "confirmed_complaints",
        "complaint_index", "source_pdf",
    ]).sort(["year", "line", "company_name_raw"])
    company.write_parquet(OUTPUT_DIR / "or_complaints_company_yearly.parquet")
    company.write_csv(OUTPUT_DIR / "or_complaints_company_yearly.csv")
    log.append(f"  wrote or_complaints_company_yearly: {company.height} rows")

    yearly = pl.DataFrame(yearly_rows).select([
        "state", "year", "line", "n_companies",
        "total_complaints", "total_confirmed", "total_premium",
    ]).sort(["line", "year"])
    yearly.write_parquet(OUTPUT_DIR / "or_complaints_yearly.parquet")
    yearly.write_csv(OUTPUT_DIR / "or_complaints_yearly.csv")
    log.append(f"  wrote or_complaints_yearly: {yearly.height} rows")

    with LOG_PATH.open("a") as f:
        f.write("\n".join(log) + "\n")
    print("\n".join(log))


if __name__ == "__main__":
    main()
