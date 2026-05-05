"""Download every Oregon DFR Insurance Complaint Report PDF.

Source landing:
  https://dfr.oregon.gov/help/complaints-licenses/Pages/complaint-information.aspx

Oregon's Division of Financial Regulation publishes per-line per-year PDF
reports of consumer complaints filed against insurers. Each report contains
per-company columns: Premium, Total Complaints, **Confirmed Complaints**,
Complaint Index. The "Confirmed Complaints" field is true outcome data
(merits-decision-against-insurer count) — directly comparable to TX's
`Confirmed`, MD's "in favor of insured", and CT's "against insurer" series.

Coverage: 6 lines × 7 years (2019–2025) = 42 PDFs as of the 2026-05-05 build.

URL pattern:
  https://dfr.oregon.gov/help/Documents/complaint-stats-{YEAR}/Complaint-{SLUG}-{YEAR}.pdf

Slugs (case-insensitive on server, but use the form documented on the page):
  AutoFull, AnnuitiesFull, HealthFull, HomeownersFull, LifeFull, LTCfull
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

USER_AGENT = "insurance-complaint-rates/1.0 (research; contact: evan.ochsner@gmail.com)"

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INTERIM_DIR = PROJECT_ROOT / "or_dfr" / "interim" / "files"
MANIFEST_PATH = PROJECT_ROOT / "or_dfr" / "interim" / "manifest.json"

YEARS = list(range(2019, 2026))  # 2019..2025
LINES = [
    ("auto",            "AutoFull"),
    ("annuities",       "AnnuitiesFull"),
    ("health",          "HealthFull"),
    ("homeowners",      "HomeownersFull"),
    ("life",            "LifeFull"),
    ("long_term_care",  "LTCfull"),
]
SLEEP_BETWEEN = 1.0


def fetch(url: str) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=60) as resp:
        return resp.read()


def main() -> None:
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    files: list[dict] = []
    for year in YEARS:
        for slug, url_slug in LINES:
            url = f"https://dfr.oregon.gov/help/Documents/complaint-stats-{year}/Complaint-{url_slug}-{year}.pdf"
            fname = f"{slug}_{year}.pdf"
            print(f"  fetching {fname}: {url}")
            try:
                body = fetch(url)
            except Exception as e:
                print(f"    FAILED: {e}", file=sys.stderr)
                sys.exit(1)
            if not body.startswith(b"%PDF"):
                print(f"    not a PDF (first 64={body[:64]!r})", file=sys.stderr)
                sys.exit(1)
            (INTERIM_DIR / fname).write_bytes(body)
            sha = hashlib.sha256(body).hexdigest()
            print(f"    ok: {len(body):,} bytes, sha256={sha[:16]}…")
            files.append({
                "filename": fname,
                "line_canonical": slug,
                "url_slug": url_slug,
                "year": year,
                "url": url,
                "bytes": len(body),
                "sha256": sha,
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
