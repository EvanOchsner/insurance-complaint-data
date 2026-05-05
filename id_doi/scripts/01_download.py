"""Download the Idaho DOI Consumer Complaint Comparison Tables landing page.

Source landing:
  https://doi.idaho.gov/information/public/reports/complaint-index/

Idaho doesn't publish the comparison tables as separate PDFs — the per-year
per-line data is embedded as a single HTML table on this one page. Coverage
at first build is 3 years (2018, 2019, 2020) × 4 lines × top-20 companies =
240 rows.
"""
from __future__ import annotations

import hashlib
import json
import sys
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

USER_AGENT = (
    "insurance-complaint-rates/1.0 "
    "(research; contact: evan.ochsner@gmail.com)"
)

LANDING_URL = "https://doi.idaho.gov/information/public/reports/complaint-index/"

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INTERIM_DIR = PROJECT_ROOT / "id_doi" / "interim"
LANDING_HTML = INTERIM_DIR / "landing.html"
MANIFEST_PATH = INTERIM_DIR / "manifest.json"


def http_get(url: str, timeout: int = 30) -> tuple[bytes, dict]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read(), dict(resp.getheaders())


def main() -> int:
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)

    print(f"GET {LANDING_URL}")
    body, headers = http_get(LANDING_URL)
    if len(body) < 1024:
        print(f"  HARD FAILURE: response is suspiciously small ({len(body)} bytes)", file=sys.stderr)
        return 2
    LANDING_HTML.write_bytes(body)
    sha = hashlib.sha256(body).hexdigest()
    print(f"  → {LANDING_HTML.name}  {len(body)/1024:.1f} KB  sha256={sha[:12]}…")

    manifest = {
        "source": LANDING_URL,
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "user_agent": USER_AGENT,
        "filename": LANDING_HTML.name,
        "size_bytes": len(body),
        "sha256": sha,
        "last_modified_header": headers.get("Last-Modified"),
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Wrote {MANIFEST_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
