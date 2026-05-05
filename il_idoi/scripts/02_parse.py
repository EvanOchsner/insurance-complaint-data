"""Parse IL IDOI consolidated complaint-ratio PDFs into per-company per-line
per-year parquet outputs.

Two structural variants in the source:

  2018–2020 layout: per-page line subtitle ("YYYY Complaint Ratios - {Line}");
    table cols = `Cocode | Company Name | Direct Written Premium | Market
    Share | Closed Complaints | Complaint Share | Complaint to Market Share
    Ratio`. Ratio is share-of-share (NAIC standard, ~1.0 = parity).

  2023–2024 layout: per-section heading ("X COMPLAINTS BY COMPANY NAME");
    table cols = `Company Name | # Complaints | Earned Premium | Complaints
    per $1M EP | Underwriting | Marketing/Sales | Claims Handling |
    Policyholder Service`. Ratio is "complaints per $1M EP" — DIFFERENT
    UNIT from 2018–2020. The 4 reason-code columns are unique to this
    layout.

Output schema preserves both ratio types via a `ratio_type` column so
downstream consumers can reconcile.
"""
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import polars as pl

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INTERIM_DIR = PROJECT_ROOT / "il_idoi" / "interim"
FILES_DIR = INTERIM_DIR / "files"
MANIFEST_PATH = INTERIM_DIR / "manifest.json"
OUTPUT_DIR = PROJECT_ROOT / "il_idoi" / "output"
LOG_PATH = OUTPUT_DIR / "run_log.txt"

# Map raw line labels (case-insensitive) → canonical slug.
LINE_NORMALIZE = {
    "private passenger automobile": "auto",
    "private passenger auto": "auto",
    "auto": "auto",
    "homeowner's": "homeowners",
    "homeowner": "homeowners",
    "homeowners": "homeowners",
    "individual life": "life",
    "life": "life",
    "individual annuity": "annuity",
    "annuity": "annuity",
    "individual accident & health": "individual_health",
    "group accident & health": "group_health",
    "health maintenance organizations": "hmo",
    "hmo": "hmo",
    "health": "health",
}

# 2018–2020 row regex: Cocode | Company Name | Direct Written Premium |
# Market Share % | Complaints | Complaint Share % | Ratio (or N/A)
ROW_RE_OLD = re.compile(
    r"^\s*(?P<cocode>\d{4,5})\s+"
    r"(?P<name>.+?)\s+"
    r"\$(?P<premium>[\d,]+|0)\s+"
    r"(?P<mshare>\d+(?:\.\d+)?)%\s+"
    r"(?P<complaints>\d+)\s+"
    r"(?P<cshare>\d+(?:\.\d+)?)%\s+"
    r"(?P<ratio>[\d.]+|N/A)\s*$"
)

# 2019–2024 row regex: Company Name | Complaints | Earned Premium | Ratio
# (per $1M EP) | + variable trailing reason-code columns (4 in 2023–2024, 6
# in 2019–2020). We capture the first 3 numerics after the name and let the
# trailing reason codes ride along in `rest` (discarded — inconsistent
# across years isn't worth the parsing complexity for v1).
ROW_RE_NEW = re.compile(
    r"^\s*"
    r"(?P<name>.+?)\s+"
    r"(?P<complaints>\d+)\s+"
    # Premium is `$<digits>` for P&C lines (auto, homeowners) but plain
    # digits for Life (policies in force) and HMO (members). Optional `$`.
    r"\$?(?P<premium>[\d,]+|0)\s+"
    r"(?P<ratio>[\d.]+|N/A)"
    r"(?:\s+\d+)*\s*$"
)

# Old-layout per-page subtitle: "YYYY Complaint Ratios - {Line}"
HDR_RE_OLD = re.compile(r"^\d{4}\s+Complaint\s+Ratios\s+-\s+(?P<line>.+?)\s*$", re.IGNORECASE)
# New-layout section heading: "{LINE} COMPLAINTS BY COMPANY NAME"
HDR_RE_NEW = re.compile(r"^(?P<line>[A-Za-z &]+?)\s+COMPLAINTS\s+BY\s+COMPANY\s+NAME\s*$")


def log(msg: str, fh) -> None:
    print(msg)
    fh.write(msg + "\n")


def parse_premium(s: str | None) -> float | None:
    if s is None or s == "0":
        return None if s != "0" else 0.0
    return float(s.replace(",", ""))


def parse_ratio(s: str | None) -> float | None:
    if s is None or s.upper() == "N/A":
        return None
    return float(s)


def parse_old_layout(path: Path, year: int, logf) -> list[dict]:
    """Walk pages tracking the active line subtitle; regex-match data rows."""
    import pdfplumber
    rows: list[dict] = []
    current_line: str | None = None
    skipped = 0
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            t = page.extract_text() or ""
            for raw in t.splitlines():
                ln = raw.strip()
                if not ln:
                    continue
                m = HDR_RE_OLD.match(ln)
                if m:
                    label = m.group("line").strip().lower()
                    line_slug = LINE_NORMALIZE.get(label)
                    if line_slug is None:
                        raise RuntimeError(f"IL {year}: unknown line label {label!r}")
                    current_line = line_slug
                    continue
                if current_line is None:
                    continue
                m = ROW_RE_OLD.match(ln)
                if not m:
                    skipped += 1
                    continue
                rows.append({
                    "year": year,
                    "line": current_line,
                    "naic_code": m.group("cocode"),
                    "company_name": m.group("name").strip(),
                    "complaints": int(m.group("complaints")),
                    "premium": parse_premium(m.group("premium")),
                    "market_share": float(m.group("mshare")) / 100.0,
                    "complaint_share": float(m.group("cshare")) / 100.0,
                    "ratio": parse_ratio(m.group("ratio")),
                    "ratio_type": "share_of_share",
                    "reason_underwriting": None,
                    "reason_marketing_sales": None,
                    "reason_claims_handling": None,
                    "reason_policyholder_service": None,
                    "source_file": path.name,
                })
    log(f"  {path.name} (old layout): {len(rows)} rows, {skipped} non-row lines skipped", logf)
    return rows


def parse_new_layout(path: Path, year: int, logf) -> list[dict]:
    """Walk pages tracking the active section header; regex-match data rows."""
    import pdfplumber
    rows: list[dict] = []
    current_line: str | None = None
    skipped = 0
    with pdfplumber.open(path) as pdf:
        for page in pdf.pages:
            t = page.extract_text() or ""
            for raw in t.splitlines():
                ln = raw.strip()
                if not ln:
                    continue
                m = HDR_RE_NEW.match(ln)
                if m:
                    label = m.group("line").strip().lower()
                    line_slug = LINE_NORMALIZE.get(label)
                    if line_slug is None:
                        raise RuntimeError(f"IL {year}: unknown line label {label!r}")
                    current_line = line_slug
                    continue
                if current_line is None:
                    continue
                m = ROW_RE_NEW.match(ln)
                if not m:
                    skipped += 1
                    continue
                rows.append({
                    "year": year,
                    "line": current_line,
                    "naic_code": None,
                    "company_name": m.group("name").strip(),
                    "complaints": int(m.group("complaints")),
                    "premium": parse_premium(m.group("premium")),
                    "market_share": None,
                    "complaint_share": None,
                    "ratio": parse_ratio(m.group("ratio")),
                    "ratio_type": "per_million_ep",
                    # Reason-code columns vary across years (4 vs 6 cols);
                    # not extracted in v1.
                    "reason_underwriting": None,
                    "reason_marketing_sales": None,
                    "reason_claims_handling": None,
                    "reason_policyholder_service": None,
                    "source_file": path.name,
                })
    log(f"  {path.name} (new layout): {len(rows)} rows, {skipped} non-row lines skipped", logf)
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
            year = f["year"]
            path = FILES_DIR / f["filename"]
            # Layout detection is content-based: 2018 uses the "Complaint
            # Ratios - {Line}" per-page subtitle; 2019+ all use "X COMPLAINTS
            # BY COMPANY NAME" sections. Scan the first 5 pages for either
            # marker since the summary/cover pages don't carry it.
            import pdfplumber as _pdfplumber
            head = ""
            with _pdfplumber.open(path) as _pdf:
                for i in range(min(5, len(_pdf.pages))):
                    head += (_pdf.pages[i].extract_text() or "") + "\n"
            if "COMPLAINTS BY COMPANY NAME" in head.upper():
                rows = parse_new_layout(path, year, logf)
            else:
                rows = parse_old_layout(path, year, logf)
            all_rows.extend(rows)

        if not all_rows:
            log("HARD FAILURE: no rows parsed", logf)
            return 4

        df = pl.DataFrame(all_rows, schema={
            "year": pl.Int32,
            "line": pl.String,
            "naic_code": pl.String,
            "company_name": pl.String,
            "complaints": pl.Int64,
            "premium": pl.Float64,
            "market_share": pl.Float64,
            "complaint_share": pl.Float64,
            "ratio": pl.Float64,
            "ratio_type": pl.String,
            "reason_underwriting": pl.Int64,
            "reason_marketing_sales": pl.Int64,
            "reason_claims_handling": pl.Int64,
            "reason_policyholder_service": pl.Int64,
            "source_file": pl.String,
        }).sort(["year", "line", "company_name"])

        # ---- Output 1: per-company per-year per-line ----
        cy_pq = OUTPUT_DIR / "il_complaints_company_yearly.parquet"
        cy_csv = OUTPUT_DIR / "il_complaints_company_yearly.csv"
        df.write_parquet(cy_pq)
        df.write_csv(cy_csv)
        log(f"Wrote {cy_pq.name} ({len(df):,} rows)", logf)

        # ---- Output 2: per-(year × line) aggregate ----
        yearly = (
            df.group_by(["year", "line"])
            .agg(
                pl.col("complaints").sum().alias("total_complaints"),
                pl.len().alias("n_companies"),
                pl.col("ratio").drop_nulls().median().alias("median_ratio"),
                pl.col("premium").sum().alias("total_premium"),
            )
            .sort(["year", "line"])
        )
        y_pq = OUTPUT_DIR / "il_complaints_yearly.parquet"
        y_csv = OUTPUT_DIR / "il_complaints_yearly.csv"
        yearly.write_parquet(y_pq)
        yearly.write_csv(y_csv)
        log(f"Wrote {y_pq.name} ({len(yearly):,} rows)", logf)

        log(f"\nYears: {sorted(df['year'].unique().to_list())}", logf)
        log(f"Lines: {sorted(df['line'].unique().to_list())}", logf)
        log(f"Ratio types: {df['ratio_type'].unique().to_list()}", logf)
        with pl.Config(tbl_rows=40, fmt_float="full"):
            log(f"\nYearly aggregate:\n{yearly}", logf)

        log(f"=== run completed {datetime.now(timezone.utc).isoformat(timespec='seconds')} ===", logf)
    return 0


if __name__ == "__main__":
    sys.exit(main())
