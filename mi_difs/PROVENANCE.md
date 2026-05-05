# Provenance

Source-of-record details for the MI DIFS complaint dataset. Outputs in `mi_difs/output/` are reproducible by re-running `scripts/01_download.py` then `scripts/02_parse.py`. The authoritative manifest is `interim/manifest.json`.

## Sources (URLs verified live 2026-05-05)

Landing page: <https://difs.state.mi.us/complaintstats>

The site exposes 24 distinct HTML pages currently — three years (2022, 2023, 2024) × eight page types per year:

### Per-company complaint ratios (5 lines × 3 years = 15 pages)

| Line | URL pattern |
|---|---|
| Automobile | `https://difs.state.mi.us/ComplaintStats/ComplaintRatios/InsuranceCompanyList?coverageType=AUTO&forYear={YEAR}` |
| Homeowners | `...?coverageType=HOME&forYear={YEAR}` |
| Life | `...?coverageType=LIFE&forYear={YEAR}` |
| Accident & Health | `...?coverageType=ACHL&forYear={YEAR}` |
| Annuity | `...?coverageType=ANTS&forYear={YEAR}` |

### Aggregate statistics (3 stats × 3 years = 9 pages)

| Stat | URL pattern |
|---|---|
| Total Complaints | `https://difs.state.mi.us/ComplaintStats/ComplaintRatios/InsuranceStatistics?statisticType=TOTALCOMPLAINT&forYear={YEAR}` |
| Line of Coverage | `...?statisticType=LINECOVERAGE&forYear={YEAR}` |
| Complaint Reason | `...?statisticType=REASON&forYear={YEAR}` |

## HTML structure

Pages use Bootstrap-style `<div class="row">` rather than `<table>`. Per-company rows look like:

```html
<div class="row company-list all-border">
  <div class="col-sm-6 bluecol" aria-label="ACE AMERICAN INSURANCE COMPANY">
    <a href='/ComplaintStats/ComplaintRatios/InsuranceRatioDetail?companyID=0000401&forYear=2024'>ACE AMERICAN INSURANCE COMPANY</a>
  </div>
  <div class="col-sm-2 center-div" aria-label="Complaints for ACE AMERICAN INSURANCE COMPANY">1</div>
  <div class="col-sm-2 r-align push-col" aria-label="Complaints count for ACE AMERICAN INSURANCE COMPANY">$8,324,577</div>
  <div class="col-sm-2 r-align" aria-label="Complaints ratio for ACE AMERICAN INSURANCE COMPANY">.12</div>
</div>
```

The parser uses `aria-label` and `data-th` attributes for stability against minor layout changes. The `companyID` is preserved as `company_id` in the output so per-company detail pages (`/InsuranceRatioDetail?companyID=...`) can be linked from the parquet.

## Access notes

- **No UA gate.** The DIFS server accepts ordinary requests; a polite Chrome-style UA is used out of courtesy.
- **No rate-limit observed.** A 1-second sleep between requests is used as a courtesy.
- **No login or cookies required.** All pages are public.

## Coverage

- **Years:** 2022, 2023, 2024 (3 years).
- **Coverage cutoff:** Companies with < $1M annual premium for the line in the report year are excluded from the per-company table. Aggregate stats include them.
- **Lines per-company:** 5 (Auto, Home, Life, A&H, Annuity).
- **Lines aggregate-only:** Fire/Allied/CMP, Liability.
- **Run-date label.** Per the landing page, "Company names listed are current as of the report run date (typically 4-6 months after the year-end)."

## File hashes

Per-file sha256 hashes are stored in `interim/manifest.json`. To verify, re-run `scripts/01_download.py` and diff the manifest.

## Run history

### 2026-05-05 — initial build

- 24 HTML pages downloaded (~1.4 MB total).
- 1,033 per-company rows × 5 lines × 3 years.
- 21 line-of-coverage rows (7 lines × 3 years).
- 12 total-complaint rows (4 entity types × 3 years).
- 36 reason rows (4 categories × 3 entity types × 3 years).
- Per-line cross-check confirms per-company sums fall short of line-of-coverage totals by 5–100 complaints (the sub-$1M-premium companies excluded by DIFS).
