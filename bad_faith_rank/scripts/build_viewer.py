"""Build single-file HTML viewer with embedded data, weight sliders, level editors, and tuning copy/load.

Reads bad_faith_rank/data/states_with_clusters.json and factors.json,
embeds them as JS literals into a self-contained index.html.
"""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "bad_faith_rank" / "data"
OUT = REPO / "bad_faith_rank" / "index.html"

states = json.load(open(DATA / "states_with_clusters.json"))
factors = json.load(open(DATA / "factors.json"))
state_paths = json.load(open(DATA / "us_state_paths.json"))

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>State Bad Faith Protection Rankings</title>
<style>
  :root {
    --fg: #222;
    --muted: #666;
    --border: #ddd;
    --bg: #fafafa;
    --panel-bg: #fff;
    --accent: #1f4e79;
    --t1: #1a9850; --t2: #66bd63; --t3: #fee08b; --t4: #fdae61; --t5: #d73027;
    --c0: #6a4c93; --c1: #1f78b4; --c2: #33a02c; --c3: #ff7f00; --c4: #e31a1c;
  }
  html, body { margin: 0; padding: 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Helvetica, Arial, sans-serif; color: var(--fg); background: #fff; font-size: 14px; }
  .layout { display: grid; grid-template-columns: 340px 1fr 380px; min-height: 100vh; }
  aside.sidebar { background: var(--bg); border-right: 1px solid var(--border); padding: 14px; overflow-y: auto; max-height: 100vh; }
  aside.detail { background: var(--bg); border-left: 1px solid var(--border); padding: 14px; overflow-y: auto; max-height: 100vh; }
  main.main { padding: 16px 22px 32px; overflow-y: auto; max-height: 100vh; }
  h1 { font-size: 18px; margin: 0 0 4px; }
  h2 { font-size: 12px; text-transform: uppercase; color: var(--muted); margin: 16px 0 6px; letter-spacing: 0.05em; }
  h2:first-child { margin-top: 0; }
  h3 { font-size: 14px; margin: 8px 0 6px; }
  header.title { border-bottom: 1px solid var(--border); padding-bottom: 10px; margin-bottom: 14px; }
  header.title .sub { color: var(--muted); font-size: 12px; }
  .controls { display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 14px; }
  .controls button { padding: 5px 10px; border: 1px solid var(--border); background: white; border-radius: 4px; cursor: pointer; font-size: 12px; }
  .controls button:hover { background: var(--bg); }
  .controls button.active { background: var(--accent); color: white; border-color: var(--accent); }

  .factor-block { border-top: 1px solid var(--border); padding: 6px 0 4px; }
  .factor-block:first-of-type { border-top: none; }
  .factor-summary { display: grid; grid-template-columns: 16px 1fr 70px 40px; gap: 6px; align-items: center; cursor: pointer; }
  .factor-summary .chev { color: var(--muted); font-size: 10px; transition: transform 0.1s; }
  .factor-block.open .factor-summary .chev { transform: rotate(90deg); }
  .factor-summary .factor-label { font-size: 12px; color: var(--fg); line-height: 1.25; }
  .factor-summary input[type=range] { width: 100%; margin: 0; }
  .factor-summary .weight-val { font-size: 12px; font-weight: 600; text-align: right; color: var(--accent); font-variant-numeric: tabular-nums; }
  .factor-summary .weight-val.zero { color: var(--muted); font-weight: 400; }
  .factor-levels { display: none; padding: 6px 0 8px 16px; }
  .factor-block.open .factor-levels { display: block; }
  .level-row { display: grid; grid-template-columns: 60px 1fr; gap: 8px; align-items: start; padding: 4px 6px; border-radius: 3px; }
  .level-row + .level-row { border-top: 1px dashed #eee; }
  .level-row.touched { background: #fff7d6; }
  .level-row .lv-input { width: 56px; padding: 2px 4px; font-size: 11px; font-variant-numeric: tabular-nums; border: 1px solid var(--border); border-radius: 3px; text-align: right; }
  .level-row .lv-name { font-size: 11px; font-weight: 600; color: var(--fg); }
  .level-row .lv-explain { font-size: 11px; color: var(--muted); margin-top: 1px; line-height: 1.35; }
  .level-row .lv-states { font-size: 10px; color: #888; margin-top: 2px; font-style: italic; }
  .level-reset { font-size: 10px; color: var(--accent); cursor: pointer; margin-top: 4px; display: inline-block; }
  .level-reset:hover { text-decoration: underline; }

  .weight-sum { font-size: 11px; color: var(--muted); margin-top: 6px; }

  table.ranking { border-collapse: collapse; width: 100%; font-size: 13px; }
  table.ranking thead th { text-align: left; padding: 4px 6px; border-bottom: 1px solid var(--border); background: var(--bg); position: sticky; top: 0; font-weight: 600; }
  table.ranking td { padding: 4px 6px; border-bottom: 1px solid #eee; vertical-align: middle; }
  table.ranking tr { cursor: pointer; }
  table.ranking tr:hover td { background: #f0f6ff; }
  table.ranking tr.active td { background: #e3edf7; }
  table.ranking td.rank { font-weight: 600; color: var(--muted); width: 32px; }
  table.ranking td.score { font-variant-numeric: tabular-nums; font-weight: 600; width: 50px; text-align: right; }
  table.ranking td.delta { font-variant-numeric: tabular-nums; font-size: 11px; width: 36px; text-align: right; }
  table.ranking td.delta.up { color: #1a9850; }
  table.ranking td.delta.down { color: #d73027; }
  .tier-pill { display: inline-block; padding: 1px 6px; border-radius: 3px; font-size: 10px; font-weight: 700; color: white; min-width: 22px; text-align: center; }
  .tier-T1 { background: var(--t1); } .tier-T2 { background: var(--t2); }
  .tier-T3 { background: var(--t3); color: #444; } .tier-T4 { background: var(--t4); }
  .tier-T5 { background: var(--t5); }
  .cluster-pill { display: inline-block; padding: 1px 6px; border-radius: 3px; font-size: 10px; font-weight: 600; color: white; }
  .cluster-S0_admin_hybrid { background: var(--c0); }
  .cluster-S1_multi_tool_statutory { background: var(--c1); }
  .cluster-S2_statute_constrained { background: var(--c2); }
  .cluster-S3_common_law_tort { background: var(--c3); }
  .cluster-S4_minimal_protection { background: var(--c4); }

  .factor-bar { background: #f0f0f0; border-radius: 3px; height: 10px; position: relative; margin: 2px 0; }
  .factor-bar .fill { background: var(--accent); height: 100%; border-radius: 3px; }
  .factor-row { display: grid; grid-template-columns: 1fr 50px; gap: 6px; align-items: center; padding: 4px 0; border-bottom: 1px solid #eee; }
  .factor-row .lbl { font-size: 11px; color: var(--muted); }
  .factor-row .lbl b { color: var(--fg); font-weight: 600; }
  .factor-row .num { font-size: 12px; font-weight: 700; font-variant-numeric: tabular-nums; text-align: right; }
  .factor-detail { font-size: 11px; color: var(--muted); margin-top: 2px; padding-left: 8px; border-left: 2px solid var(--border); }
  .factor-detail .cite { color: #444; font-style: italic; margin-top: 2px; }

  details { margin: 6px 0; }
  details summary { cursor: pointer; font-size: 12px; color: var(--accent); }
  .meta-block { font-size: 11px; color: var(--muted); padding: 8px; background: var(--bg); border-radius: 4px; margin-bottom: 10px; line-height: 1.45; }
  .meta-block code { background: white; padding: 1px 4px; border-radius: 2px; }

  .preset-btn { font-size: 11px; padding: 3px 7px; border: 1px solid var(--border); background: white; border-radius: 3px; cursor: pointer; margin: 2px 2px 2px 0; }
  .preset-btn:hover { background: var(--bg); }
  .preset-btn.active { background: var(--accent); color: white; border-color: var(--accent); }

  .tuning-row { display: flex; gap: 6px; flex-wrap: wrap; margin-bottom: 10px; }
  .tuning-row button { font-size: 11px; padding: 4px 10px; border: 1px solid var(--accent); background: white; color: var(--accent); border-radius: 3px; cursor: pointer; }
  .tuning-row button:hover { background: var(--accent); color: white; }
  .tuning-feedback { font-size: 11px; color: var(--muted); margin-top: 2px; min-height: 14px; }
  .tuning-feedback.ok { color: #1a9850; }
  .tuning-feedback.err { color: #d73027; }
  textarea#tuning-paste { width: 100%; height: 90px; font-family: ui-monospace, Menlo, Consolas, monospace; font-size: 11px; padding: 6px; box-sizing: border-box; border: 1px solid var(--border); border-radius: 3px; }

  .legend { display: flex; gap: 10px; flex-wrap: wrap; font-size: 11px; margin: 6px 0 12px; }
  .legend .item { display: flex; align-items: center; gap: 4px; }
  .legend .swatch { width: 12px; height: 12px; border-radius: 2px; }

  #cluster-info { font-size: 11px; color: var(--muted); padding: 6px 8px; background: var(--bg); border-radius: 4px; margin-bottom: 8px; min-height: 40px; }
  #cluster-info b { color: var(--fg); }

  .factor-cat { font-size: 10px; color: var(--muted); text-transform: uppercase; margin: 12px 0 4px; letter-spacing: 0.05em; font-weight: 600; }
  .factor-cat:first-of-type { margin-top: 6px; }

  /* US map */
  .map-wrap { position: relative; margin: 6px 0 14px; }
  svg#us-map { width: 100%; height: auto; display: block; background: linear-gradient(180deg,#fbfcfd 0%,#f4f7fa 100%); border: 1px solid var(--border); border-radius: 6px; }
  svg#us-map .state-path { stroke: #fff; stroke-width: 0.75; stroke-linejoin: round; cursor: pointer; transition: filter 0.08s, stroke-width 0.08s; }
  svg#us-map .state-path:hover { stroke: #222; stroke-width: 1.4; filter: brightness(1.06); }
  svg#us-map .state-path.selected { stroke: #111; stroke-width: 2.2; filter: drop-shadow(0 0 3px rgba(31,78,121,0.45)); }
  svg#us-map .dc-inset rect { stroke: #fff; stroke-width: 1; cursor: pointer; transition: filter 0.08s, stroke-width 0.08s; }
  svg#us-map .dc-inset:hover rect { stroke: #222; stroke-width: 1.6; filter: brightness(1.06); }
  svg#us-map .dc-inset.selected rect { stroke: #111; stroke-width: 2.4; filter: drop-shadow(0 0 3px rgba(31,78,121,0.45)); }
  svg#us-map .dc-inset text { font-size: 11px; font-weight: 700; fill: #fff; text-anchor: middle; pointer-events: none; paint-order: stroke; stroke: rgba(0,0,0,0.35); stroke-width: 0.6; }
  svg#us-map .dc-leader { stroke: #888; stroke-width: 0.6; stroke-dasharray: 2 2; fill: none; }
  .map-tooltip { position: fixed; pointer-events: none; background: #222; color: #fff; padding: 5px 8px; border-radius: 4px; font-size: 11px; line-height: 1.35; white-space: nowrap; box-shadow: 0 2px 8px rgba(0,0,0,0.18); opacity: 0; transition: opacity 0.08s; z-index: 50; }
  .map-tooltip b { color: #fff; }
  .map-tooltip.show { opacity: 1; }
</style>
</head>
<body>
<div class="layout">

<aside class="sidebar">
  <h1>Bad faith protection ranking</h1>
  <div class="sub" id="sidebar-sub" style="font-size:11px; color:var(--muted); margin-bottom:10px;"></div>

  <h2>Weight presets</h2>
  <div id="preset-buttons">
    <button class="preset-btn active" data-preset="default">Default</button>
    <button class="preset-btn" data-preset="doctrine">Doctrine-only</button>
    <button class="preset-btn" data-preset="statutory">Statutory teeth</button>
    <button class="preset-btn" data-preset="access">Access / cost</button>
    <button class="preset-btn" data-preset="uniform">Uniform</button>
    <button class="preset-btn" data-preset="custom">Custom</button>
  </div>

  <div class="tuning-row">
    <button id="copy-tuning-btn" title="Copy current weights and any level overrides as JSON to your clipboard">Copy tuning</button>
    <button id="toggle-load-btn" title="Paste a previously copied tuning JSON to restore it">Load tuning</button>
  </div>
  <div class="tuning-feedback" id="tuning-feedback"></div>
  <details id="tuning-load-panel" style="margin-bottom:10px;">
    <summary style="font-size:11px;">Paste tuning JSON</summary>
    <textarea id="tuning-paste" placeholder='{ "preset": "custom", "weights": { ... }, "level_overrides": { ... } }'></textarea>
    <div style="margin-top:4px;">
      <button id="apply-tuning-btn" style="font-size:11px; padding:4px 10px; border:1px solid var(--accent); background:white; color:var(--accent); border-radius:3px; cursor:pointer;">Apply</button>
    </div>
  </details>

  <h2>Color by</h2>
  <div class="controls">
    <button class="color-btn active" data-color="tier">Score-band tier</button>
    <button class="color-btn" data-color="cluster">Structural cluster</button>
  </div>

  <h2>Factor weights <span style="font-weight:400;font-size:10px;color:var(--muted);" id="weight-sum">total: 1.00</span></h2>
  <div style="font-size:11px; color:var(--muted); margin-bottom:6px;">Click any factor to view and edit its levels.</div>
  <div id="factors-list"></div>

  <details style="margin-top:14px;">
    <summary>About this rubric</summary>
    <div class="meta-block">
      Each factor is scored 0–10 along a small set of named levels (with brief explainers). The state ranking is the weighted average of factor scores, normalized to 0–10 — so the absolute size of weights doesn't matter, only their ratios. Re-weight any factor and edit any level value to fit your own framing. See <code>METHODOLOGY.md</code> in this folder for sources and per-state citations.
    </div>
  </details>
</aside>

<main class="main">
  <header class="title">
    <h1 id="rank-title">Default-weighted ranking</h1>
    <div class="sub" id="rank-sub"></div>
  </header>

  <div class="map-wrap">
    <svg id="us-map" viewBox="0 0 975 660" xmlns="http://www.w3.org/2000/svg" role="img" aria-label="US map of bad faith protection scores"></svg>
    <div class="map-tooltip" id="map-tooltip"></div>
  </div>

  <div id="cluster-info"></div>

  <table class="ranking">
    <thead>
      <tr>
        <th>#</th>
        <th>State</th>
        <th>Score</th>
        <th>Δ</th>
        <th>Tier</th>
        <th>Cluster</th>
      </tr>
    </thead>
    <tbody id="ranking-body"></tbody>
  </table>
</main>

<aside class="detail">
  <h1 id="detail-title">Select a state</h1>
  <div class="sub" style="font-size:11px; color:var(--muted); margin-bottom:10px;" id="detail-sub">Click a row in the ranking</div>
  <div id="detail-body"></div>
</aside>

</div>

<script>
const FACTORS = __FACTORS_JSON__;
const DATA = __DATA_JSON__;
const STATE_PATHS = __STATE_PATHS_JSON__;

// Cluster colors mirror the --c0..--c4 CSS vars so the map and the cluster pills stay consistent.
const CLUSTER_COLORS = {
  S0_admin_hybrid: '#6a4c93',
  S1_multi_tool_statutory: '#1f78b4',
  S2_statute_constrained: '#33a02c',
  S3_common_law_tort: '#ff7f00',
  S4_minimal_protection: '#e31a1c',
};

// --- preset definitions -------------------------------------------------
// Weights are floats. The score formula divides by sum(weights), so absolute
// magnitude is cosmetic — what matters is the ratio across factors.
const PRESETS = {
  default: Object.fromEntries(FACTORS.map(f => [f.id, f.default_weight])),
  // doctrine-only: zero out non-doctrinal factors
  doctrine: Object.fromEntries(FACTORS.map(f => [f.id, f.category === 'doctrinal' ? f.default_weight : 0])),
  // statutory teeth: up-weight statutory PRoA, statutory penalty, attorney fees
  statutory: { f1a_first_party_cause: 0.02, f1b_third_party_cause: 0.01, f2_statutory_proa: 0.25, f3_liability_standard: 0.04, f4_extracontractual_damages: 0.08, f5_punitive_damages: 0.04, f6_statutory_penalty: 0.22, f7_attorney_fees: 0.18, f8_pre_suit_barriers: 0.06, f9_admin_remedy: 0.05, f10_recent_appellate_trend: 0.05 },
  // access / cost: up-weight fee shifting, low pre-suit barriers, admin remedy
  access: { f1a_first_party_cause: 0.06, f1b_third_party_cause: 0.03, f2_statutory_proa: 0.10, f3_liability_standard: 0.06, f4_extracontractual_damages: 0.08, f5_punitive_damages: 0.04, f6_statutory_penalty: 0.08, f7_attorney_fees: 0.22, f8_pre_suit_barriers: 0.14, f9_admin_remedy: 0.14, f10_recent_appellate_trend: 0.05 },
  // uniform: every factor weighted equally
  uniform: Object.fromEntries(FACTORS.map(f => [f.id, 1])),
  // custom: not a fixed dict — keep current weights when selected; built dynamically below
};

const PRESET_EXPLAINERS = {
  default:   "Strength of state-level bad faith protection for individual P&amp;C insureds. <b>Not authoritative</b> — a starting point. Researchers and advocates are invited to re-weight factors and adjust level values to reach their own conclusions.",
  doctrine:  "Zeros out procedural and environment factors. Ranks states purely on substantive bad-faith doctrine (causes of action, damages, penalties, fee-shifting, liability standard).",
  statutory: "Up-weights statutory PRoA, statutory penalty/multiplier, and attorney-fee shifting. Down-weights common-law-only routes. Surfaces states with sharp, codified remedies.",
  access:    "Up-weights fee shifting, low pre-suit barriers, and administrative-remedy strength. Surfaces states where a real claimant can actually reach a remedy without an unreasonable cost barrier.",
  uniform:   "Every factor weighted equally. Useful as a sanity check against any preset's emphasis.",
  custom:    "Tune freely. Use the sliders below to set any weighting; click any factor to edit its level values.",
};

const PRESET_TITLES = {
  default:   "Default-weighted ranking",
  doctrine:  "Doctrine-only ranking",
  statutory: "Statutory-teeth-weighted ranking",
  access:    "Access / cost-weighted ranking",
  uniform:   "Uniformly-weighted ranking",
  custom:    "Custom-weighted ranking",
};

// --- mutable state -----------------------------------------------------
let activePreset = 'default';
let weights = {...PRESETS.default};
// levelValues[fid] = array of current numeric values, indexed by level idx.
// Initialized from factor.levels[i].value; user edits override these.
let levelValues = {};
FACTORS.forEach(f => { levelValues[f.id] = f.levels.map(l => l.value); });
let colorMode = 'tier';
let selectedState = null;
let prevRanking = {};

// --- DOM refs ----------------------------------------------------------
const factorsList = document.getElementById('factors-list');
const rankingBody = document.getElementById('ranking-body');
const weightSumEl = document.getElementById('weight-sum');
const clusterInfo = document.getElementById('cluster-info');
const rankTitle = document.getElementById('rank-title');
const rankSub = document.getElementById('rank-sub');
const sidebarSub = document.getElementById('sidebar-sub');
const tuningFeedback = document.getElementById('tuning-feedback');
const mapSvg = document.getElementById('us-map');
const mapTooltip = document.getElementById('map-tooltip');

// --- helpers ----------------------------------------------------------
function fmtWeight(w) { return (Math.round(w * 100) / 100).toFixed(2); }
function escapeHtml(s) { return String(s == null ? '' : s).replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }

function levelValue(state, factor) {
  const idx = state.scores[factor.id].level;
  return levelValues[factor.id][idx];
}

function statesAtLevel(fid, levelIdx) {
  return DATA.states.filter(s => s.scores[fid].level === levelIdx).map(s => s.state);
}

function computeScore(state) {
  let num = 0, den = 0;
  FACTORS.forEach(f => {
    const w = weights[f.id] || 0;
    if (w === 0) return;
    num += levelValue(state, f) * w;
    den += w;
  });
  return den > 0 ? num / den : 0;
}

function totalWeight() {
  return FACTORS.reduce((sum, f) => sum + (weights[f.id] || 0), 0);
}

// --- factor list / sliders / level editors ----------------------------
function buildFactorsList() {
  factorsList.innerHTML = '';
  const cats = ['doctrinal','procedural','environment'];
  const catLabel = {doctrinal:'Doctrinal', procedural:'Procedural / Access', environment:'Environment'};
  cats.forEach(cat => {
    const facs = FACTORS.filter(f => f.category === cat);
    if (!facs.length) return;
    const header = document.createElement('div');
    header.className = 'factor-cat';
    header.textContent = catLabel[cat];
    factorsList.appendChild(header);
    facs.forEach(f => factorsList.appendChild(buildFactorBlock(f)));
  });
  weightSumEl.textContent = 'total: ' + fmtWeight(totalWeight());
}

function buildFactorBlock(f) {
  const block = document.createElement('div');
  block.className = 'factor-block';
  block.dataset.fid = f.id;

  const w = weights[f.id] || 0;
  const summary = document.createElement('div');
  summary.className = 'factor-summary';
  summary.innerHTML =
    '<span class="chev">▶</span>' +
    '<span class="factor-label">' + escapeHtml(f.label) + '</span>' +
    '<input type="range" min="0" max="1" step="0.01" value="' + w + '" data-fid="' + f.id + '">' +
    '<span class="weight-val' + (w === 0 ? ' zero' : '') + '" id="wv-' + f.id + '">' + fmtWeight(w) + '</span>';
  block.appendChild(summary);

  const levelsDiv = document.createElement('div');
  levelsDiv.className = 'factor-levels';
  rebuildLevelsDiv(levelsDiv, f);
  block.appendChild(levelsDiv);

  // expand/collapse: click anywhere on the summary EXCEPT the slider toggles open state
  summary.addEventListener('click', (ev) => {
    if (ev.target.tagName === 'INPUT') return;
    block.classList.toggle('open');
  });

  const slider = summary.querySelector('input[type=range]');
  slider.addEventListener('input', e => {
    const v = parseFloat(e.target.value);
    weights[f.id] = v;
    const wv = document.getElementById('wv-' + f.id);
    wv.textContent = fmtWeight(v);
    wv.classList.toggle('zero', v === 0);
    weightSumEl.textContent = 'total: ' + fmtWeight(totalWeight());
    setActivePreset('custom');
    rerank();
  });
  // prevent collapse-toggle when interacting with the slider
  slider.addEventListener('click', e => e.stopPropagation());

  return block;
}

function rebuildLevelsDiv(div, f) {
  div.innerHTML = '';
  f.levels.forEach((lvl, i) => {
    const row = document.createElement('div');
    row.className = 'level-row';
    const cur = levelValues[f.id][i];
    const touched = cur !== lvl.value;
    if (touched) row.classList.add('touched');
    const at = statesAtLevel(f.id, i);
    const stateLine = at.length
      ? at.length + ' state' + (at.length === 1 ? '' : 's') + ': ' + at.join(', ')
      : 'no states currently at this level';
    row.innerHTML =
      '<div><input type="number" class="lv-input" min="0" max="10" step="0.1" value="' + cur + '" data-fid="' + f.id + '" data-idx="' + i + '"></div>' +
      '<div>' +
        '<div class="lv-name">' + escapeHtml(lvl.name) + '</div>' +
        '<div class="lv-explain">' + escapeHtml(lvl.explainer) + '</div>' +
        '<div class="lv-states">' + escapeHtml(stateLine) + '</div>' +
      '</div>';
    div.appendChild(row);

    const input = row.querySelector('input.lv-input');
    input.addEventListener('input', e => {
      const v = parseFloat(e.target.value);
      if (Number.isNaN(v)) return;
      levelValues[f.id][i] = v;
      row.classList.toggle('touched', v !== lvl.value);
      setActivePreset('custom');
      rerank();
    });
    input.addEventListener('click', e => e.stopPropagation());
  });

  // Per-factor reset link
  const reset = document.createElement('span');
  reset.className = 'level-reset';
  reset.textContent = '↺ Reset levels to defaults';
  reset.addEventListener('click', e => {
    e.stopPropagation();
    levelValues[f.id] = f.levels.map(l => l.value);
    rebuildLevelsDiv(div, f);
    rerank();
  });
  div.appendChild(reset);
}

// --- preset switching --------------------------------------------------
function setActivePreset(id) {
  activePreset = id;
  document.querySelectorAll('.preset-btn').forEach(b => {
    b.classList.toggle('active', b.dataset.preset === id);
  });
  rankSub.innerHTML = PRESET_EXPLAINERS[id] || '';
  rankTitle.textContent = PRESET_TITLES[id] || 'Ranking';
}

function applyPreset(id) {
  if (id === 'custom') {
    setActivePreset('custom');
    return;
  }
  weights = {...PRESETS[id]};
  setActivePreset(id);
  // Rebuild factor list to refresh slider values and weight displays
  buildFactorsList();
  rerank();
}

document.querySelectorAll('.preset-btn').forEach(btn => {
  btn.addEventListener('click', () => applyPreset(btn.dataset.preset));
});

// --- ranking render ---------------------------------------------------
function rerank() {
  weightSumEl.textContent = 'total: ' + fmtWeight(totalWeight());

  const ranked = DATA.states.map(s => ({...s, computed_score: computeScore(s)}));
  ranked.sort((a, b) => b.computed_score - a.computed_score);
  let curRank = 0, prevScore = null;
  ranked.forEach((s, i) => {
    if (s.computed_score !== prevScore) { curRank = i + 1; prevScore = s.computed_score; }
    s.rank = curRank;
  });

  rankingBody.innerHTML = '';
  ranked.forEach(s => {
    const tr = document.createElement('tr');
    tr.dataset.state = s.state;
    if (selectedState === s.state) tr.classList.add('active');
    const tierBand = DATA.tier_bands.find(b => s.computed_score >= b.min_score) || DATA.tier_bands[DATA.tier_bands.length-1];
    const cluster = DATA.structural_clusters.find(c => c.id === s.structural_cluster);
    const prevR = prevRanking[s.state];
    let deltaCell = '';
    if (prevR !== undefined && prevR !== s.rank) {
      const d = prevR - s.rank;
      const cls = d > 0 ? 'up' : 'down';
      const sign = d > 0 ? '▲' : '▼';
      deltaCell = '<td class="delta ' + cls + '">' + sign + Math.abs(d) + '</td>';
    } else {
      deltaCell = '<td class="delta">·</td>';
    }
    tr.innerHTML =
      '<td class="rank">' + s.rank + '</td>' +
      '<td><b>' + s.state + '</b> ' + s.state_name + '</td>' +
      '<td class="score">' + s.computed_score.toFixed(2) + '</td>' +
      deltaCell +
      '<td><span class="tier-pill tier-' + tierBand.id + '">' + tierBand.id + '</span></td>' +
      '<td><span class="cluster-pill cluster-' + s.structural_cluster + '" title="' + cluster.label + '">' + cluster.label.split(/[ /]/)[0] + '</span></td>';
    tr.addEventListener('click', () => selectState(s.state));
    rankingBody.appendChild(tr);
  });

  prevRanking = Object.fromEntries(ranked.map(s => [s.state, s.rank]));

  paintMap(ranked);
  if (selectedState) renderDetail(selectedState);
}

// --- map render -------------------------------------------------------
const SVG_NS = 'http://www.w3.org/2000/svg';
// DC inset: a labeled square placed in the bottom-right margin of the SVG, with a
// dashed leader pointing at DC's true geographic location (~828,267 in the Albers
// projection).  Real DC is ~3 SVG units wide on the geographic map — too small to
// click — so the inset is the actual click target.
const DC_INSET = { x: 870, y: 580, size: 38, geoX: 828, geoY: 268 };

function buildMap() {
  // Render the 50 states as <path> elements, then a DC inset as a labeled square.
  const stateLookup = Object.fromEntries(DATA.states.map(s => [s.state, s]));

  // 50 states (skip DC — handled separately as inset).
  Object.entries(STATE_PATHS).forEach(([code, d]) => {
    if (code === 'DC') return;
    const path = document.createElementNS(SVG_NS, 'path');
    path.setAttribute('d', d);
    path.setAttribute('class', 'state-path');
    path.setAttribute('id', 'state-' + code);
    path.dataset.state = code;
    path.addEventListener('click', () => selectState(code));
    attachTooltip(path, code, stateLookup);
    mapSvg.appendChild(path);
  });

  // DC inset group (leader line + labeled square).
  const leader = document.createElementNS(SVG_NS, 'path');
  leader.setAttribute('class', 'dc-leader');
  const lx1 = DC_INSET.geoX, ly1 = DC_INSET.geoY;
  const lx2 = DC_INSET.x, ly2 = DC_INSET.y + DC_INSET.size / 2;
  leader.setAttribute('d', `M${lx1},${ly1}L${lx2},${ly2}`);
  mapSvg.appendChild(leader);

  const dcGroup = document.createElementNS(SVG_NS, 'g');
  dcGroup.setAttribute('class', 'dc-inset');
  dcGroup.dataset.state = 'DC';
  dcGroup.setAttribute('id', 'state-DC');
  const dcRect = document.createElementNS(SVG_NS, 'rect');
  dcRect.setAttribute('x', DC_INSET.x);
  dcRect.setAttribute('y', DC_INSET.y);
  dcRect.setAttribute('width', DC_INSET.size);
  dcRect.setAttribute('height', DC_INSET.size);
  dcRect.setAttribute('rx', 4);
  dcGroup.appendChild(dcRect);
  const dcLabel = document.createElementNS(SVG_NS, 'text');
  dcLabel.setAttribute('x', DC_INSET.x + DC_INSET.size / 2);
  dcLabel.setAttribute('y', DC_INSET.y + DC_INSET.size / 2 + 4);
  dcLabel.textContent = 'DC';
  dcGroup.appendChild(dcLabel);
  dcGroup.addEventListener('click', () => selectState('DC'));
  attachTooltip(dcGroup, 'DC', stateLookup);
  mapSvg.appendChild(dcGroup);
}

function attachTooltip(el, code, stateLookup) {
  el.addEventListener('mousemove', e => {
    const s = stateLookup[code];
    if (!s) return;
    const score = computeScore(s);
    const tierBand = DATA.tier_bands.find(b => score >= b.min_score) || DATA.tier_bands[DATA.tier_bands.length-1];
    const cluster = DATA.structural_clusters.find(c => c.id === s.structural_cluster);
    const right = colorMode === 'cluster'
      ? '<b>' + cluster.label + '</b>'
      : '<b>' + score.toFixed(2) + '</b> · ' + tierBand.label;
    mapTooltip.innerHTML = '<b>' + s.state_name + '</b> &middot; ' + right;
    mapTooltip.style.left = (e.clientX + 12) + 'px';
    mapTooltip.style.top = (e.clientY + 12) + 'px';
    mapTooltip.classList.add('show');
  });
  el.addEventListener('mouseleave', () => {
    mapTooltip.classList.remove('show');
  });
}

function fillForState(s, score) {
  if (colorMode === 'cluster') return CLUSTER_COLORS[s.structural_cluster] || '#999';
  const tierBand = DATA.tier_bands.find(b => score >= b.min_score) || DATA.tier_bands[DATA.tier_bands.length-1];
  return tierBand.color;
}

function paintMap(ranked) {
  const list = ranked || DATA.states.map(s => ({...s, computed_score: computeScore(s)}));
  list.forEach(s => {
    const color = fillForState(s, s.computed_score);
    const el = document.getElementById('state-' + s.state);
    if (!el) return;
    if (s.state === 'DC') {
      el.querySelector('rect').setAttribute('fill', color);
    } else {
      el.setAttribute('fill', color);
    }
  });
}

// --- detail render ----------------------------------------------------
function selectState(code) {
  selectedState = code;
  document.querySelectorAll('table.ranking tr').forEach(tr => {
    tr.classList.toggle('active', tr.dataset.state === code);
  });
  mapSvg.querySelectorAll('.state-path, .dc-inset').forEach(el => {
    el.classList.toggle('selected', el.dataset.state === code);
  });
  renderDetail(code);
}

function renderDetail(code) {
  const s = DATA.states.find(x => x.state === code);
  const cluster = DATA.structural_clusters.find(c => c.id === s.structural_cluster);
  const score = computeScore(s);
  const tierBand = DATA.tier_bands.find(b => score >= b.min_score) || DATA.tier_bands[DATA.tier_bands.length-1];

  document.getElementById('detail-title').textContent = s.state_name;
  document.getElementById('detail-sub').innerHTML =
    'Score: <b>' + score.toFixed(2) + '</b> · ' +
    '<span class="tier-pill tier-' + tierBand.id + '">' + tierBand.label + '</span> · ' +
    '<span class="cluster-pill cluster-' + s.structural_cluster + '">' + cluster.label + '</span>';

  let html = '<div class="meta-block"><b>' + cluster.label + '.</b> ' + cluster.description + '</div>';
  html += '<h3>Per-factor breakdown</h3>';
  FACTORS.forEach(f => {
    const fs = s.scores[f.id];
    const w = weights[f.id] || 0;
    const lvl = f.levels[fs.level];
    const lvlVal = levelValues[f.id][fs.level];
    const fillPct = (lvlVal / 10) * 100;
    html +=
      '<div class="factor-row">' +
        '<div>' +
          '<div class="lbl"><b>' + escapeHtml(f.label) + '</b> · weight ' + fmtWeight(w) + ' · level: ' + escapeHtml(lvl.name) + '</div>' +
          '<div class="factor-bar"><div class="fill" style="width:' + fillPct + '%"></div></div>' +
        '</div>' +
        '<div class="num">' + lvlVal.toFixed(1) + '</div>' +
      '</div>' +
      '<div class="factor-detail">' + escapeHtml(fs.rationale) +
        (fs.cite ? '<div class="cite">' + escapeHtml(fs.cite) + '</div>' : '') +
      '</div>';
  });
  document.getElementById('detail-body').innerHTML = html;
}

// --- color mode buttons ----------------------------------------------
document.querySelectorAll('.color-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.color-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    colorMode = btn.dataset.color;
    if (colorMode === 'cluster') {
      let html = '<b>Structural clusters</b> (factor-profile based, weight-independent):<br>';
      DATA.structural_clusters.forEach(c => {
        html += '<span class="cluster-pill cluster-' + c.id + '" style="margin:2px 6px 2px 0;">' + c.label + '</span>';
      });
      clusterInfo.innerHTML = html;
    } else {
      let html = '<b>Score-band tiers</b> (current weights):<br>';
      DATA.tier_bands.forEach(b => {
        html += '<span class="tier-pill tier-' + b.id + '" style="margin:2px 6px 2px 0;">' + b.label + ' (≥' + b.min_score + ')</span>';
      });
      clusterInfo.innerHTML = html;
    }
    paintMap();
  });
});

// --- copy / load tuning ----------------------------------------------
function buildTuningPayload() {
  const level_overrides = {};
  FACTORS.forEach(f => {
    const diffs = {};
    f.levels.forEach((l, i) => {
      if (levelValues[f.id][i] !== l.value) diffs[i] = levelValues[f.id][i];
    });
    if (Object.keys(diffs).length) level_overrides[f.id] = diffs;
  });
  return {
    preset: activePreset,
    weights: {...weights},
    level_overrides,
  };
}

function flashFeedback(msg, kind) {
  tuningFeedback.textContent = msg;
  tuningFeedback.className = 'tuning-feedback ' + (kind || '');
  if (kind === 'ok') {
    setTimeout(() => { tuningFeedback.textContent = ''; tuningFeedback.className = 'tuning-feedback'; }, 2500);
  }
}

document.getElementById('copy-tuning-btn').addEventListener('click', async () => {
  const payload = buildTuningPayload();
  const text = JSON.stringify(payload, null, 2);
  try {
    await navigator.clipboard.writeText(text);
    flashFeedback('Copied tuning JSON to clipboard.', 'ok');
  } catch (e) {
    // Fallback: open a new window so user can copy manually
    const w = window.open('', '_blank');
    if (w) {
      w.document.title = 'Bad faith protection ranking — tuning';
      w.document.body.innerHTML = '<pre style="font-family:ui-monospace,Menlo,Consolas,monospace;font-size:12px;padding:12px;">' + text.replace(/[&<>]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;'}[c])) + '</pre>';
      flashFeedback('Clipboard blocked — opened tuning JSON in a new window.', 'ok');
    } else {
      flashFeedback('Could not copy or open a window.', 'err');
    }
  }
});

document.getElementById('toggle-load-btn').addEventListener('click', () => {
  const panel = document.getElementById('tuning-load-panel');
  panel.open = !panel.open;
  if (panel.open) document.getElementById('tuning-paste').focus();
});

document.getElementById('apply-tuning-btn').addEventListener('click', () => {
  const text = document.getElementById('tuning-paste').value.trim();
  if (!text) { flashFeedback('Paste tuning JSON first.', 'err'); return; }
  let payload;
  try {
    payload = JSON.parse(text);
  } catch (e) {
    flashFeedback('Invalid JSON: ' + e.message, 'err');
    return;
  }
  if (!payload || typeof payload !== 'object') { flashFeedback('Tuning JSON must be an object.', 'err'); return; }

  // Apply weights
  if (payload.weights && typeof payload.weights === 'object') {
    FACTORS.forEach(f => {
      if (typeof payload.weights[f.id] === 'number' && isFinite(payload.weights[f.id])) {
        weights[f.id] = Math.max(0, Math.min(1, payload.weights[f.id]));
      }
    });
  }
  // Apply level overrides
  FACTORS.forEach(f => { levelValues[f.id] = f.levels.map(l => l.value); });
  if (payload.level_overrides && typeof payload.level_overrides === 'object') {
    Object.entries(payload.level_overrides).forEach(([fid, diffs]) => {
      const f = FACTORS.find(x => x.id === fid);
      if (!f || !diffs || typeof diffs !== 'object') return;
      Object.entries(diffs).forEach(([idxStr, val]) => {
        const idx = parseInt(idxStr, 10);
        if (Number.isInteger(idx) && idx >= 0 && idx < f.levels.length && typeof val === 'number' && isFinite(val)) {
          levelValues[f.id][idx] = Math.max(0, Math.min(10, val));
        }
      });
    });
  }
  const presetId = (payload.preset && PRESET_EXPLAINERS[payload.preset]) ? payload.preset : 'custom';
  setActivePreset(presetId);
  buildFactorsList();
  rerank();
  flashFeedback('Tuning applied.', 'ok');
});

// --- init -------------------------------------------------------------
sidebarSub.textContent = DATA.states.length + ' jurisdictions · live re-rank';
setActivePreset('default');
buildFactorsList();
buildMap();
document.querySelector('.color-btn.active').click();
rerank();
selectState(DATA.states[0].state);
</script>
</body>
</html>
"""

html = HTML.replace("__FACTORS_JSON__", json.dumps(factors))
html = html.replace("__DATA_JSON__", json.dumps(states))
html = html.replace("__STATE_PATHS_JSON__", json.dumps(state_paths))
OUT.write_text(html)
print(f"wrote {OUT} ({len(html):,} bytes)")
