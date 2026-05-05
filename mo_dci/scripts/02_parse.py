"""Parse the three Missouri DCI complaint reports into tidy parquet outputs.

Inputs (from 01_download.py):
  mo_dci/interim/2021_complaint_report.pdf
  mo_dci/interim/2022_complaint_report.pdf
  mo_dci/interim/2023_complaint_index.pdf

Outputs:
  mo_dci/output/mo_complaints_yearly.{parquet,csv}
    Per-year per-line aggregate counts + consumer-relief resolution %.
    Each (year, line) cell may appear in 1-3 reports; we keep one row per
    (report_year, year, line, metric) so cross-report agreement is auditable.

  mo_dci/output/mo_complaints_company_by_period.{parquet,csv}
    Per-company complaint indices, 3-year-pooled per published report. Schema:
    state, report_year, period_start, period_end, line, naic_code,
    company_name_raw, complaints_pooled, avg_annual_premium, avg_market_share,
    complaint_index, page.

  mo_dci/output/run_log.txt   appended.

Out of scope for v1 (see PLAN.md):
  - Per-reason breakouts (Section 5).
  - P&C sub-line breakouts within "Other P&C" (Section 4 third table).
  - Top-40 writer subsections (Sections 6, 7) — redundant with Section 8 all-companies.
"""
from __future__ import annotations

import csv
import re
from datetime import datetime, timezone
from pathlib import Path

import pdfplumber
import polars as pl

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INTERIM_DIR = PROJECT_ROOT / "mo_dci" / "interim"
OUTPUT_DIR = PROJECT_ROOT / "mo_dci" / "output"
LOG_PATH = OUTPUT_DIR / "run_log.txt"

# report file, report_year, period_start, period_end, section8_first_pdf_page (1-based)
# Section-8 start is hardcoded per report (the PDFs use 3 different layouts and
# auto-detection is fragile). Verify by opening the PDF: the page should show
# "Private Passenger Automobile Insurance Complaint Indices" with a per-company
# data table — and crucially, NOT "Top 40" anywhere on the page.
REPORTS = [
    ("2021_complaint_report.pdf", 2021, 2018, 2020, 39),
    ("2022_complaint_report.pdf", 2022, 2020, 2022, 51),
    ("2023_complaint_index.pdf",   2023, 2021, 2023, 65),
]

# Order matters for label matching — longest first.
LINE_LABELS = [
    ("Total P&C Complaints", "total_pc"),
    ("Total A&H Complaints", "total_ah"),
    ("Private Passenger Auto", "private_passenger_auto"),
    ("Life and Annuities", "life_annuities"),
    ("Medicare Supplement", "medicare_supplement"),
    ("All Other A&H", "all_other_ah"),
    ("Long Term Care", "long_term_care"),
    ("Other P&C", "other_pc"),
    ("Homeowners", "homeowners"),
    ("HMO", "hmo"),
    ("Total", "total"),
]

# Section-8 sub-line order is consistent across all 3 reports' TOCs:
# 8.1 PPA, 8.2 HO/Farm/MH/Fire, 8.3 A&H, 8.4 LTC, 8.5 MedSup, 8.6 Life, 8.7 HMO.
SECTION8_LINE_BY_INDEX = [
    "private_passenger_auto",          # 8.1
    "homeowners_farm_mh_fire",          # 8.2
    "accident_health",                  # 8.3
    "long_term_care",                   # 8.4
    "medicare_supplement",              # 8.5
    "life_annuities",                   # 8.6
    "hmo",                              # 8.7
]
# 2023 report has clean "8.<n>" section numbers even when the rest of the title is garbled.
SUBLINE_INDEX_RE = re.compile(r"(?m)^\s*8\.([1-7])(?:\s|$)")
# 2021 and 2022 use plain title text per sub-section page; matching is restricted
# (in `parse_company_indices`) to head text that contains "Complaint Indices",
# so these can be lenient. Order matters — match longest/most-specific first.
SECTION8_TITLE_PATTERNS = [
    (re.compile(r"private\s*passenger\s*automobile", re.I), "private_passenger_auto"),
    (re.compile(r"long.?term\s*care", re.I), "long_term_care"),
    (re.compile(r"medicare\s*supplement", re.I), "medicare_supplement"),
    (re.compile(r"accident\s*and\s*health", re.I), "accident_health"),
    (re.compile(r"life\s*insurance|life\s*and\s*annuit", re.I), "life_annuities"),
    (re.compile(r"health\s*maintenance", re.I), "hmo"),
    (re.compile(r"homeowners", re.I), "homeowners_farm_mh_fire"),
]

PCT_RE = re.compile(r"^([\d.]+)%$")
INT_RE = re.compile(r"^[\d,]+$")


def parse_int(s: str) -> int | None:
    if s is None:
        return None
    s = str(s).strip().replace(",", "")
    if not s or s in {"-", "—"}:
        return None
    try:
        return int(s)
    except ValueError:
        return None


def parse_pct(s: str) -> float | None:
    if s is None:
        return None
    s = str(s).strip()
    if not s or s in {"-", "—"}:
        return None
    m = PCT_RE.match(s)
    if not m:
        return None
    return float(m.group(1)) / 100.0


def parse_dollar(s: str) -> int | None:
    if s is None:
        return None
    s = str(s).strip().replace(",", "").replace("$", "")
    if not s or s in {"-", "—"}:
        return None
    try:
        return int(s)
    except ValueError:
        return None


def is_toc_page(text: str) -> bool:
    """TOC pages either have many '....' dot leaders or have a literal
    'Table of Contents' / 'TABLE OF CONTENTS' header (covers the 2021 case
    which uses no dot leaders)."""
    if not text:
        return False
    if text.count("....") >= 4 or text.count(". . . .") >= 4:
        return True
    head = "\n".join(text.split("\n")[:3]).lower()
    return "table of contents" in head


def find_aggregate_pages(pdf: pdfplumber.PDF) -> tuple[list[int], list[int]]:
    """Return (total_complaints_page_indexes, consumer_relief_page_indexes).
    All zero-based."""
    total_pages: list[int] = []
    relief_pages: list[int] = []
    for i, page in enumerate(pdf.pages):
        t = page.extract_text() or ""
        if is_toc_page(t):
            continue
        norm = t.replace(" ", "").lower()
        if "totalcomplaintsbyline" in norm:
            total_pages.append(i)
        if "resolvedwithconsumerrelief" in norm:
            relief_pages.append(i)
    return total_pages, relief_pages


def parse_aggregate_block(text: str, mode: str) -> list[dict]:
    """Parse a "Total Complaints by Line" or "Complaint Resolution" table.
    `text` is the block of text containing only the relevant table (caller
    splits the page if both tables are on it)."""
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    year_re = re.compile(r"\b(20\d{2})\b")
    header_years: list[int] = []
    header_idx = None
    for i, ln in enumerate(lines):
        years = year_re.findall(ln)
        if len(years) == 5 and ("Line" in ln or "line" in ln):
            header_years = [int(y) for y in years]
            header_idx = i
            break
    if not header_years:
        return []
    rows: list[dict] = []
    for ln in lines[header_idx + 1:]:
        # match longest label first
        match = None
        for label, canonical in LINE_LABELS:
            # match either "Label" with a space or "Label" with whitespace stripped
            patterns = [label, label.replace(" ", "")]
            for pat in patterns:
                if ln.startswith(pat):
                    # Require what follows to be whitespace or digit (so "Total" doesn't match "Total P&C")
                    rest = ln[len(pat):]
                    if not rest or rest[0].isspace() or rest[0].isdigit() or rest[0] in "-—":
                        match = (label, canonical, pat, rest)
                        break
            if match:
                break
        if not match:
            continue
        label, canonical, _, rest = match
        toks = re.split(r"\s+", rest.strip())
        if mode == "count":
            cands = [t for t in toks if t in {"-", "—"} or INT_RE.match(t)]
        else:
            cands = [t for t in toks if t in {"-", "—"} or PCT_RE.match(t)]
        if len(cands) < 5:
            continue
        vals = cands[-5:]
        for yr, raw in zip(header_years, vals):
            if mode == "count":
                v = parse_int(raw)
                rows.append({"year": yr, "line": canonical, "metric": "complaints_total", "value": v, "raw": raw})
            else:
                v = parse_pct(raw)
                rows.append({"year": yr, "line": canonical, "metric": "pct_resolved_consumer_relief", "value": v, "raw": raw})
    return rows


def parse_aggregate_page(text: str) -> tuple[list[dict], list[dict]]:
    """Some reports put both tables on one page. Split by 'Complaint Resolution'
    header so each half is parsed in the right mode."""
    split_marker = re.search(r"Complaint\s+Resolution\s+by\s+Line", text)
    if split_marker:
        first = text[: split_marker.start()]
        second = text[split_marker.start():]
        counts = parse_aggregate_block(first, mode="count")
        pcts = parse_aggregate_block(second, mode="pct")
    else:
        counts = parse_aggregate_block(text, mode="count")
        pcts = parse_aggregate_block(text, mode="pct")
    return counts, pcts


def normalize_company_name(s: str) -> str:
    return " ".join(str(s).replace("\n", " ").split())


# Regex for one company row in plain-text mode (used for 2021's report which
# pdfplumber can't extract as tables). Format:
#   <NAIC code 4-5 digits> <Company Name (multi-token)> <complaints> <$premium> <market_share%> <index>
# All trailing fields can be "-" or "—" instead of numeric.
_NUM = r"(?:[\d,]+|-|—)"
_PCT = r"(?:[\d.]+%|-|—)"
_DOL = r"(?:\$[\d,-]+|-|—)"
COMPANY_ROW_RE = re.compile(
    rf"^\s*(?P<code>\d{{4,5}})\s+(?P<name>.+?)\s+(?P<complaints>{_NUM})\s+(?P<premium>{_DOL})\s+(?P<share>{_PCT})\s+(?P<index>{_NUM})\s*$"
)


def parse_company_rows_text(text: str) -> list[dict]:
    """Plain-text fallback for a section-8 sub-section page (used when
    pdfplumber's extract_tables() returns nothing — e.g., 2021 report)."""
    rows: list[dict] = []
    for line in text.split("\n"):
        line = line.strip()
        if not line:
            continue
        m = COMPANY_ROW_RE.match(line)
        if not m:
            continue
        if m["name"].strip().lower() == "total":
            continue
        rows.append({
            "naic_code": m["code"],
            "company_name_raw": " ".join(m["name"].split()),
            "complaints_pooled": parse_int(m["complaints"]),
            "avg_annual_premium": parse_dollar(m["premium"]),
            "avg_market_share": parse_pct(m["share"]),
            "complaint_index": parse_int(m["index"]),
        })
    return rows


def parse_company_indices(pdf: pdfplumber.PDF, section8_start: int) -> list[dict]:
    """Walk Section 8 from `section8_start` to end of doc, tracking sub-line.
    Try table extraction first; fall back to plain-text regex parse."""
    rows: list[dict] = []
    current_line = None
    for i in range(section8_start, len(pdf.pages)):
        page = pdf.pages[i]
        text = page.extract_text() or ""
        if is_toc_page(text):
            continue
        # Detect line transitions: "8.<digit>" pattern (2023) is the most reliable.
        # For 2021/2022, look for plain title text but ONLY on pages that show a
        # sub-section header (head text contains "Complaint Indices" near the top),
        # to avoid false positives from company names in continuation pages.
        head_lines = [l for l in text.split("\n") if l.strip()][:8]
        head_text = "\n".join(head_lines)
        m = SUBLINE_INDEX_RE.search(head_text)
        if m:
            idx = int(m.group(1)) - 1
            if 0 <= idx < len(SECTION8_LINE_BY_INDEX):
                current_line = SECTION8_LINE_BY_INDEX[idx]
        elif "complaint indices" in head_text.lower():
            # Sub-section header structure: line title appears right before "Complaint Indices".
            # Continuation pages start with "Code Name ..." or "Name Code ..." column headers.
            for pattern, canonical in SECTION8_TITLE_PATTERNS:
                if pattern.search(head_text):
                    current_line = canonical
                    break

        tables = page.extract_tables() or []
        if not tables:
            # Fallback: plain-text regex parse (2021 report).
            text_rows = parse_company_rows_text(text)
            for r in text_rows:
                r["line"] = current_line or "unknown"
                r["page"] = i + 1
                rows.append(r)
            continue
        for tbl in tables:
            if not tbl:
                continue
            # Determine column order from the header row
            header_row = tbl[0] if tbl else []
            header_text = [str(c or "").lower() for c in header_row]
            joined = " ".join(header_text)
            # Skip non-data tables
            if not ("name" in joined and "code" in joined):
                continue
            # Find column indexes
            try:
                name_col = next(j for j, c in enumerate(header_text) if "name" in c)
            except StopIteration:
                continue
            try:
                code_col = next(j for j, c in enumerate(header_text) if "code" == c.strip() or c.strip().startswith("code"))
            except StopIteration:
                continue
            # Numeric columns: complaints, premium, market share, index — appear after the max(name_col, code_col)
            data_start = max(name_col, code_col) + 1

            for row in tbl[1:]:
                if not row or len(row) <= max(name_col, code_col):
                    continue
                name_raw = str(row[name_col] or "").strip()
                code_raw = str(row[code_col] or "").strip()
                if not name_raw or not code_raw:
                    continue
                if not re.match(r"^\d{4,5}$", code_raw):
                    continue
                # Skip the "Total" row at the bottom of each per-line section
                if name_raw.lower() == "total":
                    continue
                cells = [str(c or "").strip() for c in row[data_start:]]
                # Filter to non-empty cells
                cells = [c for c in cells if c]
                # Expect 4 cells: complaints, premium, market_share, index
                if len(cells) < 4:
                    continue
                complaints = parse_int(cells[0])
                premium = parse_dollar(cells[1])
                share = parse_pct(cells[2])
                index = parse_int(cells[3])

                rows.append({
                    "line": current_line or "unknown",
                    "naic_code": code_raw,
                    "company_name_raw": normalize_company_name(name_raw),
                    "complaints_pooled": complaints,
                    "avg_annual_premium": premium,
                    "avg_market_share": share,
                    "complaint_index": index,
                    "page": i + 1,
                })
    return rows


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    yearly_rows: list[dict] = []
    company_rows: list[dict] = []
    log_lines = [f"\n### {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%MZ')} — parse run"]

    for fn, report_year, period_start, period_end, section8_first_page in REPORTS:
        path = INTERIM_DIR / fn
        section8_start = section8_first_page - 1  # 0-based
        log_lines.append(f"  -- {fn} (report_year={report_year}, period={period_start}-{period_end})")
        with pdfplumber.open(path) as pdf:
            total_pages, relief_pages = find_aggregate_pages(pdf)
            log_lines.append(f"     total-complaint pages found: {[p+1 for p in total_pages]}")
            log_lines.append(f"     relief-% pages found:        {[p+1 for p in relief_pages]}")
            log_lines.append(f"     section-8 start (hardcoded): {section8_start+1}")

            # Aggregate tables: union of total_pages and relief_pages, dedup, parse each.
            agg_pages = sorted(set(total_pages) | set(relief_pages))
            seen_count_yrs: set[tuple[int, str]] = set()
            seen_pct_yrs: set[tuple[int, str]] = set()
            for p in agg_pages:
                t = pdf.pages[p].extract_text() or ""
                cnts, pcts = parse_aggregate_page(t)
                for r in cnts:
                    key = (r["year"], r["line"])
                    if key in seen_count_yrs:
                        continue
                    seen_count_yrs.add(key)
                    yearly_rows.append({
                        "report_year": report_year, **{k: r[k] for k in ("year", "line", "metric", "value")},
                        "source_page": p + 1,
                    })
                for r in pcts:
                    key = (r["year"], r["line"])
                    if key in seen_pct_yrs:
                        continue
                    seen_pct_yrs.add(key)
                    yearly_rows.append({
                        "report_year": report_year, **{k: r[k] for k in ("year", "line", "metric", "value")},
                        "source_page": p + 1,
                    })
            log_lines.append(f"     yearly counts parsed: {len(seen_count_yrs)} cells")
            log_lines.append(f"     relief-% parsed:      {len(seen_pct_yrs)} cells")

            if section8_start is not None and section8_start < len(pdf.pages):
                comp = parse_company_indices(pdf, section8_start)
                for r in comp:
                    r["state"] = "MO"
                    r["report_year"] = report_year
                    r["period_start"] = period_start
                    r["period_end"] = period_end
                    company_rows.append(r)
                # Per-line subtotal
                from collections import Counter
                per_line = Counter(r["line"] for r in comp)
                log_lines.append(f"     section-8 company rows: {len(comp)}  by line: {dict(per_line)}")

    yearly = pl.DataFrame(yearly_rows).with_columns(pl.lit("MO").alias("state")).select([
        "state", "report_year", "year", "line", "metric", "value", "source_page",
    ]).sort(["line", "year", "report_year", "metric"])
    yearly.write_parquet(OUTPUT_DIR / "mo_complaints_yearly.parquet")
    yearly.write_csv(OUTPUT_DIR / "mo_complaints_yearly.csv")
    log_lines.append(f"  wrote mo_complaints_yearly.{{parquet,csv}}: {yearly.height} rows")

    company = pl.DataFrame(company_rows).select([
        "state", "report_year", "period_start", "period_end", "line",
        "naic_code", "company_name_raw",
        "complaints_pooled", "avg_annual_premium", "avg_market_share", "complaint_index",
        "page",
    ]).sort(["report_year", "line", "company_name_raw"])
    company.write_parquet(OUTPUT_DIR / "mo_complaints_company_by_period.parquet")
    company.write_csv(OUTPUT_DIR / "mo_complaints_company_by_period.csv")
    log_lines.append(f"  wrote mo_complaints_company_by_period.{{parquet,csv}}: {company.height} rows")

    counts = yearly.filter(pl.col("metric") == "complaints_total").drop_nulls("value")
    dupes = (
        counts.group_by(["year", "line"])
        .agg(pl.col("value").n_unique().alias("n_distinct"), pl.col("value").alias("vals"))
        .filter(pl.col("n_distinct") > 1)
    )
    if dupes.height:
        log_lines.append(f"  WARN: {dupes.height} (year,line) cells disagree across reports:")
        for row in dupes.head(20).to_dicts():
            log_lines.append(f"     {row['year']} {row['line']}: {row['vals']}")
    else:
        log_lines.append("  ok: all overlapping (year,line) counts agree across reports")

    with LOG_PATH.open("a") as f:
        f.write("\n".join(log_lines) + "\n")
    print("\n".join(log_lines))


if __name__ == "__main__":
    main()
