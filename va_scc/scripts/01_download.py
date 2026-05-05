"""Download every Virginia SCC Bureau of Insurance (BOI) annual report PDF.

Source landing:
  https://www.scc.virginia.gov/about-the-scc/annual-reports/

VA's fiscal year ends June 30. Each BOI report is filed alongside the broader
SCC umbrella annual report and has predictable URL `{YYYY}BOI.pdf` where YYYY
is the fiscal-year-ending year. Reports for FY 2022 – FY 2025 are currently
online (4 PDFs at first build).
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
INTERIM_DIR = PROJECT_ROOT / "va_scc" / "interim"
FILES_DIR = INTERIM_DIR / "files"
MANIFEST_PATH = INTERIM_DIR / "manifest.json"

URL_TEMPLATE = (
    "https://www.scc.virginia.gov/media/sccvirginiagov-home/"
    "about-the-scc/annual-reports/{year}BOI.pdf"
)
LANDING_PAGE = "https://www.scc.virginia.gov/about-the-scc/annual-reports/"

# FY ending years currently online (verified 2026-05-04). Add new years to
# this list as VA publishes them.
YEARS = [2022, 2023, 2024, 2025]

PER_REQUEST_DELAY_S = 1.0


def http_get(url: str, timeout: int = 30) -> tuple[bytes, dict]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read()
        headers = dict(resp.getheaders())
        return body, headers


def main() -> int:
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    FILES_DIR.mkdir(parents=True, exist_ok=True)

    records: list[dict] = []
    for year in YEARS:
        url = URL_TEMPLATE.format(year=year)
        print(f"GET {url}")
        try:
            body, headers = http_get(url)
        except Exception as e:
            print(f"  ERROR: {e}", file=sys.stderr)
            return 2
        if not body.startswith(b"%PDF"):
            print(
                f"  HARD FAILURE: response is not a PDF (first bytes "
                f"{body[:20]!r}). VA SCC layout may have changed.",
                file=sys.stderr,
            )
            return 3
        out_path = FILES_DIR / f"FY{year}.pdf"
        out_path.write_bytes(body)
        sha = hashlib.sha256(body).hexdigest()
        size_kb = len(body) / 1024
        print(f"  → {out_path.name}  {size_kb:.1f} KB  sha256={sha[:12]}…")
        records.append({
            "fiscal_year": year,
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
        "url_template": URL_TEMPLATE,
        "discovered_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "user_agent": USER_AGENT,
        "n_files": len(records),
        "files": records,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"\nWrote {MANIFEST_PATH} ({len(records)} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
