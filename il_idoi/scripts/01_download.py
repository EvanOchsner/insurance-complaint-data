"""Download Illinois IDOI Consumer Complaint Ratio reports.

Source landing:
  https://idoi.illinois.gov/reports/consumer-complaint.html

IL publishes consolidated complaint-ratio PDFs for years where they did one,
plus per-line per-year per-format PDFs for older years. We pull only the
consolidated reports here:

  2018, 2019                — `{YEAR}-complaint-ratios.pdf`
  2020                       — `2020-complaints-ratio-report.pdf`
  2023, 2024                 — `{YEAR}-complaint-ratio-report.pdf`

2021 and 2022 don't have consolidated ratio reports posted (likely affected
by the COVID-era publication slowdown).
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
    "insurance-complaint-rates/1.0 "
    "(research; contact: evan.ochsner@gmail.com)"
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INTERIM_DIR = PROJECT_ROOT / "il_idoi" / "interim"
FILES_DIR = INTERIM_DIR / "files"
MANIFEST_PATH = INTERIM_DIR / "manifest.json"

LANDING_PAGE = "https://idoi.illinois.gov/reports/consumer-complaint.html"
URL_BASE = "https://idoi.illinois.gov/content/dam/soi/en/web/insurance/reports/reports/"

# Each (year, filename-stem) tuple. Stems differ across years — IL didn't
# settle on a stable filename convention.
SOURCES = [
    (2018, "2018-complaint-ratios"),
    (2019, "2019-complaint-ratios"),
    (2020, "2020-complaints-ratio-report"),
    (2023, "2023-complaint-ratio-report"),
    (2024, "2024-complaint-ratio-report"),
]

PER_REQUEST_DELAY_S = 1.0


def http_get(url: str, timeout: int = 30) -> tuple[bytes, dict]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read(), dict(resp.getheaders())


def main() -> int:
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    FILES_DIR.mkdir(parents=True, exist_ok=True)

    records: list[dict] = []
    for year, stem in SOURCES:
        url = URL_BASE + stem + ".pdf"
        print(f"GET {url}")
        try:
            body, headers = http_get(url)
        except Exception as e:
            print(f"  ERROR: {e}", file=sys.stderr)
            return 2
        if not body.startswith(b"%PDF"):
            print(f"  HARD FAILURE: not a PDF ({body[:20]!r})", file=sys.stderr)
            return 3
        out_path = FILES_DIR / f"{year}.pdf"
        out_path.write_bytes(body)
        sha = hashlib.sha256(body).hexdigest()
        print(f"  → {out_path.name}  {len(body)/1024:.1f} KB  sha256={sha[:12]}…")
        records.append({
            "year": year,
            "url": url,
            "filename": out_path.name,
            "size_bytes": len(body),
            "sha256": sha,
            "last_modified_header": headers.get("Last-Modified"),
            "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        })
        time.sleep(PER_REQUEST_DELAY_S)

    manifest = {
        "source_landing": LANDING_PAGE,
        "discovered_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "user_agent": USER_AGENT,
        "n_files": len(records),
        "files": records,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"\nWrote {MANIFEST_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
