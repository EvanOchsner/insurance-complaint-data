"""Download WA OIC IFCA notice PDFs + Annual Report PDFs into interim/.

The OIC's Varnish cache returns 403 for unrecognized User-Agents, so we set
a browser-like UA. The OIC also keeps only the two most recent IFCA PDFs
online; older years return a 301 redirect to the IFCA landing page.

Verified live 2026-05-04.
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

# Browser-like UA. Identifying ourselves via the User-Agent triggers the
# OIC Varnish cache to return 403; this is one of the few cases where we
# don't lead with the project's own UA.
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
PROJECT_TAG = "insurance-complaint-rates/1.0 (research; contact: evan.ochsner@gmail.com)"

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INTERIM = PROJECT_ROOT / "wa_oic" / "interim"
IFCA_DIR = INTERIM / "ifca"
AR_DIR = INTERIM / "annual_reports"
MANIFEST_PATH = INTERIM / "manifest.json"

# Verified live 2026-05-04. Older IFCA PDFs (2008-2024) are no longer hosted.
IFCA_PDFS = {
    2025: "https://www.insurance.wa.gov/sites/default/files/2025-03/2025-notices-of-potential-lawsuits.pdf",
    2026: "https://www.insurance.wa.gov/sites/default/files/2026-04/2026-notices-of-potential-lawsuits.pdf",
}
ANNUAL_REPORTS = {
    2020: "https://www.insurance.wa.gov/sites/default/files/2024-09/oic-annual-report-2020-final-web.pdf",
    2021: "https://www.insurance.wa.gov/sites/default/files/2024-09/OIC-annual-report-2021.pdf",
    2022: "https://www.insurance.wa.gov/sites/default/files/2024-09/oic-annual-report-2022.pdf",
    2023: "https://www.insurance.wa.gov/sites/default/files/2024-12/oic-annual-report-2023.pdf",
    2024: "https://www.insurance.wa.gov/sites/default/files/2025-07/OIC-annual-report-2024-final.pdf",
}


def head(url: str) -> dict[str, str]:
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req) as resp:
        return {k.lower(): v for k, v in resp.headers.items()}


def download_pdf(url: str, dest: Path) -> dict:
    h = head(url)
    ct = h.get("content-type", "")
    if "application/pdf" not in ct:
        raise RuntimeError(f"{url}: Content-Type={ct!r} (expected application/pdf — server may have removed the file)")
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
    with dest.open("rb") as f:
        head_bytes = f.read(8)
    if not head_bytes.startswith(b"%PDF-"):
        raise RuntimeError(f"{url} downloaded but missing %PDF- magic")
    return {
        "url": url,
        "size": size,
        "sha256": sha.hexdigest(),
        "last_modified": h.get("last-modified"),
    }


def main() -> int:
    INTERIM.mkdir(parents=True, exist_ok=True)
    manifest = {
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "user_agent": USER_AGENT,
        "project_tag": PROJECT_TAG,
        "ifca": {},
        "annual_reports": {},
    }

    print("IFCA notice PDFs:")
    for year, url in IFCA_PDFS.items():
        dest = IFCA_DIR / f"{year}.pdf"
        info = download_pdf(url, dest)
        info["local_path"] = str(dest.relative_to(PROJECT_ROOT))
        manifest["ifca"][str(year)] = info
        time.sleep(1.0)

    print("\nAnnual Report PDFs:")
    for year, url in ANNUAL_REPORTS.items():
        dest = AR_DIR / f"{year}.pdf"
        info = download_pdf(url, dest)
        info["local_path"] = str(dest.relative_to(PROJECT_ROOT))
        manifest["annual_reports"][str(year)] = info
        time.sleep(1.0)

    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"\nWrote {MANIFEST_PATH}")
    n_ifca = len(manifest["ifca"])
    n_ar = len(manifest["annual_reports"])
    total = sum(v["size"] for v in manifest["ifca"].values())
    total += sum(v["size"] for v in manifest["annual_reports"].values())
    print(f"  {n_ifca} IFCA + {n_ar} AR = {total / 1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
