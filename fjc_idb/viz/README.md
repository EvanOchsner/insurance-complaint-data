# Interactive viz — federal civil insurance filings, by state and year

Single-file static HTML visualization of `fjc_idb/output/insurance_filings_by_state_year.parquet`.

## How to view

Just open the HTML file in any modern browser:

```
open fjc_idb/viz/index.html
```

No server, no install. The file embeds the entire dataset (~25 KB) and loads Plotly.js from a CDN. If you have an internet connection the chart appears within a second.

## How to rebuild

After re-running the data pipeline (which updates the parquet outputs), rebuild the HTML:

```
python3 fjc_idb/viz/build_viz.py
```

The build is fast (under a second) and idempotent. The script reads:

- `fjc_idb/output/insurance_filings_by_state_year.parquet` — the data
- `fjc_idb/interim/manifest.json` — to put the source URL, SHA-256, and fetch timestamp in the footer

…and writes `fjc_idb/viz/index.html`.

## Controls

| Control | What it does |
|---|---|
| **States** multi-select | Pick which states/territories appear as colored lines. Hold ⌘ / Ctrl to multi-select. |
| **Top 10 / All 50 + DC / All + territories / None** | Quick presets for the multi-select. The "Top 10" default is by total NoS=110 filings since 1988. |
| **Nationwide total** checkbox | Heavy black line: sum across all 55 jurisdictions. Independent of the multi-select. |
| **Exclude partial year** checkbox | The trailing year is partial (FJC has ~2 month reporting lag). Default ON; uncheck to include the partial point. |
| **Y-axis: Linear / Log** | Log helps when small states (MD ~100/yr) and big states (TX ~2000/yr) share a chart. |
| **Per-series: Average** | Default ON. For each visible state, draws a flat dashed reference line in the same color, at low alpha, at that state's mean over the full period. Tells you at a glance whether the current year is above or below the state's long-run average. |
| **Per-series: 3-yr / 5-yr MA** | Trailing moving-average overlay per state, dotted / dash-dot, same color as the parent line. |
| **Cross-state: Mean / Sum / Median of selected** | One additional line each, computed across the *currently selected* states at every year. Useful for "what's the typical state look like?" (mean/median) vs "what's the combined load?" (sum). |

The Plotly toolbar above the chart provides standard interactions:

- **Pan** — click-and-drag.
- **Zoom** — scroll wheel, or use the zoom button + drag.
- **Reset** — double-click the chart, or use the home button in the toolbar.
- **Hover** — point at any line for the value at that year.
- **Legend toggle** — click an entry to hide; double-click to isolate. Per-state averages and MAs share the state's `legendgroup`, so clicking the state in the legend hides its raw line **and** its overlays together.

## What you're looking at

- 1988–2025 calendar-year filing counts for federal civil cases coded NoS = 110 ("Insurance"). The filter is documented in `../METHODOLOGY.md`.
- 55 jurisdictions: 50 states + DC + 4 territories (PR, VI, GU, MP).
- This is **federal court only**, and **not specifically bad-faith** — see headline caveats in `../README.md`.

The numbers worth eyeballing on first load:

- **Louisiana** dominates — driven by hurricane-related insurance litigation. Watch the Katrina spike (2006-7) and the 2022-23 surge.
- **Texas** has trended up in recent years, overtaking the historical leaders.
- **Nationwide total** rises ~2x from late 1980s to early 2020s, with a sharp run-up post-2019.
- **Smaller states** (look at MD or AK) sit comfortably under their per-series average reference line in some years and above in others — a quick way to see which years were unusually litigious for that state.

## Known limitations

- **Internet required for first load.** Plotly.js loads from `cdn.plot.ly`. To make the file 100% offline, replace the `<script src="https://cdn.plot.ly/...">` line in the template inside `build_viz.py` with the bundled minified JS (~3.5 MB). Not done by default to keep the artifact small.
- **The trailing year is partial.** Default is to exclude it from all series. Toggle the checkbox to see it (rendered without distinction; future iteration could mark the trailing point with a hollow marker).
- **No URL state.** Reloading the page resets controls to defaults. Shareable URLs / bookmarkable views are future work.
- **Mobile layout works but isn't tuned.** Controls wrap; chart height is fixed at 620 px.

## Files

```
fjc_idb/viz/
├── PLAN.md         # design doc + the open questions and how they were resolved
├── build_viz.py    # one-shot build: parquet -> index.html
├── index.html      # the deliverable; safe to commit (~25 KB)
└── README.md       # this file
```
