"""Parse the 24 Michigan DIFS HTML pages into tidy parquet outputs.

Inputs (from 01_download.py):
  mi_difs/interim/files/company_<line>_<year>.html      (5 lines × 3 years)
  mi_difs/interim/files/stats_<kind>_<year>.html         (3 stats × 3 years)
  mi_difs/interim/manifest.json

Outputs:
  mi_difs/output/mi_complaints_company_yearly.{parquet,csv}
    Per-company per-line per-year ratios. Columns:
    state, year, line, company_id, company_name_raw, complaints,
    written_premium, complaint_ratio_per_million.
    Note: only companies with > $1M annual premium for the line are included
    (DIFS exclusion rule, documented).

  mi_difs/output/mi_complaints_yearly.{parquet,csv}
    Per-line per-year aggregate counts (from the Line of Coverage stats page).
    Columns: state, year, line, count.

  mi_difs/output/mi_complaints_total_yearly.{parquet,csv}
    Per-year totals broken out by entity type (Insurance Company / HMO / Other).
    Columns: state, year, entity_type, count.

  mi_difs/output/mi_complaints_by_reason.{parquet,csv}
    Per-year per-reason × entity-type counts.
    Columns: state, year, reason_category, entity_type, count, pct_within_entity.

  mi_difs/output/run_log.txt   appended.
"""
from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path

import polars as pl
from bs4 import BeautifulSoup

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INTERIM_DIR = PROJECT_ROOT / "mi_difs" / "interim" / "files"
MANIFEST_PATH = PROJECT_ROOT / "mi_difs" / "interim" / "manifest.json"
OUTPUT_DIR = PROJECT_ROOT / "mi_difs" / "output"
LOG_PATH = OUTPUT_DIR / "run_log.txt"

# DIFS line names on the Line-of-Coverage stats page → canonical.
LINE_OF_COVERAGE_MAP = {
    "Accident and Health": "accident_health",
    "Annuity": "annuity",
    "Automobile": "automobile",
    "Fire, Allied Lines & CMP": "fire_allied_cmp",
    "Homeowners": "homeowners",
    "Liability": "liability",
    "Life": "life",
}

PCT_RE = re.compile(r"\(?\s*([\d.]+)\s*%\s*\)?")
INT_RE = re.compile(r"^[\d,]+$")
DOLLAR_RE = re.compile(r"^\s*\$?\s*([\d,]+)\s*$")


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
    m = PCT_RE.search(str(s))
    if not m:
        return None
    return float(m.group(1)) / 100.0


def parse_dollar(s: str) -> int | None:
    if s is None:
        return None
    m = DOLLAR_RE.match(str(s).strip())
    if not m:
        return None
    return int(m.group(1).replace(",", ""))


def parse_ratio(s: str) -> float | None:
    if s is None:
        return None
    s = str(s).strip()
    if not s or s in {"-", "—"}:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def parse_company_page(html: str, line_canonical: str, year: int) -> list[dict]:
    """Each per-company page has rows like:
      <div class="row company-list all-border">
        <div class="col-sm-6 bluecol"><a href="...?companyID=NNNN&forYear=YYYY">NAME</a></div>
        <div class="col-sm-2 center-div">N_COMPLAINTS</div>
        <div class="col-sm-2 r-align push-col">$WRITTEN_PREMIUM</div>
        <div class="col-sm-2 r-align">RATIO</div>
      </div>
    """
    soup = BeautifulSoup(html, "html.parser")
    rows: list[dict] = []
    for div in soup.find_all("div", class_="row"):
        cls = " ".join(div.get("class", []))
        if "company-list" not in cls:
            continue
        cols = div.find_all("div", recursive=False)
        if len(cols) < 4:
            continue
        # company name + ID
        name_link = cols[0].find("a")
        if not name_link:
            continue
        name = name_link.get_text(strip=True)
        href = name_link.get("href", "")
        m = re.search(r"companyID=([0-9]+)", href)
        company_id = m.group(1) if m else ""
        complaints_txt = cols[1].get_text(strip=True)
        premium_txt = cols[2].get_text(strip=True)
        ratio_txt = cols[3].get_text(strip=True)
        rows.append({
            "state": "MI",
            "year": year,
            "line": line_canonical,
            "company_id": company_id,
            "company_name_raw": name,
            "complaints": parse_int(complaints_txt),
            "written_premium": parse_dollar(premium_txt),
            "complaint_ratio_per_million": parse_ratio(ratio_txt),
        })
    return rows


def parse_line_of_coverage(html: str, year: int) -> list[dict]:
    """Line-of-coverage stats: one row per line with count + pct."""
    soup = BeautifulSoup(html, "html.parser")
    rows: list[dict] = []
    for div in soup.find_all("div", class_="row"):
        cols = div.find_all("div", recursive=False)
        if len(cols) < 3:
            continue
        first = cols[0].get_text(strip=True)
        if first not in LINE_OF_COVERAGE_MAP:
            continue
        count = parse_int(cols[1].get_text(strip=True))
        rows.append({
            "state": "MI",
            "year": year,
            "line": LINE_OF_COVERAGE_MAP[first],
            "count": count,
        })
    return rows


def parse_total_complaints(html: str, year: int) -> list[dict]:
    """Total complaints page: 'Insurance Company Complaints', 'HMO Complaints',
    'Other Complaints', 'Total'. Buckets are presented as label + count rows."""
    soup = BeautifulSoup(html, "html.parser")
    text = soup.get_text(" ", strip=True)
    # Use simple regex across the flat text
    rows: list[dict] = []
    patterns = [
        ("insurance_company", r"Insurance\s+Company\s+Complaints\s+([\d,]+)"),
        ("hmo", r"HMO\s+Complaints\s+([\d,]+)"),
        ("other", r"Other\s+Complaints\s+([\d,]+)"),
        ("total", r"Total:\s*([\d,]+)"),
    ]
    for key, pat in patterns:
        m = re.search(pat, text, re.I)
        if m:
            rows.append({"state": "MI", "year": year, "entity_type": key, "count": parse_int(m.group(1))})
    return rows


REASON_CATEGORIES = ["Claim Handling", "Marketing & Sales", "Customer Service", "Underwriting"]


def parse_reasons(html: str, year: int) -> list[dict]:
    """Reason page: 4 reason categories × 3 entity types (insurance, HMO, other).
    Each cell has aria-label like 'Claim Handling insurance count' / '... percentage'."""
    soup = BeautifulSoup(html, "html.parser")
    rows: list[dict] = []
    # Find each reason category by its row
    for cat in REASON_CATEGORIES:
        for entity_label, entity_canonical in [
            ("insurance", "insurance_company"),
            ("HMO", "hmo"),
            ("other", "other"),
        ]:
            count_div = soup.find("div", attrs={"aria-label": f"{cat} {entity_label} count"})
            pct_div = soup.find("div", attrs={"aria-label": f"{cat} {entity_label} percentage"})
            if count_div is None:
                continue
            rows.append({
                "state": "MI",
                "year": year,
                "reason_category": cat,
                "entity_type": entity_canonical,
                "count": parse_int(count_div.get_text(strip=True)),
                "pct_within_entity": parse_pct(pct_div.get_text(strip=True)) if pct_div else None,
            })
    return rows


def main() -> None:
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    manifest = json.loads(MANIFEST_PATH.read_text())
    log_lines = [f"\n### {datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%MZ')} — parse run"]

    company_rows: list[dict] = []
    yearly_rows: list[dict] = []
    total_rows: list[dict] = []
    reason_rows: list[dict] = []

    for entry in manifest["files"]:
        path = INTERIM_DIR / entry["filename"]
        html = path.read_text()
        if entry["kind"] == "company_ratios":
            r = parse_company_page(html, entry["line_canonical"], entry["year"])
            company_rows.extend(r)
            log_lines.append(f"  -- {entry['filename']}: {len(r)} company rows")
        elif entry["kind"] == "statistics":
            slug = entry["kind_slug"]
            if slug == "line_of_coverage":
                r = parse_line_of_coverage(html, entry["year"])
                yearly_rows.extend(r)
                log_lines.append(f"  -- {entry['filename']}: {len(r)} line-of-coverage rows")
            elif slug == "total":
                r = parse_total_complaints(html, entry["year"])
                total_rows.extend(r)
                log_lines.append(f"  -- {entry['filename']}: {len(r)} total-complaint rows")
            elif slug == "complaint_reason":
                r = parse_reasons(html, entry["year"])
                reason_rows.extend(r)
                log_lines.append(f"  -- {entry['filename']}: {len(r)} reason rows")

    # Write outputs
    company = pl.DataFrame(company_rows).select([
        "state", "year", "line", "company_id", "company_name_raw",
        "complaints", "written_premium", "complaint_ratio_per_million",
    ]).sort(["year", "line", "company_name_raw"])
    company.write_parquet(OUTPUT_DIR / "mi_complaints_company_yearly.parquet")
    company.write_csv(OUTPUT_DIR / "mi_complaints_company_yearly.csv")
    log_lines.append(f"  wrote mi_complaints_company_yearly: {company.height} rows")

    yearly = pl.DataFrame(yearly_rows).select(["state", "year", "line", "count"]).sort(["year", "line"])
    yearly.write_parquet(OUTPUT_DIR / "mi_complaints_yearly.parquet")
    yearly.write_csv(OUTPUT_DIR / "mi_complaints_yearly.csv")
    log_lines.append(f"  wrote mi_complaints_yearly: {yearly.height} rows")

    total = pl.DataFrame(total_rows).select(["state", "year", "entity_type", "count"]).sort(["year", "entity_type"])
    total.write_parquet(OUTPUT_DIR / "mi_complaints_total_yearly.parquet")
    total.write_csv(OUTPUT_DIR / "mi_complaints_total_yearly.csv")
    log_lines.append(f"  wrote mi_complaints_total_yearly: {total.height} rows")

    reason = pl.DataFrame(reason_rows).select([
        "state", "year", "reason_category", "entity_type", "count", "pct_within_entity",
    ]).sort(["year", "reason_category", "entity_type"])
    reason.write_parquet(OUTPUT_DIR / "mi_complaints_by_reason.parquet")
    reason.write_csv(OUTPUT_DIR / "mi_complaints_by_reason.csv")
    log_lines.append(f"  wrote mi_complaints_by_reason: {reason.height} rows")

    # Sanity: cross-check that company-row sums roughly track Line of Coverage counts
    log_lines.append("  cross-check: per-line company-complaint sums vs Line-of-Coverage totals")
    sums = company.group_by(["year", "line"]).agg(pl.col("complaints").sum().alias("sum_company_complaints"))
    joined = sums.join(yearly, on=["year", "line"], how="left").with_columns(
        diff=pl.col("count") - pl.col("sum_company_complaints"),
    )
    for row in joined.sort(["year", "line"]).to_dicts():
        log_lines.append(
            f"     {row['year']} {row['line']}: company-sum={row['sum_company_complaints']} "
            f"line-of-coverage={row['count']} diff={row['diff']}"
        )

    with LOG_PATH.open("a") as f:
        f.write("\n".join(log_lines) + "\n")
    print("\n".join(log_lines))


if __name__ == "__main__":
    main()
