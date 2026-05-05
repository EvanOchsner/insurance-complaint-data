"""Download NY DFS auto complaint data (Socrata) and health-guide PDFs.

Writes:
  ny_dfs/interim/h2wd-9xfe.parquet                 # auto, full Socrata pull
  ny_dfs/interim/health/{guide_year}.pdf           # 10 health-guide PDFs
  ny_dfs/interim/manifest.json                     # provenance
"""
from __future__ import annotations

import hashlib
import json
import sys
import time
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

import polars as pl

USER_AGENT = (
    "insurance-complaint-rates/1.0 "
    "(research; contact: evan.ochsner@gmail.com)"
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INTERIM = PROJECT_ROOT / "ny_dfs" / "interim"
HEALTH_DIR = INTERIM / "health"
AUTO_PARQUET = INTERIM / "h2wd-9xfe.parquet"
MANIFEST_PATH = INTERIM / "manifest.json"

AUTO_DATASET_ID = "h2wd-9xfe"
AUTO_RESOURCE = f"https://data.ny.gov/resource/{AUTO_DATASET_ID}.json"
AUTO_METADATA = f"https://data.ny.gov/api/views/{AUTO_DATASET_ID}.json"

HEALTH_GUIDE_URL_TMPL = "https://www.dfs.ny.gov/consumers/health_insurance/guide_{year}"
HEALTH_GUIDE_YEARS = list(range(2016, 2026))  # guide-publication years; data year = guide_year - 1


def http_get_json(url: str) -> object:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def head(url: str) -> dict[str, str]:
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req) as resp:
        return {k.lower(): v for k, v in resp.headers.items()}


def download_pdf(url: str, dest: Path) -> dict:
    h = head(url)
    ct = h.get("content-type", "")
    if "application/pdf" not in ct:
        raise RuntimeError(f"{url}: Content-Type={ct!r} (expected application/pdf)")
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


def pull_auto() -> tuple[int, dict]:
    print("Auto: GET metadata")
    meta = http_get_json(AUTO_METADATA)
    cols = [(c["fieldName"], c["dataTypeName"]) for c in meta.get("columns", [])]
    print(f"  schema: {cols}")
    print("Auto: GET row count")
    cnt = http_get_json(AUTO_RESOURCE + "?$select=count(*)")
    expected = int(cnt[0]["count"])
    print(f"  rows expected: {expected:,}")

    print("Auto: GET full resource")
    qs = urllib.parse.urlencode({"$limit": 50000, "$order": ":id"})
    rows = http_get_json(f"{AUTO_RESOURCE}?{qs}")
    print(f"  rows pulled: {len(rows):,}")
    if len(rows) != expected:
        raise RuntimeError(f"row count mismatch: pulled {len(rows)} expected {expected}")

    column_names = [c[0] for c in cols]
    schema = {n: pl.String for n in column_names}
    normalized = [{c: r.get(c) for c in column_names} for r in rows]
    df = pl.DataFrame(normalized, schema=schema)
    df.write_parquet(AUTO_PARQUET)
    print(f"  wrote {AUTO_PARQUET} ({AUTO_PARQUET.stat().st_size / 1e6:.2f} MB)")
    return expected, {
        "dataset_id": AUTO_DATASET_ID,
        "metadata_url": AUTO_METADATA,
        "resource_url": AUTO_RESOURCE,
        "rows_pulled": len(rows),
        "rows_expected_at_fetch": expected,
        "view_last_modified": meta.get("viewLastModified"),
        "rows_updated_at": meta.get("rowsUpdatedAt"),
        "columns": column_names,
    }


def main() -> int:
    INTERIM.mkdir(parents=True, exist_ok=True)
    HEALTH_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "user_agent": USER_AGENT,
    }

    # Auto
    expected, auto_meta = pull_auto()
    manifest["auto"] = auto_meta

    # Health PDFs
    print("\nHealth guides:")
    health_meta = {}
    for guide_year in HEALTH_GUIDE_YEARS:
        url = HEALTH_GUIDE_URL_TMPL.format(year=guide_year)
        dest = HEALTH_DIR / f"{guide_year}.pdf"
        info = download_pdf(url, dest)
        info["guide_year"] = guide_year
        info["data_year"] = guide_year - 1  # guide YYYY reports on YYYY-1
        info["local_path"] = str(dest.relative_to(PROJECT_ROOT))
        health_meta[str(guide_year)] = info
        time.sleep(1.0)
    manifest["health_guides"] = health_meta

    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"\nWrote {MANIFEST_PATH}")
    total_health_size = sum(v["size"] for v in health_meta.values())
    print(f"  auto rows: {expected:,}; health PDFs: {len(health_meta)}, {total_health_size / 1e6:.1f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
