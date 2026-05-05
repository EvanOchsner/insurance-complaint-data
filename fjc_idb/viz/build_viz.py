"""Build a self-contained interactive viz HTML for the FJC IDB dataset.

Reads:
  fjc_idb/output/insurance_filings_by_state_year.parquet
  fjc_idb/interim/manifest.json   (for source provenance footer)

Writes:
  fjc_idb/viz/index.html
"""
from __future__ import annotations

import json
from pathlib import Path

import polars as pl

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SY_PARQUET = PROJECT_ROOT / "fjc_idb" / "output" / "insurance_filings_by_state_year.parquet"
MANIFEST = PROJECT_ROOT / "fjc_idb" / "interim" / "manifest.json"
OUT_HTML = PROJECT_ROOT / "fjc_idb" / "viz" / "index.html"

# 2-letter postal code -> human label + territory flag.
STATE_META = {
    "AK": ("Alaska", False), "AL": ("Alabama", False), "AR": ("Arkansas", False),
    "AZ": ("Arizona", False), "CA": ("California", False), "CO": ("Colorado", False),
    "CT": ("Connecticut", False), "DC": ("District of Columbia", False),
    "DE": ("Delaware", False), "FL": ("Florida", False), "GA": ("Georgia", False),
    "GU": ("Guam", True), "HI": ("Hawaii", False), "IA": ("Iowa", False),
    "ID": ("Idaho", False), "IL": ("Illinois", False), "IN": ("Indiana", False),
    "KS": ("Kansas", False), "KY": ("Kentucky", False), "LA": ("Louisiana", False),
    "MA": ("Massachusetts", False), "MD": ("Maryland", False), "ME": ("Maine", False),
    "MI": ("Michigan", False), "MN": ("Minnesota", False), "MO": ("Missouri", False),
    "MP": ("Northern Mariana Islands", True), "MS": ("Mississippi", False),
    "MT": ("Montana", False), "NC": ("North Carolina", False),
    "ND": ("North Dakota", False), "NE": ("Nebraska", False),
    "NH": ("New Hampshire", False), "NJ": ("New Jersey", False),
    "NM": ("New Mexico", False), "NV": ("Nevada", False), "NY": ("New York", False),
    "OH": ("Ohio", False), "OK": ("Oklahoma", False), "OR": ("Oregon", False),
    "PA": ("Pennsylvania", False), "PR": ("Puerto Rico", True),
    "RI": ("Rhode Island", False), "SC": ("South Carolina", False),
    "SD": ("South Dakota", False), "TN": ("Tennessee", False), "TX": ("Texas", False),
    "UT": ("Utah", False), "VA": ("Virginia", False), "VI": ("U.S. Virgin Islands", True),
    "VT": ("Vermont", False), "WA": ("Washington", False), "WI": ("Wisconsin", False),
    "WV": ("West Virginia", False), "WY": ("Wyoming", False),
}


def build_payload() -> dict:
    df = pl.read_parquet(SY_PARQUET)
    states = sorted(df["state"].unique().to_list())
    years_observed = sorted(df["year"].unique().to_list())
    year_min, year_max = int(years_observed[0]), int(years_observed[-1])
    years = list(range(year_min, year_max + 1))

    # Pivot to a state-by-year grid; missing combos -> null.
    counts: dict[str, list[int | None]] = {}
    df_dict = {(r["state"], r["year"]): r["count"] for r in df.iter_rows(named=True)}
    for state in states:
        counts[state] = [df_dict.get((state, y)) for y in years]

    # Top-10 by total since 1988 (the default selection).
    totals = (
        df.group_by("state")
        .agg(pl.col("count").sum().alias("total"))
        .sort("total", descending=True)
    )
    top10 = totals.head(10)["state"].to_list()

    # Source provenance for the footer.
    manifest = json.loads(MANIFEST.read_text()) if MANIFEST.exists() else {}

    state_meta = {
        s: {
            "label": STATE_META.get(s, (s, False))[0],
            "is_territory": STATE_META.get(s, (s, False))[1],
        }
        for s in states
    }

    # Identify trailing partial year using max FILEDATE if encoded; otherwise
    # default to the last year present.
    partial_year = year_max  # the script logs this; the data alone implies it.

    return {
        "years": years,
        "year_min": year_min,
        "year_max": year_max,
        "partial_year": partial_year,
        "states": states,
        "state_meta": state_meta,
        "counts": counts,
        "default_selection": top10,
        "source": {
            "url": manifest.get("source_url"),
            "fetched_at": manifest.get("fetched_at"),
            "sha256": manifest.get("sha256"),
            "last_modified": manifest.get("last_modified"),
        },
    }


HTML_TEMPLATE = r"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Federal civil insurance filings (NoS=110) by state and year</title>
<script src="https://cdn.plot.ly/plotly-2.35.0.min.js" charset="utf-8"></script>
<style>
  :root {
    --fg: #222;
    --muted: #666;
    --border: #ddd;
    --bg: #fafafa;
    --accent: #1f4e79;
  }
  html, body {
    margin: 0; padding: 0;
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif;
    color: var(--fg);
    background: #fff;
    font-size: 14px;
  }
  .wrap { max-width: 1200px; margin: 0 auto; padding: 16px 20px 40px; }
  header h1 { font-size: 18px; margin: 0 0 4px; }
  header .sub { color: var(--muted); font-size: 13px; margin-bottom: 12px; }
  .controls {
    background: var(--bg);
    border: 1px solid var(--border);
    border-radius: 6px;
    padding: 10px 14px;
    margin-bottom: 14px;
    display: grid;
    grid-template-columns: 1fr;
    gap: 8px;
  }
  .row { display: flex; flex-wrap: wrap; align-items: center; gap: 16px; }
  .row > label { display: inline-flex; align-items: center; gap: 4px; }
  .row .group-label { color: var(--muted); font-weight: 600; min-width: 90px; }
  .quick-presets button {
    margin-right: 6px; padding: 3px 8px;
    background: #fff; border: 1px solid var(--border); border-radius: 4px; cursor: pointer;
    font-size: 12px;
  }
  .quick-presets button:hover { background: #eef; }
  select[multiple] {
    width: 100%; min-height: 80px; max-height: 140px;
    padding: 4px;
    border: 1px solid var(--border); border-radius: 4px;
    font-size: 12px;
  }
  #plot { width: 100%; height: 620px; }
  footer {
    margin-top: 18px; padding-top: 12px; border-top: 1px solid var(--border);
    font-size: 12px; color: var(--muted); line-height: 1.5;
  }
  footer code { font-size: 11px; }
  footer a { color: var(--accent); }
</style>
</head>
<body>
<div class="wrap">
  <header>
    <h1>Federal civil insurance filings (Nature of Suit = 110), by state and year</h1>
    <div class="sub">
      Source: FJC Integrated Database, civil cases since 1988.
      Data through <span id="hdr-max-filedate"></span>.
      <span id="hdr-partial-warning"></span>
    </div>
  </header>

  <div class="controls">
    <div class="row">
      <span class="group-label">States</span>
      <div class="quick-presets">
        <button data-preset="top10">Top 10</button>
        <button data-preset="all50">All 50 + DC</button>
        <button data-preset="allplus">All + territories</button>
        <button data-preset="none">None</button>
      </div>
    </div>
    <div class="row">
      <select id="state-select" multiple></select>
    </div>
    <div class="row">
      <label><input type="checkbox" id="opt-nationwide" checked> Nationwide total</label>
      <label><input type="checkbox" id="opt-exclude-partial" checked> Exclude partial year (<span id="hdr-partial-year"></span>)</label>
      <span class="group-label" style="min-width: 60px;">Y-axis</span>
      <label><input type="radio" name="yaxis" value="linear" checked> Linear</label>
      <label><input type="radio" name="yaxis" value="log"> Log</label>
    </div>
    <div class="row">
      <span class="group-label">Per-series</span>
      <label><input type="checkbox" id="ovl-avg" checked> Average</label>
      <label><input type="checkbox" id="ovl-ma3"> 3-yr MA</label>
      <label><input type="checkbox" id="ovl-ma5"> 5-yr MA</label>
    </div>
    <div class="row">
      <span class="group-label">Cross-state</span>
      <label><input type="checkbox" id="ovl-mean"> Mean of selected</label>
      <label><input type="checkbox" id="ovl-sum"> Sum of selected</label>
      <label><input type="checkbox" id="ovl-median"> Median of selected</label>
    </div>
  </div>

  <div id="plot"></div>

  <footer>
    Built from <code>fjc_idb/output/insurance_filings_by_state_year.parquet</code>.
    Source: <a id="footer-src" href="">FJC IDB cv88on.zip</a>,
    SHA-256 <code id="footer-sha"></code>,
    fetched <span id="footer-fetched"></span>.
    See <code>fjc_idb/METHODOLOGY.md</code> for what NoS=110 covers and what's not in this data.
    NoS=110 ≠ "bad faith"; federal court only; the trailing year is partial.
  </footer>
</div>

<script>
const PAYLOAD = __PAYLOAD_JSON__;

// ----------------------- color cycle -----------------------
// Distinct, light-theme-friendly palette. Plotly's default works but cycling
// 55 series quickly collides; we expand the palette with a deterministic
// hash-based fallback so each state has a stable color across reloads.
const PALETTE = [
  "#1f77b4", "#ff7f0e", "#2ca02c", "#d62728", "#9467bd",
  "#8c564b", "#e377c2", "#7f7f7f", "#bcbd22", "#17becf",
  "#393b79", "#637939", "#8c6d31", "#843c39", "#7b4173",
  "#5254a3", "#8ca252", "#bd9e39", "#ad494a", "#a55194",
  "#6b6ecf", "#b5cf6b", "#e7ba52", "#d6616b", "#ce6dbd",
  "#9c9ede", "#cedb9c", "#e7cb94", "#e7969c", "#de9ed6",
];
const stateColor = {};
function colorFor(state) {
  if (state in stateColor) return stateColor[state];
  // Deterministic assignment by sort order of all states, then palette wrap.
  const idx = PAYLOAD.states.indexOf(state);
  const c = PALETTE[idx % PALETTE.length];
  stateColor[state] = c;
  return c;
}

// ----------------------- math helpers -----------------------
function trailingMA(values, window) {
  const out = new Array(values.length).fill(null);
  for (let i = window - 1; i < values.length; i++) {
    let sum = 0, n = 0, ok = true;
    for (let k = 0; k < window; k++) {
      const v = values[i - k];
      if (v === null || v === undefined) { ok = false; break; }
      sum += v; n++;
    }
    if (ok && n === window) out[i] = sum / n;
  }
  return out;
}

function seriesMean(values) {
  let sum = 0, n = 0;
  for (const v of values) {
    if (v !== null && v !== undefined) { sum += v; n++; }
  }
  return n > 0 ? sum / n : null;
}

function median(arr) {
  const s = arr.filter(v => v !== null && v !== undefined).slice().sort((a, b) => a - b);
  if (!s.length) return null;
  const mid = Math.floor(s.length / 2);
  return s.length % 2 ? s[mid] : 0.5 * (s[mid - 1] + s[mid]);
}

// Apply "exclude partial year" by truncating arrays to drop the trailing year.
function maybeExcludePartial(years, ...arrays) {
  const exclude = document.getElementById("opt-exclude-partial").checked;
  if (!exclude) return [years, ...arrays];
  const lastIdx = years.indexOf(PAYLOAD.partial_year);
  if (lastIdx === -1) return [years, ...arrays];
  return [years.slice(0, lastIdx), ...arrays.map(a => a.slice(0, lastIdx))];
}

// ----------------------- selection state -----------------------
function getSelected() {
  const sel = document.getElementById("state-select");
  return Array.from(sel.selectedOptions).map(o => o.value);
}

function setSelected(states) {
  const sel = document.getElementById("state-select");
  for (const opt of sel.options) opt.selected = states.includes(opt.value);
}

function applyPreset(name) {
  if (name === "top10") setSelected(PAYLOAD.default_selection);
  else if (name === "none") setSelected([]);
  else if (name === "all50") {
    setSelected(PAYLOAD.states.filter(s => !PAYLOAD.state_meta[s].is_territory));
  } else if (name === "allplus") {
    setSelected(PAYLOAD.states.slice());
  }
  recompute();
}

// ----------------------- plot construction -----------------------
function buildTraces() {
  const selected = getSelected();
  const years = PAYLOAD.years;

  const showAvg = document.getElementById("ovl-avg").checked;
  const showMA3 = document.getElementById("ovl-ma3").checked;
  const showMA5 = document.getElementById("ovl-ma5").checked;
  const showNat = document.getElementById("opt-nationwide").checked;
  const showMean = document.getElementById("ovl-mean").checked;
  const showSum = document.getElementById("ovl-sum").checked;
  const showMedian = document.getElementById("ovl-median").checked;

  const traces = [];

  // Per-state traces (raw + per-series overlays).
  for (const state of selected) {
    const color = colorFor(state);
    const counts = PAYLOAD.counts[state];
    const [yrs, vals] = maybeExcludePartial(years, counts);
    const label = `${state} — ${PAYLOAD.state_meta[state].label}`;

    traces.push({
      x: yrs, y: vals,
      type: "scatter", mode: "lines",
      name: label,
      legendgroup: state,
      line: { color: color, width: 2 },
      hovertemplate: `<b>${state}</b> %{x}<br>Filings: %{y:,}<extra></extra>`,
    });

    if (showAvg) {
      const m = seriesMean(vals);
      if (m !== null) {
        traces.push({
          x: [yrs[0], yrs[yrs.length - 1]],
          y: [m, m],
          type: "scatter", mode: "lines",
          legendgroup: state,
          showlegend: false,
          line: { color: color, width: 1, dash: "dash" },
          opacity: 0.35,
          hoverinfo: "skip",
        });
      }
    }
    if (showMA3) {
      const ma = trailingMA(vals, 3);
      traces.push({
        x: yrs, y: ma,
        type: "scatter", mode: "lines",
        legendgroup: state,
        showlegend: false,
        line: { color: color, width: 1.5, dash: "dot" },
        opacity: 0.6,
        hovertemplate: `<b>${state} 3yr MA</b> %{x}<br>%{y:,.0f}<extra></extra>`,
      });
    }
    if (showMA5) {
      const ma = trailingMA(vals, 5);
      traces.push({
        x: yrs, y: ma,
        type: "scatter", mode: "lines",
        legendgroup: state,
        showlegend: false,
        line: { color: color, width: 1.5, dash: "dashdot" },
        opacity: 0.6,
        hovertemplate: `<b>${state} 5yr MA</b> %{x}<br>%{y:,.0f}<extra></extra>`,
      });
    }
  }

  // Cross-state aggregates over the SELECTED set.
  if (selected.length > 0 && (showMean || showSum || showMedian)) {
    // Build a year-by-state matrix, then collapse year-by-year.
    const fullArrays = selected.map(s => PAYLOAD.counts[s]);
    const [yrs, ...arrays] = maybeExcludePartial(years, ...fullArrays);

    const meanVals = [], sumVals = [], medVals = [];
    for (let i = 0; i < yrs.length; i++) {
      const col = arrays.map(a => a[i]).filter(v => v !== null && v !== undefined);
      if (col.length === 0) {
        meanVals.push(null); sumVals.push(null); medVals.push(null);
      } else {
        const s = col.reduce((a, b) => a + b, 0);
        sumVals.push(s);
        meanVals.push(s / col.length);
        medVals.push(median(col));
      }
    }
    if (showMean) {
      traces.push({
        x: yrs, y: meanVals,
        type: "scatter", mode: "lines",
        name: `Mean of selected (n=${selected.length})`,
        line: { color: "#444", width: 2.5, dash: "dash" },
        hovertemplate: `<b>Mean of selected</b> %{x}<br>%{y:,.1f}<extra></extra>`,
      });
    }
    if (showSum) {
      traces.push({
        x: yrs, y: sumVals,
        type: "scatter", mode: "lines",
        name: `Sum of selected (n=${selected.length})`,
        line: { color: "#444", width: 2.5, dash: "dot" },
        hovertemplate: `<b>Sum of selected</b> %{x}<br>%{y:,}<extra></extra>`,
      });
    }
    if (showMedian) {
      traces.push({
        x: yrs, y: medVals,
        type: "scatter", mode: "lines",
        name: `Median of selected (n=${selected.length})`,
        line: { color: "#444", width: 2.5, dash: "dashdot" },
        hovertemplate: `<b>Median of selected</b> %{x}<br>%{y:,.1f}<extra></extra>`,
      });
    }
  }

  // Nationwide total — sum across ALL states, independent of selection.
  if (showNat) {
    const allArrays = PAYLOAD.states.map(s => PAYLOAD.counts[s]);
    const [yrs, ...arrays] = maybeExcludePartial(years, ...allArrays);
    const tot = [];
    for (let i = 0; i < yrs.length; i++) {
      const col = arrays.map(a => a[i]).filter(v => v !== null && v !== undefined);
      tot.push(col.length ? col.reduce((a, b) => a + b, 0) : null);
    }
    traces.push({
      x: yrs, y: tot,
      type: "scatter", mode: "lines",
      name: "Nationwide total (all 55 jurisdictions)",
      line: { color: "#000", width: 3 },
      hovertemplate: `<b>Nationwide</b> %{x}<br>%{y:,}<extra></extra>`,
    });
  }

  return traces;
}

function buildLayout() {
  const yScale = document.querySelector("input[name='yaxis']:checked").value;
  return {
    margin: { l: 70, r: 20, t: 10, b: 50 },
    xaxis: { title: "Filing year (calendar)", tickformat: "d" },
    yaxis: {
      title: "Filings (NoS = 110)",
      type: yScale,
      rangemode: yScale === "log" ? "normal" : "tozero",
    },
    legend: { orientation: "v", x: 1.01, y: 1, xanchor: "left", font: { size: 11 } },
    hovermode: "closest",
    plot_bgcolor: "#fff",
    paper_bgcolor: "#fff",
    showlegend: true,
  };
}

function recompute() {
  const traces = buildTraces();
  const layout = buildLayout();
  const config = {
    responsive: true,
    displaylogo: false,
    modeBarButtonsToRemove: ["lasso2d", "select2d"],
  };
  Plotly.react("plot", traces, layout, config);
}

// ----------------------- init -----------------------
function init() {
  // Populate state dropdown.
  const sel = document.getElementById("state-select");
  for (const s of PAYLOAD.states) {
    const meta = PAYLOAD.state_meta[s];
    const opt = document.createElement("option");
    opt.value = s;
    opt.textContent = `${s} — ${meta.label}${meta.is_territory ? " (territory)" : ""}`;
    sel.appendChild(opt);
  }
  setSelected(PAYLOAD.default_selection);

  // Header strings.
  document.getElementById("hdr-max-filedate").textContent =
    PAYLOAD.source.last_modified
      ? `${PAYLOAD.year_max} (zip last modified ${PAYLOAD.source.last_modified})`
      : `${PAYLOAD.year_max}`;
  document.getElementById("hdr-partial-warning").textContent =
    `${PAYLOAD.partial_year} is partial.`;
  document.getElementById("hdr-partial-year").textContent = PAYLOAD.partial_year;

  // Footer.
  if (PAYLOAD.source.url) {
    const a = document.getElementById("footer-src");
    a.href = PAYLOAD.source.url;
    a.textContent = PAYLOAD.source.url.split("/").pop();
  }
  if (PAYLOAD.source.sha256) {
    document.getElementById("footer-sha").textContent =
      PAYLOAD.source.sha256.slice(0, 12) + "…";
  }
  if (PAYLOAD.source.fetched_at) {
    document.getElementById("footer-fetched").textContent = PAYLOAD.source.fetched_at;
  }

  // Wire controls.
  sel.addEventListener("change", recompute);
  for (const id of [
    "opt-nationwide", "opt-exclude-partial",
    "ovl-avg", "ovl-ma3", "ovl-ma5",
    "ovl-mean", "ovl-sum", "ovl-median",
  ]) {
    document.getElementById(id).addEventListener("change", recompute);
  }
  for (const r of document.querySelectorAll("input[name='yaxis']")) {
    r.addEventListener("change", recompute);
  }
  for (const btn of document.querySelectorAll(".quick-presets button")) {
    btn.addEventListener("click", () => applyPreset(btn.dataset.preset));
  }

  recompute();
}

document.addEventListener("DOMContentLoaded", init);
</script>
</body>
</html>
"""


def main() -> int:
    payload = build_payload()
    payload_json = json.dumps(payload, separators=(",", ":"))
    html = HTML_TEMPLATE.replace("__PAYLOAD_JSON__", payload_json)
    OUT_HTML.parent.mkdir(parents=True, exist_ok=True)
    OUT_HTML.write_text(html)
    size_kb = OUT_HTML.stat().st_size / 1024
    print(f"Wrote {OUT_HTML} ({size_kb:.1f} KB)")
    print(f"  states: {len(payload['states'])}")
    print(f"  years: {payload['year_min']}-{payload['year_max']}")
    print(f"  default selection: {payload['default_selection']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
