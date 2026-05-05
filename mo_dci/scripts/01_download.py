"""Download every published Missouri DCI Complaint Index/Report PDF.

Source landing pages:
  - https://insurance.mo.gov/consumer-complaints/consumer-complaint-index
  - https://insurance.mo.gov/reports/historical-reports

Three reports are currently published (2026-05-05 snapshot):
  - 2021 Missouri Complaint Report   — covers 2018-2020 (3-year pooled per-company indices,
                                       plus 2017-2021 per-year per-line aggregates)
  - 2022 Missouri Complaints Report — covers 2020-2022 (per-company); 2018-2022 (per-year per-line)
  - 2023 Missouri Complaint Index   — covers 2021-2023 (per-company); 2019-2023 (per-year per-line)

URL pattern is `https://insurance.mo.gov/sites/insurance/files/<YYYY-MM>/<filename>.pdf` where the
YYYY-MM publication-month directory varies by year. URLs were resolved via the `/media/<id>`
short-link redirector (see PROVENANCE.md).

The MO DCI origin imposes a fairly aggressive rate limit (returns HTTP 429 even when the body
delivers). We use a Chrome-like UA, set Referer, sleep between requests, and accept a 429 status
as long as the body is a valid PDF (`%PDF-` magic). Failed fetches retry through the browser via
Claude-in-Chrome — see `interim/manifest.json` for which fetches were curl vs browser-assisted.
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
REFERER = "https://insurance.mo.gov/reports/historical-reports"
SLEEP_BETWEEN_REQUESTS = 30  # MO 429s aggressively; pad each fetch.

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INTERIM_DIR = PROJECT_ROOT / "mo_dci" / "interim"
MANIFEST_PATH = INTERIM_DIR / "manifest.json"

# (report year, canonical filename, resolved URL).
# Resolved 2026-05-05 from the `/media/<id>` short-link redirector.
SOURCES = [
    (
        2021,
        "2021_complaint_report.pdf",
        "https://insurance.mo.gov/sites/insurance/files/2024-09/2021ComplaintReport.pdf",
    ),
    (
        2022,
        "2022_complaint_report.pdf",
        "https://insurance.mo.gov/sites/insurance/files/2024-09/2022ComplaintReport.pdf",
    ),
    (
        2023,
        "2023_complaint_index.pdf",
        "https://insurance.mo.gov/sites/insurance/files/2024-11/2023%20Complaint%20Index.pdf",
    ),
]


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Referer": REFERER})
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        # MO returns 429 even with a valid body; keep the body if it's a real PDF.
        body = e.read()
        if e.code == 429 and body.startswith(b"%PDF"):
            return body
        raise


def main() -> None:
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {
        "project_tag": "insurance-complaint-rates/1.0 (research; contact: evan.ochsner@gmail.com)",
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "files": [],
    }
    for i, (year, fn, url) in enumerate(SOURCES):
        if i > 0:
            time.sleep(SLEEP_BETWEEN_REQUESTS)
        target = INTERIM_DIR / fn
        print(f"  fetching {year}: {url}")
        try:
            body = fetch(url)
        except Exception as e:
            print(f"    FAILED: {e}", file=sys.stderr)
            sys.exit(1)
        if not body.startswith(b"%PDF"):
            print(f"    not a PDF (first 64 bytes: {body[:64]!r})", file=sys.stderr)
            sys.exit(1)
        target.write_bytes(body)
        sha256 = hashlib.sha256(body).hexdigest()
        print(f"    ok: {len(body):,} bytes, sha256={sha256[:16]}…")
        manifest["files"].append(
            {
                "report_year": year,
                "filename": fn,
                "url": url,
                "bytes": len(body),
                "sha256": sha256,
            }
        )
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"  wrote {MANIFEST_PATH}")


if __name__ == "__main__":
    main()
