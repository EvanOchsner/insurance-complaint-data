"""Download every Michigan DIFS Insurance Complaint Statistics HTML page.

Source landing:
  https://difs.state.mi.us/complaintstats

DIFS publishes 3 years of data (currently 2022, 2023, 2024) across 8 page
types per year:
  - 5 per-company per-line ratio tables (coverageType=AUTO|HOME|LIFE|ACHL|ANTS)
  - 3 statistic summaries (statisticType=TOTALCOMPLAINT|LINECOVERAGE|REASON)

Total 24 HTML pages (~10s to fetch). DIFS appears not to rate-limit; we still
sleep 1s between requests as a courtesy.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/130.0.0.0 Safari/537.36"
)
BASE = "https://difs.state.mi.us"
SLEEP_BETWEEN = 1.0

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INTERIM_DIR = PROJECT_ROOT / "mi_difs" / "interim" / "files"
MANIFEST_PATH = PROJECT_ROOT / "mi_difs" / "interim" / "manifest.json"

YEARS = [2022, 2023, 2024]
COVERAGE_TYPES = [
    ("AUTO", "automobile"),
    ("HOME", "homeowners"),
    ("LIFE", "life"),
    ("ACHL", "accident_health"),
    ("ANTS", "annuity"),
]
STATISTIC_TYPES = [
    ("TOTALCOMPLAINT", "total"),
    ("LINECOVERAGE", "line_of_coverage"),
    ("REASON", "complaint_reason"),
]


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def main() -> None:
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    files: list[dict] = []
    for year in YEARS:
        for code, slug in COVERAGE_TYPES:
            url = f"{BASE}/ComplaintStats/ComplaintRatios/InsuranceCompanyList?coverageType={code}&forYear={year}"
            fname = f"company_{slug}_{year}.html"
            print(f"  fetching {fname}: {url}")
            body = fetch(url)
            (INTERIM_DIR / fname).write_bytes(body)
            files.append({
                "kind": "company_ratios",
                "coverage_type_code": code,
                "line_canonical": slug,
                "year": year,
                "url": url,
                "filename": fname,
                "bytes": len(body),
                "sha256": hashlib.sha256(body).hexdigest(),
            })
            time.sleep(SLEEP_BETWEEN)
        for code, slug in STATISTIC_TYPES:
            url = f"{BASE}/ComplaintStats/ComplaintRatios/InsuranceStatistics?statisticType={code}&forYear={year}"
            fname = f"stats_{slug}_{year}.html"
            print(f"  fetching {fname}: {url}")
            body = fetch(url)
            (INTERIM_DIR / fname).write_bytes(body)
            files.append({
                "kind": "statistics",
                "statistic_type_code": code,
                "kind_slug": slug,
                "year": year,
                "url": url,
                "filename": fname,
                "bytes": len(body),
                "sha256": hashlib.sha256(body).hexdigest(),
            })
            time.sleep(SLEEP_BETWEEN)
    manifest = {
        "project_tag": "insurance-complaint-rates/1.0 (research; contact: evan.ochsner@gmail.com)",
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "files": files,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"  wrote {MANIFEST_PATH}; {len(files)} files")


if __name__ == "__main__":
    main()
