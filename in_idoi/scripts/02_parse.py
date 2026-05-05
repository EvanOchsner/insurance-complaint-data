"""Parse every IDOI Company Complaint Index file (PDF or XLSX) into a single
per-(year, line, company) parquet.

Reads from `in_idoi/interim/files/{year}_{line}.{pdf,xlsx}`. Writes to
`in_idoi/output/in_complaints_company_yearly.parquet` plus aggregates.

Per-row parquet schema:
  year (i32) | line (str) | naic_code (str) | company_name (str) |
  premium (f64, nullable) | complaints (i64) | complaint_index (f64, nullable) |
  source_file (str)

Premium is nullable because IDOI tags small-volume rows with "None" or "DNC".
Complaint index is nullable when IDOI prints "DNC" (Did Not Compute, applied
when the premium denominator is too small to yield a meaningful index).
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import polars as pl

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INTERIM_DIR = PROJECT_ROOT / "in_idoi" / "interim"
FILES_DIR = INTERIM_DIR / "files"
MANIFEST_PATH = INTERIM_DIR / "manifest.json"
OUTPUT_DIR = PROJECT_ROOT / "in_idoi" / "output"
LOG_PATH = OUTPUT_DIR / "run_log.txt"

# Each PDF row reads as: [optional row#] NAIC# Company Name Premium Complaints Index
# Premium may be a comma-separated integer or "None"; index may be a float or "DNC".
PDF_ROW_PATTERN = re.compile(
    r"^\s*"
    r"(?:(?P<rowno>\d{1,3})\s+)?"
    r"(?P<naic>\d{4,5})\s+"
    r"(?P<name>.+?)\s+"
    r"\$?(?P<premium>[\d,]+|None)\s+"
    r"(?P<complaints>\d+)\s+"
    r"(?P<index>[\d.]+|DNC)\s*$"
)

# Lines that look like headers/footers and should not feed the row parser.
PDF_SKIP_PREFIXES = (
    "NAIC",
    "Number of Complaint",
    "Company Name",
    "Indiana Department of Insurance",
    "https://",
    "www.",
    "Page ",
)


def log(msg: str, fh) -> None:
    print(msg)
    fh.write(msg + "\n")


def parse_premium(s: str) -> float | None:
    if s is None:
        return None
    s = s.strip()
    if not s or s.lower() == "none":
        return None
    return float(s.replace(",", ""))


def parse_index(s: str) -> float | None:
    if s is None:
        return None
    s = s.strip()
    if not s or s.upper() == "DNC":
        return None
    return float(s)


def parse_pdf(path: Path, year: int, line: str) -> list[dict]:
    """Run the PDF row regex over every text line of every page."""
    import pdfplumber  # local import keeps script importable without pdfplumber

    rows: list[dict] = []
    skipped: list[str] = []
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            text = page.extract_text() or ""
            for raw_line in text.splitlines():
                txt = raw_line.strip()
                if not txt:
                    continue
                if any(txt.startswith(p) for p in PDF_SKIP_PREFIXES):
                    continue
                # Year/line title lines like "2024 Auto" or "Auto 2024 Complaint Index".
                if re.match(r"^\d{4}\s+\w+\s*$", txt):
                    continue
                if re.match(r"^[A-Za-z &/\-]+$", txt):
                    # pure-alpha line (header continuation, banner)
                    continue
                m = PDF_ROW_PATTERN.match(txt)
                if not m:
                    skipped.append(txt)
                    continue
                rows.append({
                    "year": year,
                    "line": line,
                    "naic_code": m.group("naic"),
                    "company_name": m.group("name").strip(),
                    "premium": parse_premium(m.group("premium")),
                    "complaints": int(m.group("complaints")),
                    "complaint_index": parse_index(m.group("index")),
                    "source_file": path.name,
                })
    return rows, skipped


def parse_xlsx(path: Path, year: int, line: str) -> list[dict]:
    """Parse the 2014 IDOI XLSX file. Single worksheet; columns roughly:
    [optional row#] NAIC | Company Name | Premium | Complaints | Index."""
    import openpyxl

    wb = openpyxl.load_workbook(path, data_only=True, read_only=True)
    ws = wb.active
    rows: list[dict] = []
    skipped: list[str] = []
    for r in ws.iter_rows(values_only=True):
        # Skip empty rows.
        if all(c is None or (isinstance(c, str) and not c.strip()) for c in r):
            continue
        cells = [c for c in r if c is not None and not (isinstance(c, str) and not c.strip())]
        # Identify the trailing 3 numeric-ish cells (premium, complaints, index)
        # and walk back from the right.
        if len(cells) < 4:
            skipped.append(repr(cells))
            continue
        # The last 3 cells are: premium, complaints, index.
        try:
            premium_raw = cells[-3]
            complaints_raw = cells[-2]
            index_raw = cells[-1]

            if isinstance(premium_raw, (int, float)):
                premium = float(premium_raw)
            elif isinstance(premium_raw, str):
                premium = parse_premium(premium_raw)
            else:
                premium = None

            if isinstance(complaints_raw, (int, float)):
                complaints = int(complaints_raw)
            elif isinstance(complaints_raw, str) and complaints_raw.strip().isdigit():
                complaints = int(complaints_raw.strip())
            else:
                # Header row, skip.
                skipped.append(repr(cells))
                continue

            if isinstance(index_raw, (int, float)):
                idx = float(index_raw)
            elif isinstance(index_raw, str):
                idx = parse_index(index_raw)
            else:
                idx = None
        except (ValueError, TypeError):
            skipped.append(repr(cells))
            continue

        # Before premium: company name; before that NAIC; before that optional row #.
        head = cells[:-3]
        if not head:
            skipped.append(repr(cells))
            continue

        # NAIC code is the last numeric-only cell in head; everything after is name.
        naic_idx = None
        for i in range(len(head) - 1, -1, -1):
            cell = head[i]
            if isinstance(cell, int) and 1000 <= cell <= 99999:
                naic_idx = i
                break
            if isinstance(cell, str) and cell.strip().isdigit() and 4 <= len(cell.strip()) <= 5:
                naic_idx = i
                break
        if naic_idx is None:
            skipped.append(repr(cells))
            continue

        naic = str(head[naic_idx]).strip()
        name_parts = [str(c).strip() for c in head[naic_idx + 1:]]
        name = " ".join(p for p in name_parts if p)
        if not name:
            skipped.append(repr(cells))
            continue

        rows.append({
            "year": year,
            "line": line,
            "naic_code": naic,
            "company_name": name,
            "premium": premium,
            "complaints": complaints,
            "complaint_index": idx,
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
        per_file_counts: list[tuple[str, int, int]] = []

        for f in files:
            path = FILES_DIR / f["filename"]
            year = f["year"]
            line = f["line"]
            ext = f["ext"]
            try:
                if ext == "pdf":
                    rows, skipped = parse_pdf(path, year, line)
                elif ext == "xlsx":
                    rows, skipped = parse_xlsx(path, year, line)
                else:
                    log(f"  {path.name}: unknown ext '{ext}', skipped", logf)
                    continue
            except Exception as e:
                log(f"  HARD FAILURE parsing {path.name}: {e}", logf)
                return 3

            all_rows.extend(rows)
            per_file_counts.append((path.name, len(rows), len(skipped)))
            n_skipped_str = f"  ({len(skipped)} skipped)" if skipped else ""
            log(f"  {path.name}: {len(rows)} rows{n_skipped_str}", logf)
            if skipped and len(skipped) < 8:
                for s in skipped:
                    log(f"      skip: {s[:120]}", logf)

        if not all_rows:
            log("HARD FAILURE: no rows parsed", logf)
            return 4

        df = pl.DataFrame(all_rows, schema={
            "year": pl.Int32,
            "line": pl.String,
            "naic_code": pl.String,
            "company_name": pl.String,
            "premium": pl.Float64,
            "complaints": pl.Int64,
            "complaint_index": pl.Float64,
            "source_file": pl.String,
        })

        # Sanity: complaint_index should cluster around 1.0 with a long right tail.
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
        cy_pq = OUTPUT_DIR / "in_complaints_company_yearly.parquet"
        cy_csv = OUTPUT_DIR / "in_complaints_company_yearly.csv"
        per_company.write_parquet(cy_pq)
        per_company.write_csv(cy_csv)
        log(f"Wrote {cy_pq.name} ({len(per_company):,} rows)", logf)

        # ---- Output 2: per-year per-line aggregate ----
        # Sums premium-weighted-and-unweighted complaint counts; emits how
        # many companies appeared in each (year, line) slice.
        yearly = (
            df.group_by(["year", "line"])
            .agg(
                pl.col("complaints").sum().alias("total_complaints"),
                pl.col("premium").sum().alias("total_premium"),
                pl.len().alias("n_companies"),
                pl.col("complaint_index").drop_nulls().median().alias("median_index"),
            )
            .sort(["year", "line"])
        )
        y_pq = OUTPUT_DIR / "in_complaints_yearly.parquet"
        y_csv = OUTPUT_DIR / "in_complaints_yearly.csv"
        yearly.write_parquet(y_pq)
        yearly.write_csv(y_csv)
        log(f"Wrote {y_pq.name} ({len(yearly):,} rows)", logf)

        # ---- Soft sanity ----
        log(f"\nDistinct (year × line) slices: {len(yearly)}", logf)
        log(f"Years: {sorted(df['year'].unique().to_list())}", logf)
        log(f"Lines: {sorted(df['line'].unique().to_list())}", logf)
        with pl.Config(tbl_rows=20, fmt_float="full"):
            log(f"\nYearly aggregate (head):\n{yearly}", logf)

        log(f"=== run completed {datetime.now(timezone.utc).isoformat(timespec='seconds')} ===", logf)
    return 0


if __name__ == "__main__":
    sys.exit(main())
