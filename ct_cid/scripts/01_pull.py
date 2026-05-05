"""Pull the CT CID 'Insurance Company Complaints, Resolutions, Status, and
Recoveries' dataset from data.ct.gov and write a Polars Parquet plus a manifest.

Source: https://data.ct.gov/widgets/t64r-mt64
Resource: https://data.ct.gov/resource/t64r-mt64.json

Anonymous Socrata access. ~77k rows; ~2 paginated GETs at 50k page size.
"""
from __future__ import annotations

import json
import sys
import urllib.request
import urllib.parse
from datetime import datetime, timezone
from pathlib import Path

import polars as pl

DATASET_ID = "t64r-mt64"
METADATA_URL = f"https://data.ct.gov/api/views/{DATASET_ID}.json"
RESOURCE_URL = f"https://data.ct.gov/resource/{DATASET_ID}.json"

USER_AGENT = (
    "insurance-complaint-rates/1.0 "
    "(research; contact: evan.ochsner@gmail.com)"
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INTERIM_DIR = PROJECT_ROOT / "ct_cid" / "interim"
OUT_PARQUET = INTERIM_DIR / f"{DATASET_ID}.parquet"
MANIFEST_PATH = INTERIM_DIR / "manifest.json"

PAGE_SIZE = 50_000


def http_get_json(url: str) -> object:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_metadata() -> dict:
    print(f"GET {METADATA_URL}")
    meta = http_get_json(METADATA_URL)
    cols = [(c["fieldName"], c["dataTypeName"]) for c in meta.get("columns", [])]
    print(f"  name: {meta.get('name')}")
    print(f"  rowsUpdatedAt (epoch): {meta.get('rowsUpdatedAt')}")
    print(f"  columns: {cols}")
    return {
        "name": meta.get("name"),
        "rows_updated_at": meta.get("rowsUpdatedAt"),
        "view_last_modified": meta.get("viewLastModified"),
        "columns": cols,
    }


def fetch_row_count() -> int:
    url = RESOURCE_URL + "?$select=count(*)"
    print(f"GET {url}")
    data = http_get_json(url)
    n = int(data[0]["count"])
    print(f"  count: {n:,}")
    return n


def fetch_page(offset: int, limit: int) -> list[dict]:
    qs = urllib.parse.urlencode({
        "$limit": limit,
        "$offset": offset,
        "$order": ":id",
    })
    url = f"{RESOURCE_URL}?{qs}"
    return http_get_json(url)


def main() -> int:
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)

    meta = fetch_metadata()
    expected = fetch_row_count()

    rows: list[dict] = []
    offset = 0
    while True:
        page = fetch_page(offset, PAGE_SIZE)
        rows.extend(page)
        print(f"  pulled {len(page):,} (total {len(rows):,} / {expected:,})")
        if len(page) < PAGE_SIZE:
            break
        offset += PAGE_SIZE

    if len(rows) != expected:
        print(
            f"ERROR: pulled {len(rows):,} rows but server reported {expected:,} "
            f"— pagination may have raced an update; re-run.",
            file=sys.stderr,
        )
        return 2

    # Force every column to pl.String to avoid schema-inference races on
    # rows that omit optional fields (Socrata serves sparse JSON).
    column_names = [c[0] for c in meta["columns"]]
    schema = {name: pl.String for name in column_names}
    normalized = [{c: r.get(c) for c in column_names} for r in rows]
    df = pl.DataFrame(normalized, schema=schema)
    print(f"DataFrame shape: {df.shape}")
    print(f"Columns: {df.columns}")

    df.write_parquet(OUT_PARQUET)
    print(f"Wrote {OUT_PARQUET} ({OUT_PARQUET.stat().st_size / 1e6:.1f} MB)")

    manifest = {
        "dataset_id": DATASET_ID,
        "metadata_url": METADATA_URL,
        "resource_url": RESOURCE_URL,
        "pulled_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "rows_pulled": len(rows),
        "rows_expected_at_fetch": expected,
        "page_size": PAGE_SIZE,
        "columns": df.columns,
        "metadata": meta,
        "user_agent": USER_AGENT,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"Manifest written to {MANIFEST_PATH}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
