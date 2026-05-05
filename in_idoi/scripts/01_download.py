"""Discover and download every IDOI Company Complaint Index file.

Lists the IDOI landing page, parses out the (year × line) → URL grid, and
downloads each file (mostly PDFs; 2014 is XLSX). Records SHA256 +
Last-Modified per file in interim/manifest.json.

Source landing:
  https://www.in.gov/idoi/consumer-services/complaint-index/company-complaint-index/

Files cover 5 lines (Annuity, Auto, Health, Homeowners, Life) for years
2009–2024 — about 80 files at first build.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import time
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

USER_AGENT = (
    "insurance-complaint-rates/1.0 "
    "(research; contact: evan.ochsner@gmail.com)"
)

LANDING_URL = (
    "https://www.in.gov/idoi/consumer-services/complaint-index/"
    "company-complaint-index/"
)
HOST = "https://www.in.gov"

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INTERIM_DIR = PROJECT_ROOT / "in_idoi" / "interim"
FILES_DIR = INTERIM_DIR / "files"
MANIFEST_PATH = INTERIM_DIR / "manifest.json"

# Map link-text line label → canonical line slug used in filenames + parquet.
LINE_NORMALIZE = {
    "annuity": "annuity",
    "auto": "auto",
    "health carriers": "health",
    "homeowners": "homeowners",
    "life": "life",
}

# Polite-scraping pause between downloads.
PER_REQUEST_DELAY_S = 1.0


def http_get(url: str, timeout: int = 30) -> tuple[bytes, dict]:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read()
        headers = dict(resp.getheaders())
        return body, headers


def discover_files() -> list[dict]:
    """Parse the IDOI landing page and return a list of
    {year, line, url, link_text} dicts, one per (year × line) file."""
    print(f"GET {LANDING_URL}")
    html_bytes, _ = http_get(LANDING_URL)
    html = html_bytes.decode("utf-8", errors="replace")

    # Each link reads like '<a href="/idoi/files/...">2024 Auto Complaint Index</a>'.
    pattern = re.compile(
        r'<a\s+href="(?P<href>/idoi/files/[^"]+)"[^>]*>'
        r'\s*(?P<text>(?P<year>\d{4})\s+(?P<line_label>[^<]+?)\s+Complaint\s+Index)\s*</a>',
        re.IGNORECASE,
    )
    found: dict[tuple[int, str], dict] = {}
    for m in pattern.finditer(html):
        year = int(m.group("year"))
        line_label_raw = m.group("line_label").strip().lower()
        line = LINE_NORMALIZE.get(line_label_raw)
        if line is None:
            print(f"  skipping unknown line label: '{line_label_raw}'")
            continue
        url = HOST + m.group("href")
        # Dedup on (year, line) — landing page doesn't currently double-list.
        key = (year, line)
        if key in found:
            continue
        found[key] = {
            "year": year,
            "line": line,
            "line_label_source": line_label_raw,
            "url": url,
            "link_text": m.group("text").strip(),
        }
    return sorted(
        found.values(),
        key=lambda d: (d["year"], d["line"]),
    )


def fetch_one(entry: dict) -> dict:
    """Download a single file, write to interim/files/{year}_{line}.{ext},
    return manifest record with SHA256 + Last-Modified."""
    url = entry["url"]
    ext = "xlsx" if url.lower().endswith(".xlsx") else "pdf"
    out_path = FILES_DIR / f"{entry['year']}_{entry['line']}.{ext}"

    print(f"GET {url}")
    body, headers = http_get(url)
    if ext == "pdf" and not body.startswith(b"%PDF"):
        raise RuntimeError(
            f"Expected PDF for {url}, got first bytes {body[:20]!r}. "
            f"Source layout may have changed."
        )
    out_path.write_bytes(body)
    sha = hashlib.sha256(body).hexdigest()
    last_modified = headers.get("Last-Modified")
    print(f"  → {out_path.name}  {len(body)/1024:.1f} KB  sha256={sha[:12]}…")
    return {
        "year": entry["year"],
        "line": entry["line"],
        "url": url,
        "ext": ext,
        "filename": out_path.name,
        "size_bytes": len(body),
        "sha256": sha,
        "last_modified_header": last_modified,
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
    }


def main() -> int:
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    FILES_DIR.mkdir(parents=True, exist_ok=True)

    discoveries = discover_files()
    print(f"\nDiscovered {len(discoveries)} files on the IDOI landing page:")
    by_year: dict[int, list[str]] = {}
    for d in discoveries:
        by_year.setdefault(d["year"], []).append(d["line"])
    for y in sorted(by_year):
        lines = sorted(by_year[y])
        print(f"  {y}: {', '.join(lines)}")

    records: list[dict] = []
    for d in discoveries:
        try:
            rec = fetch_one(d)
            records.append(rec)
        except Exception as e:
            print(f"  ERROR fetching {d['url']}: {e}", file=sys.stderr)
            return 2
        time.sleep(PER_REQUEST_DELAY_S)

    manifest = {
        "source": LANDING_URL,
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
