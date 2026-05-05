"""Download Colorado DOI Annual Complaint and Recoveries Reports.

Source landing:
  https://doi.colorado.gov/for-consumers/consumer-resources/insurance-complaint-reports

CO publishes one annual report per fiscal year (CO fiscal year ends June 30).
Filenames are inconsistent across years — early reports are titled "Annual
Complaint and Inquiry Report"; later ones "Annual Complaint and Recoveries
Report"; the FY 2024-25 file even drops the "FY" prefix. The downloader
hardcodes the per-year URL.

CO origin requires a browser-style User-Agent (anonymous bots get a CDN
"ERROR: The request could not be satisfied" page). Same workaround as KS.
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
INTERIM_DIR = PROJECT_ROOT / "co_doi" / "interim"
FILES_DIR = INTERIM_DIR / "files"
MANIFEST_PATH = INTERIM_DIR / "manifest.json"

LANDING_PAGE = "https://doi.colorado.gov/for-consumers/consumer-resources/insurance-complaint-reports"

# (FY-end-year, URL).
SOURCES = [
    (2022, "https://doi.colorado.gov/sites/doi/files/documents/FY%202021-22%20Annual%20Complaint%20and%20Inquiry%20Report.pdf"),
    (2023, "https://doi.colorado.gov/sites/doi/files/documents/FY%202022-23%20Colorado%20DOI%20Annual%20Complaint%20and%20Recoveries%20Report.pdf"),
    (2024, "https://doi.colorado.gov/sites/doi/files/documents/FY%202023-24%20Colorado%20DOI%20Annual%20Complaint%20and%20Recoveries%20Report.pdf"),
    (2025, "https://doi.colorado.gov/sites/doi/files/documents/2025%20Colorado%20Division%20of%20Insurance%20Annual%20Complaint%20and%20Recoveries%20Report.pdf"),
]

PER_REQUEST_DELAY_S = 1.0


def http_get(url: str, timeout: int = 60) -> tuple[bytes, dict]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read(), dict(resp.getheaders())


def main() -> int:
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    FILES_DIR.mkdir(parents=True, exist_ok=True)

    records: list[dict] = []
    for fy, url in SOURCES:
        print(f"GET {url}")
        try:
            body, headers = http_get(url)
        except Exception as e:
            print(f"  ERROR: {e}", file=sys.stderr)
            return 2
        if not body.startswith(b"%PDF"):
            print(
                f"  HARD FAILURE: not a PDF (first bytes {body[:30]!r}). "
                f"CO website may be UA-blocking or layout may have changed.",
                file=sys.stderr,
            )
            return 3
        out_path = FILES_DIR / f"FY{fy}.pdf"
        out_path.write_bytes(body)
        sha = hashlib.sha256(body).hexdigest()
        print(f"  → {out_path.name}  {len(body)/1024:.1f} KB  sha256={sha[:12]}…")
        records.append({
            "fiscal_year": fy,
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
