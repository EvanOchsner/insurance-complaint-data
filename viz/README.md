# Insurance Complaint Rates — Unified Data Viewer

Single self-contained HTML app that lets you browse and visualize every dataset in this repo. Pick a dataset on the left, get a tailored chart with the controls that actually matter for that dataset.

## How to view

```
open viz/index.html
```

That's it. Static file, opens in any modern browser. Internet required only to load Plotly.js from its CDN (see "Offline" below).

## How to rebuild

After re-running any of the data pipelines (which updates the parquet outputs), rebuild the viz:

```
python3 viz/build_viz.py
```

The build is fast (~5 seconds) and idempotent. The script discovers every `<dataset>/viz_manifest.json`, loads the referenced parquets, and emits a self-describing payload embedded in `viz/index.html`.

## What's in the picker

The left sidebar groups datasets by **conceptual category** because they're not all measuring the same thing. The category controls the caveat banner color above the chart and is permanently visible in the picker.

### Regulator findings (green banner)

The regulator concluded the insurer acted improperly. Comparable across these datasets in concept, though not on the same axis without normalization.

| Entry | Source |
|---|---|
| **CA CDI top-50 by line** | CA Department of Insurance Consumer Complaint Studies — top-50 carriers per line of insurance, 2020–2024. |
| **CA CDI state totals** | CA DI Annual Reports — statewide complaints closed/opened/dollars recovered, 2020–2024. |
| **CT CID** | CT Insurance Department closed complaints — 2018–2026, with CT's `disposition` mapped to a 3-bucket against/for/ambiguous classification. |
| **NY DFS Auto** | NY Department of Financial Services Auto Complaint Ranking — per-company, 2009–2024. **Note: 2-year rolling window**. |
| **NY DFS Health** | NY DFS Consumer Guide to Health Insurers — per-plan, 2015–2024, by HMO / EPO-PPO / Commercial. |
| **TX TDI** | TX Department of Insurance closed complaints — 2012–2026, with TDI's own `Confirmed`/`Not Confirmed` finding. |
| **WA OIC AR** | WA Office of the Insurance Commissioner Annual Report — annual workload counts, 2020–2024. |
| **7-state merits rate** | Cross-state comparison: against-insurer share of on-merits decisions over time, for the seven states that publish a merits-decision denominator (CT, MD, MO, NY [Auto + Health = 2 lines], OR, TX, VA). Synthesized by summing each state's outcome buckets to a state-year total. Methodologies aren't identical — NY Auto is a 2-yr rolling window, VA SCC ER is health external review only — so this is a *trend* comparison, not a leaderboard. Surfaces in the picker only (not on per-state pages). |

### Regulator complaint indexes (tan banner)

NAIC-tradition complaint indexes — `(company's share of complaints) / (company's share of premium)`, normalized so 1.0 = parity. **Different metric class than "regulator findings"**: a relative ratio, not a count of insurer-improperly-handled determinations. Above 1.0 = more complaints than market share predicts; below 1.0 = fewer. The viz keeps these in a separate category so they aren't accidentally co-plotted with confirmed/upheld counts.

| Entry | Source |
|---|---|
| **IN IDOI** | Indiana DOI annual *Company Complaint Index* — per-company by line (Annuity / Auto / Health / Homeowners / Life), 2009–2024. **Excludes companies with zero complaints** — per-company medians biased above 1.0 for that reason. |
| **KS KID** | Kansas DOI annual *Complaint Index Report* — top-20 premium writers per line plus 10+-complaint companies, 2020–2024. **Includes zero-complaint top-20 writers**, so per-company medians sit closer to ~1.0. Inclusion rules differ from IN's; per-company medians are not apples-to-apples. |

### ⚠ Plaintiff allegations (yellow banner)

These are notices filed by plaintiffs (or their attorneys) as a precondition to suing — **NOT regulator findings**. Counts measure pre-litigation pressure, not insurer wrongdoing per se. Treat as a different kind of metric.

| Entry | Source |
|---|---|
| **FL CRN** | FL Civil Remedy Notice counts by line — 2014–2026. Hurricane and AOB-litigation eras drive non-organic spikes. |
| **WA IFCA** | WA Insurance Fair Conduct Act 20-day notices — 2025–2026 only (older PDFs were removed by OIC). |

### Federal lawsuits (blue banner)

| Entry | Source |
|---|---|
| **FJC IDB** | Federal Judicial Center Integrated Database — civil filings under Nature-of-Suit code 110 (Insurance), all 50 states + DC + 4 territories, 1988–2025. A lawsuit being filed, not a regulator finding. |

A standalone, more-comprehensive viz for the FJC dataset alone lives at [`fjc_idb/viz/index.html`](../fjc_idb/viz/index.html) — same controls but FJC-only.

## Controls

The sidebar adapts to the active dataset:

- **Filters** — the dimensions specific to that dataset (state list, coverage type, plan type & plan, line of insurance, …).
- **Metric** — when a dataset exposes more than one metric (e.g. TX has count, confirmed count, confirmed rate), pick which one drives the y-axis.
- **Chart mode** (only shown when the dataset declares outcome buckets — currently MD, TX, CT, NY auto, NY health, CA top-50): **Line** / **Stacked bars** / **Two-panel**. Default per-dataset is in its `viz_manifest.json`.
- **Display** — the same overlay set across every dataset:
  - **Exclude partial year** — default ON. Drops the row tagged as the partial year (anywhere in the series — usually the trailing year, but MD MIA's partial year is FY 2008 at the start).
  - **Per-year rate labels** (two-panel mode only) — `7.5% (3/40)` annotations on the rate panel; toggleable.
  - **Y-axis: Linear / Log**.
  - **Per-series: Average** (default ON; dashed light-alpha line at each series' mean), 3-yr MA, 5-yr MA. (line mode only)
  - **Cross-series: Mean / Sum / Median** of currently selected series. (line mode only)

## Chart modes

For datasets that publish a regulator-finding breakdown (i.e. how each closed complaint was resolved), the viewer offers three chart modes:

- **Line** — the legacy single-line chart. One trace per group (coverage type, plan, company, …). Most flexible for ad-hoc comparison.
- **Stacked bars** — single panel with stacked bars per year, broken into 4 outcome buckets (canonical taxonomy below). Best for reading per-year volume + composition at a glance.
- **Two-panel** — stacked bars on top, against-rate line below. Matches the supplied MD-style chart layout. Default for datasets with full bucket coverage.

The 4-bucket outcome taxonomy (declared per-dataset in `viz_manifest.json`):

| Canonical bucket | Color | Meaning |
|---|---|---|
| `against_insurer` | red `#C44536` | Regulator decided on merits *against* the insurer (TX `Confirmed`, CT `Company Position Overturned + Claim Settled + …`, NY `upheld`, MD `bad_faith`, CA `justified`) |
| `mixed` | gold `#D4A55E` | Partial finding for insured (currently MD `breach_pay_only` only) |
| `for_insurer` | blue `#5B7BA0` | Regulator decided on merits *for* the insurer |
| `no_decision` | gray `#B8B8C8` | No merits decision (settled, withdrawn, dismissed, ambiguous, question-of-fact) |

The bottom-panel rate is `against_insurer / on_merits` where `on_merits = against + mixed + for` (excluding no_decision). A dashed dark-gray line shows the dataset's lifetime aggregate of that rate. Years where `against = 0` get an open marker; nonzero years get filled red markers.

### Plot interactions (Plotly toolbar)

Pan with click-drag · scroll-wheel zoom · double-click to reset · hover for value · click legend entry to toggle a series. Per-series overlays share a `legendgroup` with their parent line, so toggling a state's legend entry hides that state's average/MA together.

## Adding a new state (or any new dataset)

1. Land your data pipeline outputs as a Parquet under `<state_code>_<agency>/output/...`.
2. Drop a `<state_code>_<agency>/viz_manifest.json` next to it. See any of the existing manifests for the schema; the FJC, TX, and CA ones cover the spectrum of complexity.
3. Run `python3 viz/build_viz.py`.

That's it. No code changes to the viz itself.

The manifest declares one or more `entries` (each becomes a row in the picker). Each entry needs:

- `id`, `name`, `short_name` (for the picker)
- `category` (one of `regulator_finding`, `plaintiff_allegation`, `federal_lawsuit`)
- `jurisdiction`, `caveat_short`, `provenance_url`
- `parquet`, `x_field`, `group_field` (or `null` for scalar series), optional `filter_field`
- `metrics` — list of `{id, label, column}`
- `default_metric`, `default_groups` (or `default_groups_strategy: "top_n_by_metric"`)
- Optional: `group_presets`, `partial_year`, `notes`

## Headline caveats

1. **Different categories are different things.** The viz never puts plaintiff-allegation counts and regulator-finding counts on the same axis, by design. If you want a cross-state comparison, stay within one category.
2. **No normalization in v1.** Per-capita, per-premium, and per-policy-in-force normalization all require external data (Census, NAIC IDRR) and are deferred to a v2.
3. **Trailing partial year:** every dataset where the most recent year is incomplete has it flagged, and the toggle drops it from every series including overlays.
4. **2-year rolling caveat for NY Auto:** the only metric NY DFS exposes is a 2-year rolling complaint ratio. Don't sum `filing_year` rows across years (would double-count). Use the rolling-window value as-is.
5. **Top-50 caveat for CA top-50:** CDI publishes only the top-50 insurers per line per year. Smaller carriers' justified complaints aren't in the data, so the line totals are a lower bound.

## Files

```
viz/
├── PLAN.md           # design + how to add a new state
├── README.md         # this file
├── build_viz.py      # one-shot build: discovers manifests + emits index.html
└── index.html        # the deliverable; safe to commit (~180 KB)
```

Plus, in each dataset folder:

```
<dataset>/
└── viz_manifest.json
```

## Offline

The viz loads Plotly.js from `cdn.plot.ly`. To make the file fully offline, replace the `<script src="https://cdn.plot.ly/...">` tag in `build_viz.py`'s `HTML_TEMPLATE` with the bundled minified JS (~3.5 MB). Not done by default — the CDN is reliable and keeps the artifact under 200 KB.
