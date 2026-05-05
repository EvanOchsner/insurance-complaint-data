# Provenance

Source-of-record details for the LA LDI complaint dataset. Outputs in `la_ldi/output/` are reproducible by re-running `scripts/01_download.py` then `scripts/02_parse.py`. The authoritative manifest is `interim/manifest.json`.

## Source URL (verified live 2026-05-05)

Online services landing: <https://ldi.la.gov/onlineservices/complaintindex/>

Same URL handles both the GET (renders the form) and the POST (returns a PDF when `downloadReportButton=Download Report` is included).

## Cloudflare bypass

The `ldi.la.gov` origin is behind Cloudflare's "managed challenge" — it rejects ordinary `requests.get()` with HTTP 403 and a `Just a moment...` JavaScript challenge page. The downloader uses **`cloudscraper`** (`pip install cloudscraper`) to clear the challenge, then reuses the same session for subsequent POSTs. The browser fingerprint configuration:

```python
cloudscraper.create_scraper(browser={
    "browser": "chrome",
    "platform": "darwin",
    "mobile": False,
})
```

If Cloudflare changes its challenge format, cloudscraper may need an update or we may need to switch to a real-browser driver (Playwright, Claude-in-Chrome, etc.). Browser-based fallback was verified working during recon — see `interim/files/auto_2024.pdf` originally fetched via Claude-in-Chrome on 2026-05-05.

## Form mechanics — ASP.NET WebForms / Telerik RadGrid

The page is ASP.NET WebForms with Telerik RadGrid. To trigger a download POST:

1. **GET** the page to capture three hidden tokens — `__VIEWSTATE`, `__VIEWSTATEGENERATOR`, `__EVENTVALIDATION`. These rotate on each GET; you must include them verbatim in the POST.
2. **POST** to the same URL with these form fields:

| Field | Value | Notes |
|---|---|---|
| `__EVENTTARGET` | `""` | empty |
| `__EVENTARGUMENT` | `""` | empty |
| `__VIEWSTATE` | (from GET) | server state |
| `__VIEWSTATEGENERATOR` | (from GET) | |
| `__EVENTVALIDATION` | (from GET) | |
| `RadToolTip1_ClientState` | `""` | |
| `coverageType_List$list` | `1`, `47`, `70`, or `119` | **Note `$` not `_`** — Telerik convention; the `id` attribute uses `_` but the `name` (which is what the server reads) uses `$`. |
| `companyName_Box` | `""` | optional company-name filter |
| `sortByList` | `Premiums Written` | could also be `Company Name` or `Complaint Index` |
| `year_List$list` | `2015`–`2024` | use `$` |
| `consumerComplaintsSearchGrid_ClientState` | `""` | |
| `downloadReportButton` | `Download Report` | the button-name → triggers PDF download |

3. **Headers:** include `Referer: https://ldi.la.gov/onlineservices/complaintindex/` and `Origin: https://ldi.la.gov`.

A successful POST returns `Content-Type: binary/octet-stream` and a `%PDF-` body of ~720-770 KB.

## Coverage type codes

| Code | Label |
|---|---|
| 1 | Auto - Individual Private Passenger |
| 47 | Homeowners |
| 70 | Life & Annuity - Individual Life |
| 119 | Accident & Health - Individual |

(The page's prose mentions "Life Company Sort" but no such option exists in the form.)

## File hashes

Per-file sha256 hashes are stored in `interim/manifest.json`. Sample (first build):

| File | Bytes | sha256 (first 16) |
|---|---:|---|
| `auto_2024.pdf` | 733,078 | `73eeeb0e3c3ba291…` |
| `homeowners_2021.pdf` | 739,338 | `d9bcc27374171830…` |
| `life_2018.pdf` | 767,608 | `c6d0d9b71e72c2bc…` |

## Run history

### 2026-05-05 — initial build

- 40 PDFs fetched (~30 MB total).
- 9,550 per-company per-line per-year rows after parsing.
- 40 per-line per-year aggregate rows.
- Parsed years 2015–2024 across 4 lines; all 40 (line, year) cells populated.
- Notable signal: homeowners 2021 = 4,492 complaints (Hurricane Ida year), with the high-index outliers cleanly matching carriers that subsequently became insolvent (Ocean Harbor, Allied Trust, Southern Fidelity, FedNat, United Property & Cas, Maison, GeoVera Specialty).
