"""Download every Louisiana DOI Consumer Complaint Data Report PDF.

Source landing:
  https://ldi.la.gov/onlineservices/complaintindex/

LDI exposes the data via an ASP.NET WebForms / Telerik RadGrid page sitting
behind Cloudflare's managed-challenge protection. We use cloudscraper to
clear the challenge, then drive the form to download one PDF per
(line of insurance, year) combination — 4 lines × 10 years = 40 PDFs as of
2026-05-05.

Coverage type codes (id values from the page's <select>):
    1   = Auto - Individual Private Passenger
   47   = Homeowners
   70   = Life & Annuity - Individual Life
  119   = Accident & Health - Individual

Years: 2015 through 2024 (10 years).

The form is keyed by `coverageType_List$list` and `year_List$list` (Telerik's
$ naming, not _). The download is triggered by including
`downloadReportButton=Download Report` in the POST. Each iteration GETs the
page first to capture a fresh `__VIEWSTATE` / `__VIEWSTATEGENERATOR` /
`__EVENTVALIDATION` triplet — required by ASP.NET WebForms.
"""
from __future__ import annotations

import hashlib
import html as html_lib
import json
import re
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import cloudscraper

PROJECT_ROOT = Path(__file__).resolve().parents[2]
INTERIM_DIR = PROJECT_ROOT / "la_ldi" / "interim" / "files"
MANIFEST_PATH = PROJECT_ROOT / "la_ldi" / "interim" / "manifest.json"
URL = "https://ldi.la.gov/onlineservices/complaintindex/"

LINES = [
    ("auto",        1,    "Auto - Individual Private Passenger"),
    ("homeowners",  47,   "Homeowners"),
    ("life",        70,   "Life & Annuity - Individual Life"),
    ("accident_health", 119, "Accident & Health - Individual"),
]
YEARS = list(range(2015, 2025))  # 2015 through 2024 inclusive

SLEEP_BETWEEN = 2.5  # be polite — LDI is behind Cloudflare


def make_scraper() -> cloudscraper.CloudScraper:
    return cloudscraper.create_scraper(browser={
        "browser": "chrome",
        "platform": "darwin",
        "mobile": False,
    })


def hidden(text: str, name: str) -> str:
    m = re.search(rf'<input[^>]+name="{re.escape(name)}"[^>]+value="([^"]*)"', text)
    return html_lib.unescape(m.group(1)) if m else ""


def fetch_pdf(scraper: cloudscraper.CloudScraper, line_code: int, year: int) -> bytes:
    r = scraper.get(URL, timeout=60)
    r.raise_for_status()
    text = r.text
    data = {
        "__EVENTTARGET": "",
        "__EVENTARGUMENT": "",
        "__VIEWSTATE": hidden(text, "__VIEWSTATE"),
        "__VIEWSTATEGENERATOR": hidden(text, "__VIEWSTATEGENERATOR"),
        "__EVENTVALIDATION": hidden(text, "__EVENTVALIDATION"),
        "RadToolTip1_ClientState": "",
        "coverageType_List$list": str(line_code),
        "companyName_Box": "",
        "sortByList": "Premiums Written",
        "year_List$list": str(year),
        "consumerComplaintsSearchGrid_ClientState": "",
        "downloadReportButton": "Download Report",
    }
    r2 = scraper.post(
        URL,
        data=data,
        headers={"Referer": URL, "Origin": "https://ldi.la.gov"},
        timeout=60,
    )
    r2.raise_for_status()
    if not r2.content.startswith(b"%PDF"):
        raise RuntimeError(f"non-PDF body for line={line_code} year={year}; first 64={r2.content[:64]!r}")
    return r2.content


def main() -> None:
    INTERIM_DIR.mkdir(parents=True, exist_ok=True)
    scraper = make_scraper()
    files: list[dict] = []
    for slug, code, label in LINES:
        for year in YEARS:
            fname = f"{slug}_{year}.pdf"
            target = INTERIM_DIR / fname
            print(f"  fetching {fname}: line={code} ({label!r}), year={year}")
            try:
                body = fetch_pdf(scraper, code, year)
            except Exception as e:
                print(f"    FAILED: {e}", file=sys.stderr)
                sys.exit(1)
            target.write_bytes(body)
            sha = hashlib.sha256(body).hexdigest()
            print(f"    ok: {len(body):,} bytes, sha256={sha[:16]}…")
            files.append({
                "filename": fname,
                "line_canonical": slug,
                "line_label": label,
                "coverage_type_code": code,
                "year": year,
                "url": URL,
                "bytes": len(body),
                "sha256": sha,
            })
            time.sleep(SLEEP_BETWEEN)
    manifest = {
        "project_tag": "insurance-complaint-rates/1.0 (research; contact: evan.ochsner@gmail.com)",
        "fetched_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "fetch_method": "cloudscraper (clears Cloudflare managed challenge) + WebForms POST replay",
        "files": files,
    }
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2) + "\n")
    print(f"  wrote {MANIFEST_PATH}; {len(files)} files")


if __name__ == "__main__":
    main()
