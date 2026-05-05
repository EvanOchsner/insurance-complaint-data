"""Download the FJC IDB combined civil dataset (cv88on) and record provenance.

Source: Federal Judicial Center, Integrated Database, Civil Cases since 1988.
Landing page: https://www.fjc.gov/research/idb/interactive/IDB-civil-since-1988

This script writes:
  fjc_idb/interim/cv88on.zip
  fjc_idb/interim/cv88on.txt   (extracted)
  fjc_idb/interim/manifest.json

Re-run is idempotent: if the local zip's sha256 already matches the live
server's content (via Last-Modified / Content-Length comparison) the download
is skipped.
"""
from __future__ import annotations

import hashlib
import json
import sys
import urllib.request
import zipfile
from datetime import datetime, timezone
from pathlib import Path

# Canonical URL for the 1988-onward civil tab-delimited file.
# Verified live and serving content on 2026-05-04.
# If this URL stops working, re-resolve from
# https://www.fjc.gov/research/idb/interactive/IDB-civil-since-1988
SOURCE_URL = "https://www.fjc.gov/sites/default/files/idb/textfiles/cv88on.zip"
URL_VERIFIED_DATE = "2026-05-04"

USER_AGENT = (
    "insurance-complaint-rates/1.0 "
    "(research; contact: evan.ochsner@gmail.com)"
)

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INTERIM_DIR = PROJECT_ROOT / "fjc_idb" / "interim"
ZIP_PATH = INTERIM_DIR / "cv88on.zip"
MANIFEST_PATH = INTERIM_DIR / "manifest.json"


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def head(url: str) -> dict[str, str]:
    req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req) as resp:
        return {k.lower(): v for k, v in resp.headers.items()}


def download(url: str, dest: Path) -> None:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    dest.parent.mkdir(parents=True, exist_ok=True)
    print(f"Downloading {url} -> {dest}")
    with urllib.request.urlopen(req) as resp, dest.open("wb") as out:
        total = int(resp.headers.get("content-length", "0"))
        downloaded = 0
        chunk_size = 1 << 20
        while True:
            chunk = resp.read(chunk_size)
            if not chunk:
                break
            out.write(chunk)
            downloaded += len(chunk)
            if total:
                pct = 100.0 * downloaded / total
                print(f"  {downloaded / 1e6:.1f} MB / {total / 1e6:.1f} MB ({pct:.1f}%)", end="\r")
        print()


def extract(zip_path: Path) -> list[str]:
    with zipfile.ZipFile(zip_path) as z:
        members = z.namelist()
        print(f"Zip contents: {members}")
        z.extractall(zip_path.parent)
    return members


def main() -> int:
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)

    # Probe the server first.
    server_headers = head(SOURCE_URL)
    server_size = server_headers.get("content-length")
    server_etag = server_headers.get("etag")
    server_last_modified = server_headers.get("last-modified")
    print(f"Server: size={server_size} etag={server_etag} last_modified={server_last_modified}")

    # Decide whether to skip the download.
    skip_download = False
    if ZIP_PATH.exists() and MANIFEST_PATH.exists():
        try:
            prior = json.loads(MANIFEST_PATH.read_text())
            if (
                prior.get("etag") == server_etag
                and prior.get("size") == int(server_size or 0)
                and prior.get("last_modified") == server_last_modified
            ):
                # Verify the local file still matches its recorded sha256.
                if sha256_of(ZIP_PATH) == prior.get("sha256"):
                    print("Local zip matches server (etag, size, last-modified, sha256). Skipping download.")
                    skip_download = True
        except (json.JSONDecodeError, ValueError):
            pass

    if not skip_download:
        download(SOURCE_URL, ZIP_PATH)

    digest = sha256_of(ZIP_PATH)
    size = ZIP_PATH.stat().st_size

    members = extract(ZIP_PATH)

    manifest = {
        "source_url": SOURCE_URL,
        "url_verified_date": URL_VERIFIED_DATE,
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "size": size,
        "sha256": digest,
        "etag": server_etag,
        "last_modified": server_last_modified,
        "zip_members": members,
        "user_agent": USER_AGENT,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"\nManifest written to {MANIFEST_PATH}")
    print(f"  sha256: {digest}")
    print(f"  size:   {size:,} bytes")
    return 0


if __name__ == "__main__":
    sys.exit(main())
