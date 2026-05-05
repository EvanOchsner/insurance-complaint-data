"""Download CA CDI Annual Reports + Consumer Complaint Studies into interim/.

The CDI server returns HTTP 200 with an HTML 'not found' page for missing
files, so a status code alone is not enough. We require the server to send
Content-Type: application/pdf and verify the saved file starts with %PDF-.

Verified 2026-05-04: the 14 URLs below all return application/pdf.
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
INTERIM_DIR = PROJECT_ROOT / "ca_cdi" / "interim"
AR_DIR = INTERIM_DIR / "annual_reports"
COMP_DIR = INTERIM_DIR / "composites"
MANIFEST_PATH = INTERIM_DIR / "manifest.json"

AR_BASE = "https://www.insurance.ca.gov/0400-news/0200-studies-reports/0700-commissioner-report/upload/"
COMP_BASE = "https://www.insurance.ca.gov/01-consumers/120-company/03-concmplt/upload/"

# Verified live 2026-05-04. Server lies with HTTP 200 for missing files —
# always re-check Content-Type when adding URLs.
ANNUAL_REPORTS = [
    (2020, AR_BASE + "2020-Annual-Report-of-the-Insurance-Commissioner.pdf"),
    (2021, AR_BASE + "2021Annual-Report-of-the-Insurance-Commissioner.pdf"),
    (2022, AR_BASE + "2022-Annual-Report-of-the-Insurance-Commissioner.pdf"),
    (2023, AR_BASE + "2023-Annual-Report-of-the-Insurance-Commissioner.pdf"),
    (2024, AR_BASE + "2024-Annual-Report-of-the-Commissioner.pdf"),
]

COMPOSITE_STUDIES = [
    (year, line)
    for year in (2023, 2024, 2025)
    for line in ("Auto", "Home", "Life")
]


def head(url: str) -> dict[str, str]:
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req) as resp:
        return {k.lower(): v for k, v in resp.headers.items()}


def download_pdf(url: str, dest: Path) -> dict:
    h = head(url)
    ct = h.get("content-type", "")
    if "application/pdf" not in ct:
        raise RuntimeError(f"{url} returned Content-Type={ct!r} (expected application/pdf)")
    print(f"  GET {url}")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    dest.parent.mkdir(parents=True, exist_ok=True)
    sha = hashlib.sha256()
    size = 0
    with urllib.request.urlopen(req) as resp, dest.open("wb") as out:
        while True:
            chunk = resp.read(1 << 20)
            if not chunk:
                break
            out.write(chunk)
            sha.update(chunk)
            size += len(chunk)
    # Verify it's actually a PDF.
    with dest.open("rb") as f:
        head_bytes = f.read(8)
    if not head_bytes.startswith(b"%PDF-"):
        raise RuntimeError(f"{url} downloaded but file does not start with %PDF- magic")
    return {
        "url": url,
        "size": size,
        "sha256": sha.hexdigest(),
        "last_modified": h.get("last-modified"),
        "etag": h.get("etag"),
    }


def main() -> int:
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "user_agent": USER_AGENT,
        "annual_reports": {},
        "composites": {},
    }

    print("Annual Reports:")
    for year, url in ANNUAL_REPORTS:
        dest = AR_DIR / f"{year}.pdf"
        info = download_pdf(url, dest)
        info["local_path"] = str(dest.relative_to(PROJECT_ROOT))
        manifest["annual_reports"][str(year)] = info
        time.sleep(1.0)  # be polite

    print("Composite Studies:")
    for year, line in COMPOSITE_STUDIES:
        url = COMP_BASE + f"{year}-Consumer-Complaint-Study-{line}.pdf"
        dest = COMP_DIR / f"{year}-{line.lower()}.pdf"
        info = download_pdf(url, dest)
        info["local_path"] = str(dest.relative_to(PROJECT_ROOT))
        info["line"] = line.lower()
        manifest["composites"][f"{year}-{line.lower()}"] = info
        time.sleep(1.0)

    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"\nWrote {MANIFEST_PATH}")
    n_ar = len(manifest["annual_reports"])
    n_comp = len(manifest["composites"])
    total_size = sum(v["size"] for v in manifest["annual_reports"].values())
    total_size += sum(v["size"] for v in manifest["composites"].values())
    print(f"  {n_ar} Annual Reports + {n_comp} Composite Studies = {total_size / 1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
