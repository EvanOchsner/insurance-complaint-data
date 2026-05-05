"""Download every KID Complaint Index Report PDF.

Source landing:
  https://insurance.ks.gov/department/publications.php

Files cover years 2020–2024 (5 PDFs at first build) at predictable URLs:
  https://insurance.ks.gov/documents/department/publications/complaint-index-report-{YYYY}.pdf

The KID web origin requires a browser-like User-Agent (anonymous bot UAs
are 403'd at the edge). We use a Chrome UA for downloads but record the
actual identifier we'd prefer in PROVENANCE.md.
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
    "Chrome/120.0.0.0 Safari/537.36"
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INTERIM_DIR = PROJECT_ROOT / "ks_kid" / "interim"
FILES_DIR = INTERIM_DIR / "files"
MANIFEST_PATH = INTERIM_DIR / "manifest.json"

URL_TEMPLATE = (
    "https://insurance.ks.gov/documents/department/publications/"
    "complaint-index-report-{year}.pdf"
)
PUBLICATIONS_PAGE = "https://insurance.ks.gov/department/publications.php"

YEARS = [2020, 2021, 2022, 2023, 2024]

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
                f"{body[:20]!r}). Source layout may have changed.",
                file=sys.stderr,
            )
            return 3
        out_path = FILES_DIR / f"{year}.pdf"
        out_path.write_bytes(body)
        sha = hashlib.sha256(body).hexdigest()
        size_kb = len(body) / 1024
        print(f"  → {out_path.name}  {size_kb:.1f} KB  sha256={sha[:12]}…")
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
        "source_landing": PUBLICATIONS_PAGE,
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
