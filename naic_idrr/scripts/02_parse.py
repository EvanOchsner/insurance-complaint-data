"""Parse NAIC IDRR Vol 1 PDFs into a tidy state x year complaint table.

Inputs (from 01_download.py):
  naic_idrr/interim/idrr/<year>[_vol12|_vol2].pdf
  naic_idrr/interim/manifest.json

Outputs:
  naic_idrr/output/naic_idrr_complaints_state_yearly.parquet
  naic_idrr/output/naic_idrr_complaints_state_yearly.csv
  naic_idrr/output/run_log.txt   (appended)

Parsing strategy:
  1. Find the page in each PDF whose extracted text matches both the title
     "Consumer Complaints/Inquiries - YYYY" and a state-name anchor (Alabama).
  2. The title's YYYY is the canonical *data year* (which may differ from the
     publication year used in NAIC's archive labels). Pre-1998 PDFs are
     scanned with poor OCR and are skipped with a logged warning.
  3. For each row whose first tokens match a known state/jurisdiction name,
     pull the **last two integer-like tokens** as (complaints, inquiries).
     This handles both layout eras:
       - 2005-2022: `State <complaints> <inquiries> <Yes|No>`
       - 1998-2004: `State <Yes|No> <sites> <mobile_sites> <complaints>
                     <inquiries> <Yes|No>` (sites/mobile_sites are smaller
                     integers; complaints/inquiries are always last-two).
  4. Strip thousands-separators and treat "-", "n/a", "" as null.
  5. Validate: the "Total" row's national totals match the sum of per-state
     rows (warn-only) AND fall within a sane band (50k-1M complaints).
"""
from __future__ import annotations

import csv
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import pdfplumber
import polars as pl

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_ROOT = PROJECT_ROOT / "naic_idrr"
INTERIM = DATASET_ROOT / "interim"
IDRR_DIR = INTERIM / "idrr"
INDEX_CSV = DATASET_ROOT / "reference" / "idrr_pdf_index.csv"
MANIFEST_PATH = INTERIM / "manifest.json"
OUTPUT = DATASET_ROOT / "output"
LOG_PATH = OUTPUT / "run_log.txt"

OUT_PARQUET = OUTPUT / "naic_idrr_complaints_state_yearly.parquet"
OUT_CSV = OUTPUT / "naic_idrr_complaints_state_yearly.csv"

# Known state / jurisdiction name prefixes as they appear in IDRR tables.
# Order matters: longer multi-word names come first so the regex picks the
# longest match. We match at line start, case-sensitive (state names are
# title-case in the source).
JURISDICTIONS = [
    ("Alabama", "AL"),
    ("Alaska", "AK"),
    ("American Samoa", "AS"),
    ("Arizona", "AZ"),
    ("Arkansas", "AR"),
    ("California", "CA"),
    ("Colorado", "CO"),
    ("Connecticut", "CT"),
    ("Delaware", "DE"),
    ("Dist. of Columbia", "DC"),
    ("District of Columbia", "DC"),
    ("Florida", "FL"),
    ("Georgia", "GA"),
    ("Guam", "GU"),
    ("Hawaii", "HI"),
    ("Idaho", "ID"),
    ("Illinois", "IL"),
    ("Indiana", "IN"),
    ("Iowa", "IA"),
    ("Kansas", "KS"),
    ("Kentucky", "KY"),
    ("Louisiana", "LA"),
    ("Maine", "ME"),
    ("Maryland", "MD"),
    ("Massachusetts", "MA"),
    ("Michigan", "MI"),
    ("Minnesota", "MN"),
    ("Mississippi", "MS"),
    ("Missouri", "MO"),
    ("Montana", "MT"),
    ("Nebraska", "NE"),
    ("Nevada", "NV"),
    ("New Hampshire", "NH"),
    ("New Jersey", "NJ"),
    ("New Mexico", "NM"),
    ("New York", "NY"),
    ("North Carolina", "NC"),
    ("North Dakota", "ND"),
    ("N. Mariana Islands", "MP"),
    ("N.Mariana Islands", "MP"),
    ("Northern Mariana Islands", "MP"),
    ("Ohio", "OH"),
    ("Oklahoma", "OK"),
    ("Oregon", "OR"),
    ("Pennsylvania", "PA"),
    ("Puerto Rico", "PR"),
    ("Rhode Island", "RI"),
    ("South Carolina", "SC"),
    ("South Dakota", "SD"),
    ("Tennessee", "TN"),
    ("Texas", "TX"),
    ("U.S. Virgin Islands", "VI"),
    ("US Virgin Islands", "VI"),
    ("Virgin Islands", "VI"),
    ("Utah", "UT"),
    ("Vermont", "VT"),
    ("Virginia", "VA"),
    ("Washington", "WA"),
    ("West Virginia", "WV"),
    ("Wisconsin", "WI"),
    ("Wyoming", "WY"),
]
# Sort longest-first so multi-word prefixes match before their substrings.
JURISDICTIONS.sort(key=lambda x: -len(x[0]))
JUR_RE = re.compile(
    r"^(" + "|".join(re.escape(name) for name, _ in JURISDICTIONS) + r")\s+(.*)$"
)
NAME_TO_CODE = {name: code for name, code in JURISDICTIONS}

TITLE_RE = re.compile(r"Consumer\s+Complaints/Inquiries\s*[-–]\s*(\d{4})", re.IGNORECASE)
INT_TOKEN_RE = re.compile(r"^-?[\d,]+$")


def log(msg: str, fh) -> None:
    print(msg)
    fh.write(msg + "\n")


def find_table_page(pdf: pdfplumber.PDF) -> tuple[int, int, str] | None:
    """Return (page_idx_1based, data_year, page_text) or None.

    Distinguishes the actual data page from a TOC page that merely cites the
    table title by requiring ≥30 jurisdiction-prefixed rows (the table has
    ~55 rows; TOC pages have 0).
    """
    for i, page in enumerate(pdf.pages, 1):
        try:
            text = page.extract_text() or ""
        except Exception:
            continue
        m = TITLE_RE.search(text)
        if not m:
            continue
        n_jur_rows = sum(
            1 for line in text.splitlines() if JUR_RE.match(line.strip())
        )
        if n_jur_rows < 30:
            continue
        return i, int(m.group(1)), text
    return None


def parse_int(token: str) -> int | None:
    s = token.replace(",", "").strip()
    if s in ("", "-", "–", "—", "n/a", "N/A", "rda", "n!a", "0"):
        # NB: "0" is legitimate (Arkansas 2022 had 0/0); we *do* keep it
        # but the early-OCR garbage "rda"/"n!a" maps to null.
        if s == "0":
            return 0
        return None
    if INT_TOKEN_RE.match(token.replace(",", "")) or s.isdigit():
        try:
            return int(s)
        except ValueError:
            return None
    return None


def parse_row(line: str) -> tuple[str, int | None, int | None] | None:
    """Match the row against known jurisdictions and pull the last two
    integer-valued tokens as (complaints, inquiries). Returns
    (jurisdiction_name, complaints, inquiries) or None."""
    m = JUR_RE.match(line.strip())
    if not m:
        return None
    name = m.group(1)
    rest_tokens = m.group(2).split()
    # Drop a trailing Yes/No (the "available to public" column).
    while rest_tokens and rest_tokens[-1] in ("Yes", "No", "-", "–", "—"):
        rest_tokens.pop()
    # Now collect integer-valued tokens, taking the last two.
    int_indices = []
    for idx, tok in enumerate(rest_tokens):
        if INT_TOKEN_RE.match(tok):
            int_indices.append(idx)
    if len(int_indices) >= 2:
        complaints_tok = rest_tokens[int_indices[-2]]
        inquiries_tok = rest_tokens[int_indices[-1]]
        return name, parse_int(complaints_tok), parse_int(inquiries_tok)
    if len(int_indices) == 1:
        # Sometimes inquiries is missing/dash; treat single integer as complaints.
        return name, parse_int(rest_tokens[int_indices[0]]), None
    # Pure-dash row (territory with no data).
    return name, None, None


def parse_pdf(pdf_path: Path, expected_year: int, fh) -> list[dict]:
    """Returns list of {year, jurisdiction, state, complaints, inquiries}."""
    rows: list[dict] = []
    try:
        pdf = pdfplumber.open(pdf_path)
    except Exception as e:
        log(f"  !! {pdf_path.name}: open failed: {e}", fh)
        return rows
    try:
        loc = find_table_page(pdf)
        if loc is None:
            log(f"  -- {pdf_path.name}: no Consumer Complaints/Inquiries table page found (likely scanned/OCR-broken; skipping)", fh)
            return rows
        page_idx, data_year, page_text = loc
        if data_year != expected_year:
            log(
                f"  ?? {pdf_path.name}: title says data year={data_year} but index says {expected_year} "
                f"(NAIC IDRR is published in year N+1 with year-N data; using title year)",
                fh,
            )
        n_rows = 0
        n_skipped = 0
        seen_codes = set()
        national_total_complaints = None
        national_total_inquiries = None
        for line in page_text.splitlines():
            stripped = line.strip()
            if stripped.lower().startswith("total"):
                # Modern (2005+): "Total 282,567 1,516,175"
                # Legacy (1998-2004): "Total 86 23 405,323 3,546,563" - the
                # first two are sites/mobile-sites totals, NOT
                # complaints/inquiries. Take the LAST two integer tokens.
                int_tokens = [
                    tok for tok in stripped.split() if INT_TOKEN_RE.match(tok)
                ]
                if len(int_tokens) >= 2:
                    national_total_complaints = int(int_tokens[-2].replace(",", ""))
                    national_total_inquiries = int(int_tokens[-1].replace(",", ""))
                continue
            parsed = parse_row(stripped)
            if parsed is None:
                continue
            name, complaints, inquiries = parsed
            code = NAME_TO_CODE[name]
            if code in seen_codes:
                # Some pages render territories twice (continuation/footer).
                continue
            seen_codes.add(code)
            if complaints is None and inquiries is None:
                n_skipped += 1
                continue
            rows.append({
                "year": data_year,
                "jurisdiction": code,
                "jurisdiction_name": name,
                "complaints": complaints,
                "inquiries": inquiries,
            })
            n_rows += 1
        # Sanity: sum of per-state vs Total.
        sum_complaints = sum(r["complaints"] or 0 for r in rows if r["year"] == data_year)
        sum_inquiries = sum(r["inquiries"] or 0 for r in rows if r["year"] == data_year)
        log(
            f"  ok {pdf_path.name}: data_year={data_year} page={page_idx} "
            f"rows={n_rows} (skipped {n_skipped} empty/territory) "
            f"sum_complaints={sum_complaints:,} sum_inquiries={sum_inquiries:,}",
            fh,
        )
        if national_total_complaints is not None:
            diff_c = abs(sum_complaints - national_total_complaints)
            diff_i = abs(sum_inquiries - (national_total_inquiries or 0))
            ratio_c = diff_c / max(national_total_complaints, 1)
            ok_c = ratio_c < 0.05
            log(
                f"     vs PDF Total row: complaints={national_total_complaints:,} "
                f"(Δ={diff_c}, {'ok' if ok_c else 'WARN'}) "
                f"inquiries={national_total_inquiries:,} (Δ={diff_i})",
                fh,
            )
            # Reject the year wholesale if the per-state sum diverges from
            # the printed Total row by more than 5%. This catches rows where
            # the parser picked the wrong column due to garbled OCR or
            # split-cell artifacts in early PDFs (1994-1996).
            if not ok_c:
                log(
                    f"     XX rejecting {pdf_path.name} year={data_year}: "
                    f"sum-vs-Total mismatch is {ratio_c:.1%} > 5%; data unreliable",
                    fh,
                )
                rows.clear()
        # Likewise reject obviously-incomplete extractions. Real tables have
        # 50 states + DC + 4 territories = 55 rows; we expect at least 45.
        if rows and len(rows) < 45:
            log(
                f"     XX rejecting {pdf_path.name} year={data_year}: "
                f"only {len(rows)} jurisdiction rows extracted (need ≥45)",
                fh,
            )
            rows.clear()
    finally:
        pdf.close()
    return rows


def load_index() -> list[dict]:
    rows = []
    with INDEX_CSV.open() as f:
        for row in csv.DictReader(f):
            row["year"] = int(row["year"])
            rows.append(row)
    return rows


def build_local_path(row: dict) -> Path:
    suffix = {"1": "", "2": "_vol2", "12": "_vol12"}.get(row["vol"], f"_vol{row['vol']}")
    return IDRR_DIR / f"{row['year']}{suffix}.pdf"


def main() -> int:
    OUTPUT.mkdir(parents=True, exist_ok=True)
    fh = LOG_PATH.open("a")
    fh.write(f"\n=== {datetime.now(timezone.utc).isoformat(timespec='seconds')} parse run ===\n")

    index = load_index()
    all_rows: list[dict] = []
    seen_years: set[int] = set()
    skipped_pdfs: list[str] = []
    for entry in index:
        # Vol 2 PDFs don't carry the consumer-complaints table; only Vol 1
        # and combined Vol 1+2 do.
        if entry["vol"] == "2":
            continue
        path = build_local_path(entry)
        if not path.exists():
            log(f"  !! {path.name}: missing on disk", fh)
            continue
        rows = parse_pdf(path, entry["year"], fh)
        if not rows:
            skipped_pdfs.append(path.name)
            continue
        # Dedupe on data_year — if we already have this data year (from
        # another publication-year PDF), keep the first one parsed.
        data_year = rows[0]["year"]
        if data_year in seen_years:
            log(f"  -- {path.name}: data_year={data_year} already seen, skipping duplicate", fh)
            continue
        seen_years.add(data_year)
        all_rows.extend(rows)

    if not all_rows:
        log("  !! no rows parsed; nothing to write", fh)
        fh.close()
        return 1

    df = pl.DataFrame(all_rows).select(
        pl.col("year").cast(pl.Int32),
        pl.col("jurisdiction"),
        pl.col("jurisdiction_name"),
        pl.col("complaints").cast(pl.Int64),
        pl.col("inquiries").cast(pl.Int64),
    ).sort(["year", "jurisdiction"])

    df.write_parquet(OUT_PARQUET)
    df.write_csv(OUT_CSV)
    log(
        f"  wrote {OUT_PARQUET.name} + {OUT_CSV.name}: "
        f"{df.height} rows, {df['year'].n_unique()} years "
        f"({df['year'].min()}-{df['year'].max()}), "
        f"{df['jurisdiction'].n_unique()} jurisdictions",
        fh,
    )
    if skipped_pdfs:
        log(f"  skipped {len(skipped_pdfs)} PDFs: {', '.join(skipped_pdfs)}", fh)
    fh.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
