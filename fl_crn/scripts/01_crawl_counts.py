"""Iterate (year, type_of_insurance) and record CRN search-result counts.

Reads no input. Writes:
  fl_crn/output/fl_crn_yearly_counts.{parquet,csv}
  fl_crn/output/fl_crn_yearly_total.{parquet,csv}
  fl_crn/output/run_log.txt   (appended)
  fl_crn/interim/manifest.json

The FDFS search page is an ASP.NET WebForms app. Each call:
  1. Bootstrap a fresh session: GET to capture cookies + __VIEWSTATE.
  2. POST a search with the date range and (optional) insurance-type filter.
  3. Parse "Records 1 - N of <total>" from the result page.

Polite: 2-second sleep between requests; identifying User-Agent.
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.parse
import urllib.request
import http.cookiejar
from datetime import datetime, timezone
from pathlib import Path

import polars as pl

USER_AGENT = (
    "insurance-complaint-rates/1.0 "
    "(research; contact: evan.ochsner@gmail.com)"
)
URL = "https://apps.fldfs.com/civilremedy/SearchFiling.aspx"

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INTERIM_DIR = PROJECT_ROOT / "fl_crn" / "interim"
OUTPUT_DIR = PROJECT_ROOT / "fl_crn" / "output"
MANIFEST = INTERIM_DIR / "manifest.json"
LOG_PATH = OUTPUT_DIR / "run_log.txt"

YEAR_START = 2003
# YEAR_END is the current year; filled in main().

# ddlInsuranceType options exactly as the form sends them (8-char fixed-width
# values; trailing-space-padded). Verified 2026-05-04 by inspecting the live
# <select> options.
LINE_CODES = {
    "Accident & Health":           "ACCHLTH ",
    "Life & Annuity":              "LIFEANTY",
    "Medicare Supplement":         "MEDICARE",
    "Auto":                        "AUTO    ",
    "Residential Property & Casualty":  "RESIDENT",
    "Commercial Property & Casualty":   "COMMERCE",
    "Professional Liability":      "PROFLIAB",
    "Miscellaneous":               "MISC    ",
    "Other":                       "OTHER   ",
}

INPUT_RE = re.compile(r'<input([^>]*)>')
SELECT_RE = re.compile(r'<select[^>]*name="([^"]+)"[^>]*>(.*?)</select>', re.S)
SELECTED_OPTION_RE = re.compile(r'<option[^>]*selected[^>]*value="([^"]*)"')
ATTR_NAME = re.compile(r'name="([^"]+)"')
ATTR_VALUE = re.compile(r'value="([^"]*)"')
ATTR_TYPE = re.compile(r'type="([^"]+)"')

RECORDS_OF_RE = re.compile(r"Records\s+\d+\s*-\s*\d+\s+of\s+(\d+)")
NO_RECORDS_HINTS = ("No filings match", "no records", "no filings")


def extract_form_fields(html: str) -> list[tuple[str, str, str]]:
    """Return list of (type, name, value) for every named input + selected
    option in the form. Skips submit buttons (callers add the one they need)."""
    fields: list[tuple[str, str, str]] = []
    for m in INPUT_RE.finditer(html):
        a = m.group(1)
        n = ATTR_NAME.search(a)
        if not n:
            continue
        v = ATTR_VALUE.search(a)
        t = ATTR_TYPE.search(a)
        fields.append((t.group(1) if t else "", n.group(1), v.group(1) if v else ""))
    for m in SELECT_RE.finditer(html):
        name = m.group(1)
        sel = SELECTED_OPTION_RE.search(m.group(2))
        fields.append(("select", name, sel.group(1) if sel else ""))
    return fields


def make_opener() -> urllib.request.OpenerDirector:
    jar = http.cookiejar.CookieJar()
    op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))
    op.addheaders = [("User-Agent", USER_AGENT), ("Referer", URL)]
    return op


def fetch_count(year: int, line_code: str | None, log_fh) -> int:
    """Submit a search for the year and (optional) insurance line; return the
    total record count from the result page header. Returns 0 if 'No filings'."""
    op = make_opener()

    # Bootstrap.
    raw = op.open(URL).read().decode("utf-8", errors="replace")
    fields = extract_form_fields(raw)

    start = f"01/01/{year}"
    end = f"12/31/{year}"
    post: list[tuple[str, str]] = []
    for t, n, v in fields:
        if t == "submit":
            continue
        if n == "ctl00$phPageContent$txtSubmissionStartDate":
            v = start
        elif n == "ctl00$phPageContent$txtSubmissionEndDate":
            v = end
        elif n == "ctl00$phPageContent$ddlInsuranceType" and line_code is not None:
            v = line_code
        post.append((n, v))
    post.append(("ctl00$phPageContent$btnSearch", "Search"))

    body = urllib.parse.urlencode(post).encode()
    req = urllib.request.Request(
        URL,
        data=body,
        headers={
            "User-Agent": USER_AGENT,
            "Referer": URL,
            "Content-Type": "application/x-www-form-urlencoded",
        },
    )
    resp_html = op.open(req).read().decode("utf-8", errors="replace")
    text = re.sub(r"<[^>]+>", " ", resp_html)
    text = re.sub(r"\s+", " ", text)

    m = RECORDS_OF_RE.search(text)
    if m:
        return int(m.group(1))
    if any(h.lower() in text.lower() for h in NO_RECORDS_HINTS):
        return 0
    # Unrecognized response: log and treat as failure.
    snippet = text[:300]
    log_fh.write(f"  ! unrecognized response for year={year} line={line_code}: {snippet!r}\n")
    raise RuntimeError(f"could not parse count for {year}/{line_code}")


def main() -> int:
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    year_end = datetime.now(timezone.utc).year
    rows: list[dict] = []

    with LOG_PATH.open("a") as logf:
        run_started = datetime.now(timezone.utc).isoformat(timespec="seconds")
        logf.write(f"\n=== run started {run_started} ===\n")
        print(f"crawling {YEAR_START}-{year_end} × {len(LINE_CODES)} lines")
        total_requests = 0

        for year in range(YEAR_START, year_end + 1):
            for line_label, line_code in LINE_CODES.items():
                # Retry up to 3x on transient failures.
                last_err: Exception | None = None
                count: int | None = None
                for attempt in range(3):
                    try:
                        count = fetch_count(year, line_code, logf)
                        last_err = None
                        break
                    except Exception as e:
                        last_err = e
                        time.sleep(5 * (attempt + 1))
                if last_err is not None:
                    print(f"  HARD FAIL {year} {line_label}: {last_err}")
                    return 2
                rows.append({"year": year, "type_of_insurance": line_label, "count": count})
                total_requests += 1
                print(f"  {year} {line_label:>32}: {count:>7,}")
                logf.write(f"  {year} {line_label}: {count}\n")
                time.sleep(2.0)

            # Per-year, no-line-filter total — also captures rows with null line.
            last_err = None
            count = None
            for attempt in range(3):
                try:
                    count = fetch_count(year, None, logf)
                    break
                except Exception as e:
                    last_err = e
                    time.sleep(5 * (attempt + 1))
            if last_err is not None:
                print(f"  HARD FAIL {year} TOTAL: {last_err}")
                return 2
            rows.append({"year": year, "type_of_insurance": "ALL", "count": count})
            total_requests += 1
            print(f"  {year} {'ALL (no filter)':>32}: {count:>7,}")
            logf.write(f"  {year} ALL: {count}\n")
            time.sleep(2.0)

        df = pl.DataFrame(rows)
        per_line = df.filter(pl.col("type_of_insurance") != "ALL").sort(
            ["year", "type_of_insurance"]
        )
        per_line.write_parquet(OUTPUT_DIR / "fl_crn_yearly_counts.parquet")
        per_line.write_csv(OUTPUT_DIR / "fl_crn_yearly_counts.csv")

        per_year_total = df.filter(pl.col("type_of_insurance") == "ALL").select(
            ["year", "count"]
        ).sort("year")
        per_year_total.write_parquet(OUTPUT_DIR / "fl_crn_yearly_total.parquet")
        per_year_total.write_csv(OUTPUT_DIR / "fl_crn_yearly_total.csv")

        # Soft cross-check: sum-of-lines vs no-filter total (logged, not hard-fail).
        sum_lines = (
            per_line.group_by("year")
            .agg(pl.col("count").sum().alias("sum_lines"))
            .sort("year")
        )
        compare = per_year_total.join(sum_lines, on="year").with_columns(
            delta=(pl.col("sum_lines") - pl.col("count"))
        )
        logf.write("\n--- sum-of-lines vs no-filter total ---\n")
        for r in compare.iter_rows(named=True):
            logf.write(
                f"  {r['year']}: no_filter={r['count']:>7,}  "
                f"sum_of_lines={r['sum_lines']:>7,}  delta={r['delta']:+}\n"
            )

        manifest = {
            "url": URL,
            "year_range": [YEAR_START, year_end],
            "line_codes": LINE_CODES,
            "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
            "total_requests": total_requests,
            "user_agent": USER_AGENT,
        }
        MANIFEST.write_text(json.dumps(manifest, indent=2) + "\n")
        logf.write(f"=== run completed; {total_requests} requests ===\n")
        print(f"\nWrote outputs ({total_requests} requests).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
