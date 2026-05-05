"""Build single-file HTML viewer with embedded data and weight sliders.

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

HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>State Bad-Faith Protection Ranking</title>
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
  .layout { display: grid; grid-template-columns: 320px 1fr 380px; min-height: 100vh; }
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
  .slider-row { display: grid; grid-template-columns: 1fr 36px; gap: 6px; align-items: center; margin: 4px 0; }
  .slider-row label { font-size: 12px; color: var(--fg); }
  .slider-row .factor-label { font-size: 11px; color: var(--muted); display: block; margin-bottom: 2px; }
  .slider-row input[type=range] { width: 100%; }
  .slider-row .weight-val { font-size: 12px; font-weight: 600; text-align: right; min-width: 30px; color: var(--accent); }
  .slider-row .weight-val.zero { color: var(--muted); font-weight: 400; }
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
  .factor-row { display: grid; grid-template-columns: 1fr 22px; gap: 6px; align-items: center; padding: 4px 0; border-bottom: 1px solid #eee; }
  .factor-row .lbl { font-size: 11px; color: var(--muted); }
  .factor-row .lbl b { color: var(--fg); font-weight: 600; }
  .factor-row .num { font-size: 12px; font-weight: 700; font-variant-numeric: tabular-nums; text-align: right; }
  .factor-detail { font-size: 11px; color: var(--muted); margin-top: 2px; padding-left: 8px; border-left: 2px solid var(--border); }
  .factor-detail .cite { color: #444; font-style: italic; margin-top: 2px; }

  details { margin: 6px 0; }
  details summary { cursor: pointer; font-size: 12px; color: var(--accent); }
  .meta-block { font-size: 11px; color: var(--muted); padding: 8px; background: var(--bg); border-radius: 4px; margin-bottom: 12px; }
  .meta-block code { background: white; padding: 1px 4px; border-radius: 2px; }
  .preset-btn { font-size: 11px; padding: 3px 7px; border: 1px solid var(--border); background: white; border-radius: 3px; cursor: pointer; margin: 2px 2px 2px 0; }
  .preset-btn:hover { background: var(--bg); }
  .preset-btn.active { background: var(--accent); color: white; border-color: var(--accent); }

  .legend { display: flex; gap: 10px; flex-wrap: wrap; font-size: 11px; margin: 6px 0 12px; }
  .legend .item { display: flex; align-items: center; gap: 4px; }
  .legend .swatch { width: 12px; height: 12px; border-radius: 2px; }

  #cluster-info { font-size: 11px; color: var(--muted); padding: 6px 8px; background: var(--bg); border-radius: 4px; margin-bottom: 8px; min-height: 40px; }
  #cluster-info b { color: var(--fg); }

  .factor-cat { font-size: 10px; color: var(--muted); text-transform: uppercase; margin-top: 8px; margin-bottom: 2px; letter-spacing: 0.05em; }
</style>
</head>
<body>
<div class="layout">

<aside class="sidebar">
  <h1>Bad-faith ranking</h1>
  <div class="sub" style="font-size:11px; color:var(--muted); margin-bottom:10px;">51 jurisdictions · 11 factors · live re-rank</div>

  <h2>Weight presets</h2>
  <div>
    <button class="preset-btn active" data-preset="default">Default (v0.3)</button>
    <button class="preset-btn" data-preset="doctrine">Doctrine-only</button>
    <button class="preset-btn" data-preset="statutory">Statutory teeth</button>
    <button class="preset-btn" data-preset="access">Access / cost</button>
    <button class="preset-btn" data-preset="zero">Zero all</button>
  </div>

  <h2>Color by</h2>
  <div class="controls">
    <button class="color-btn active" data-color="tier">Score-band tier</button>
    <button class="color-btn" data-color="cluster">Structural cluster</button>
  </div>

  <h2>Factor weights <span style="font-weight:400;font-size:10px;color:var(--muted);" id="weight-sum">total: 100</span></h2>
  <div id="sliders"></div>

  <details style="margin-top:14px;">
    <summary>About this rubric</summary>
    <div class="meta-block">
      Each state is scored 0–10 on 11 factors. Weights default to v0.3 (sum 100). Weighted score = Σ(score × weight) / Σ(weight), normalized to 0–10. Factor 8 (pre-suit barriers) is scored inversely so higher = better for insureds. See <code>METHODOLOGY.md</code> in this folder for the full rubric and citations.
    </div>
  </details>
</aside>

<main class="main">
  <header class="title">
    <h1 id="rank-title">Default-weight ranking</h1>
    <div class="sub" id="rank-sub">Click any state row to see per-factor breakdown · Drag sliders to re-rank live</div>
  </header>

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

// --- presets (weight overrides) ---
const PRESETS = {
  default: Object.fromEntries(FACTORS.map(f => [f.id, f.default_weight])),
  // doctrine-only: zeroes f8/f9/f10, redistributes none (just lowers total)
  doctrine: Object.fromEntries(FACTORS.map(f => [f.id, f.category === 'doctrinal' ? f.default_weight : 0])),
  // statutory teeth: weights f2/f6/f7 heavily, downplays common-law factors
  statutory: { f1a_first_party_cause: 2, f1b_third_party_cause: 1, f2_statutory_proa: 25, f3_liability_standard: 4, f4_extracontractual_damages: 8, f5_punitive_damages: 4, f6_statutory_penalty: 22, f7_attorney_fees: 18, f8_pre_suit_barriers: 6, f9_admin_remedy: 5, f10_recent_appellate_trend: 5 },
  // access / cost: prioritize fee shifting, pre-suit barriers, admin remedy
  access: { f1a_first_party_cause: 6, f1b_third_party_cause: 3, f2_statutory_proa: 10, f3_liability_standard: 6, f4_extracontractual_damages: 8, f5_punitive_damages: 4, f6_statutory_penalty: 8, f7_attorney_fees: 22, f8_pre_suit_barriers: 14, f9_admin_remedy: 14, f10_recent_appellate_trend: 5 },
  zero: Object.fromEntries(FACTORS.map(f => [f.id, 0])),
};

let weights = {...PRESETS.default};
let colorMode = 'tier';
let selectedState = null;
let prevRanking = {};   // state -> rank, used for delta indicator

const sliders = document.getElementById('sliders');
const rankingBody = document.getElementById('ranking-body');
const weightSumEl = document.getElementById('weight-sum');
const clusterInfo = document.getElementById('cluster-info');

// --- build sliders, grouped by category ---
function buildSliders() {
  sliders.innerHTML = '';
  const cats = ['doctrinal','procedural','environment'];
  const catLabel = {doctrinal:'Doctrinal', procedural:'Procedural / Access', environment:'Environment'};
  cats.forEach(cat => {
    const header = document.createElement('div');
    header.className = 'factor-cat';
    header.textContent = catLabel[cat];
    sliders.appendChild(header);
    FACTORS.filter(f => f.category === cat).forEach(f => {
      const row = document.createElement('div');
      row.className = 'slider-row';
      const inv = f.inverse ? ' (inverse)' : '';
      row.innerHTML =
        '<div>' +
          '<span class="factor-label">' + f.label.replace(/ \\(inverse[^)]*\\)/, inv) + '</span>' +
          '<input type="range" min="0" max="30" step="1" value="' + weights[f.id] + '" data-fid="' + f.id + '">' +
        '</div>' +
        '<span class="weight-val' + (weights[f.id] === 0 ? ' zero' : '') + '" id="wv-' + f.id + '">' + weights[f.id] + '</span>';
      sliders.appendChild(row);
      row.querySelector('input').addEventListener('input', e => {
        weights[f.id] = parseInt(e.target.value, 10);
        const wv = document.getElementById('wv-' + f.id);
        wv.textContent = weights[f.id];
        wv.classList.toggle('zero', weights[f.id] === 0);
        rerank();
      });
    });
  });
}

// --- compute weighted score ---
function computeScore(state) {
  let num = 0, den = 0;
  FACTORS.forEach(f => {
    const w = weights[f.id] || 0;
    if (w === 0) return;
    num += state.scores[f.id].score * w;
    den += w;
  });
  return den > 0 ? num / den : 0;
}

// --- render ranking ---
function rerank() {
  const totalWeight = Object.values(weights).reduce((a,b) => a+b, 0);
  weightSumEl.textContent = 'total: ' + totalWeight;

  const ranked = DATA.states.map(s => ({...s, computed_score: computeScore(s)}));
  ranked.sort((a, b) => b.computed_score - a.computed_score);
  let curRank = 0, prevScore = null;
  ranked.forEach((s, i) => {
    if (s.computed_score !== prevScore) { curRank = i + 1; prevScore = s.computed_score; }
    s.rank = curRank;
  });

  // build rows
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

  // update prev ranking AFTER rendering
  prevRanking = Object.fromEntries(ranked.map(s => [s.state, s.rank]));

  if (selectedState) renderDetail(selectedState);
}

// --- render per-state detail panel ---
function selectState(code) {
  selectedState = code;
  document.querySelectorAll('table.ranking tr').forEach(tr => {
    tr.classList.toggle('active', tr.dataset.state === code);
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
    const fillPct = (fs.score / 10) * 100;
    html +=
      '<div class="factor-row">' +
        '<div>' +
          '<div class="lbl"><b>' + f.label + '</b> · weight ' + w + '</div>' +
          '<div class="factor-bar"><div class="fill" style="width:' + fillPct + '%"></div></div>' +
        '</div>' +
        '<div class="num">' + fs.score + '</div>' +
      '</div>' +
      '<div class="factor-detail">' + escapeHtml(fs.rationale) +
        (fs.cite ? '<div class="cite">' + escapeHtml(fs.cite) + '</div>' : '') +
      '</div>';
  });
  document.getElementById('detail-body').innerHTML = html;
}

function escapeHtml(s) { return String(s||'').replace(/[&<>"]/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c])); }

// --- preset buttons ---
document.querySelectorAll('.preset-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.preset-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    weights = {...PRESETS[btn.dataset.preset]};
    buildSliders();
    rerank();
  });
});

// --- color-mode buttons ---
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
  });
});

// init
buildSliders();
document.querySelector('.color-btn.active').click();   // populate cluster-info
rerank();
selectState(DATA.states[0].state);   // pick first ranked state
</script>
</body>
</html>
"""

html = HTML.replace("__FACTORS_JSON__", json.dumps(factors))
html = html.replace("__DATA_JSON__", json.dumps(states))
OUT.write_text(html)
print(f"wrote {OUT} ({len(html):,} bytes)")
