"""Download NAIC IDRR Vol 1 PDFs into interim/idrr/.

Coverage: 1986-2023, sourced from the NAIC archive on Soutron Global plus the
current-year canonical URL on content.naic.org. The Soutron archive returns
PDFs from a query-string DownloadImageFile endpoint; the content.naic.org
2023 URL is the canonical "latest" Vol 1 path that NAIC overwrites each year.

CIS Tableau dashboards (Closed Confirmed Complaints by Reason / Disposition /
Coverage Type) are also captured here as raw HTML snapshots only - the actual
data lives in client-side rendered Tableau visualizations and is not extracted
in v1. The HTML snapshots are stored for provenance + as a starting point for
v2 Tableau-bootstrap-protocol scraping.
"""
from __future__ import annotations

import csv
import hashlib
import json
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
PROJECT_TAG = "insurance-complaint-rates/1.0 (research; contact: evan.ochsner@gmail.com)"

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATASET_ROOT = PROJECT_ROOT / "naic_idrr"
INTERIM = DATASET_ROOT / "interim"
IDRR_DIR = INTERIM / "idrr"
CIS_DIR = INTERIM / "cis"
INDEX_CSV = DATASET_ROOT / "reference" / "idrr_pdf_index.csv"
MANIFEST_PATH = INTERIM / "manifest.json"

# Tableau-rendered CIS dashboards. We capture the HTML wrappers for provenance.
# Real data extraction is deferred (would require Tableau bootstrapSession
# protocol implementation); see naic_idrr/METHODOLOGY.md.
CIS_DASHBOARDS = {
    "by_reason": "https://content.naic.org/cis_agg_reason.htm",
    "by_disposition": "https://content.naic.org/cis_agg_disposition.htm",
    "by_coverage": "https://content.naic.org/cis_agg_type.htm",
}


def http_get(url: str, dest: Path, *, expected_pdf: bool) -> dict:
    print(f"  GET {url}")
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    dest.parent.mkdir(parents=True, exist_ok=True)
    sha = hashlib.sha256()
    size = 0
    with urllib.request.urlopen(req, timeout=60) as resp, dest.open("wb") as out:
        ct = resp.headers.get("Content-Type", "")
        last_mod = resp.headers.get("Last-Modified")
        while True:
            chunk = resp.read(1 << 20)
            if not chunk:
                break
            out.write(chunk)
            sha.update(chunk)
            size += len(chunk)
    if expected_pdf:
        with dest.open("rb") as f:
            magic = f.read(8)
        if not magic.startswith(b"%PDF-"):
            raise RuntimeError(
                f"{url} -> {dest.name}: bytes don't start with %PDF- (got {magic!r}; "
                f"Content-Type was {ct!r})"
            )
    return {
        "url": url,
        "content_type": ct,
        "size_bytes": size,
        "sha256": sha.hexdigest(),
        "last_modified": last_mod,
    }


def load_index() -> list[dict]:
    rows = []
    with INDEX_CSV.open() as f:
        for row in csv.DictReader(f):
            row["year"] = int(row["year"])
            rows.append(row)
    return rows


def main() -> int:
    INTERIM.mkdir(parents=True, exist_ok=True)
    manifest = {
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "user_agent": USER_AGENT,
        "project_tag": PROJECT_TAG,
        "idrr_pdfs": {},
        "cis_dashboards": {},
    }

    rows = load_index()
    print(f"IDRR PDFs (n={len(rows)}):")
    for row in rows:
        year = row["year"]
        vol = row["vol"]
        # Distinguish Vol 1 vs Vol 2 vs combined Vol 1+2 by suffix.
        suffix = {"1": "", "2": "_vol2", "12": "_vol12"}.get(vol, f"_vol{vol}")
        local_name = f"{year}{suffix}.pdf"
        dest = IDRR_DIR / local_name
        try:
            info = http_get(row["url"], dest, expected_pdf=True)
        except Exception as e:
            print(f"  !! {year} vol={vol}: {e}")
            manifest["idrr_pdfs"][local_name] = {
                "url": row["url"],
                "year": year,
                "vol": vol,
                "error": str(e),
            }
            continue
        info["year"] = year
        info["vol"] = vol
        info["source"] = row["source"]
        info["local_path"] = str(dest.relative_to(PROJECT_ROOT))
        manifest["idrr_pdfs"][local_name] = info
        time.sleep(0.3)

    print(f"\nCIS dashboard HTML snapshots (n={len(CIS_DASHBOARDS)}):")
    for name, url in CIS_DASHBOARDS.items():
        dest = CIS_DIR / f"{name}.html"
        info = http_get(url, dest, expected_pdf=False)
        info["local_path"] = str(dest.relative_to(PROJECT_ROOT))
        manifest["cis_dashboards"][name] = info
        time.sleep(0.5)

    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n")
    n_pdfs_ok = sum(1 for v in manifest["idrr_pdfs"].values() if "error" not in v)
    n_pdfs_err = len(manifest["idrr_pdfs"]) - n_pdfs_ok
    total_pdf_bytes = sum(v.get("size_bytes", 0) for v in manifest["idrr_pdfs"].values())
    print(f"\nWrote {MANIFEST_PATH}")
    print(f"  IDRR PDFs: {n_pdfs_ok} ok, {n_pdfs_err} errored ({total_pdf_bytes / 1e6:.1f} MB)")
    print(f"  CIS dashboards: {len(manifest['cis_dashboards'])} captured")
    return 0


if __name__ == "__main__":
    sys.exit(main())
