"""Download Wisconsin OCI Insurance Report PDFs.

Source landing:
  https://oci.wi.gov/Pages/AboutOCI/WisconsinInsuranceReport.aspx

Each year's main "View the Wisconsin Insurance Report" PDF is the canonical
source. Filenames are inconsistent year-to-year (no stable convention). The
downloader hardcodes the per-year URL.

Each main WIR PDF contains a "Division of Market Regulation and Enforcement"
section with Table II (complaints by line of insurance), Table III (reasons),
Table IV (recoveries by line × reason), Table V (additional reviews). v1
extracts Table II only — the per-line complaint counts. Other tables are
preserved in the source PDFs for later expansion.
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
INTERIM_DIR = PROJECT_ROOT / "wi_oci" / "interim"
FILES_DIR = INTERIM_DIR / "files"
MANIFEST_PATH = INTERIM_DIR / "manifest.json"

LANDING_PAGE = "https://oci.wi.gov/Pages/AboutOCI/WisconsinInsuranceReport.aspx"

# (report-year, URL). Each report's Table II covers report-year and the prior
# year, so 5 reports give us 6 distinct data years (2019-2024).
SOURCES = [
    (2020, "https://oci.wi.gov/Documents/AboutOCI/WIR_2020_FINAL_Web.pdf"),
    (2021, "https://oci.wi.gov/Documents/AboutOCI/2021_WisconsinInsuranceReport.pdf"),
    (2022, "https://oci.wi.gov/Documents/AboutOCI/2022_WisconsinInsuranceReport-Web.pdf"),
    (2023, "https://oci.wi.gov/Documents/AboutOCI/2023_WIR_Final_Web.pdf"),
    (2024, "https://oci.wi.gov/Documents/AboutOCI/2024_WIR.pdf"),
]

PER_REQUEST_DELAY_S = 1.0


def http_get(url: str, timeout: int = 120) -> tuple[bytes, dict]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read(), dict(resp.getheaders())


def main() -> int:
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    FILES_DIR.mkdir(parents=True, exist_ok=True)

    records: list[dict] = []
    for report_year, url in SOURCES:
        print(f"GET {url}")
        try:
            body, headers = http_get(url)
        except Exception as e:
            print(f"  ERROR: {e}", file=sys.stderr)
            return 2
        if not body.startswith(b"%PDF"):
            print(f"  HARD FAILURE: not a PDF (first bytes {body[:30]!r})", file=sys.stderr)
            return 3
        out_path = FILES_DIR / f"WIR_{report_year}.pdf"
        out_path.write_bytes(body)
        sha = hashlib.sha256(body).hexdigest()
        size_mb = len(body) / (1024 * 1024)
        print(f"  → {out_path.name}  {size_mb:.1f} MB  sha256={sha[:12]}…")
        records.append({
            "report_year": report_year,
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
    print(f"\nWrote {MANIFEST_PATH} ({len(records)} files)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
