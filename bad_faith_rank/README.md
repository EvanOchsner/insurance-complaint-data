# bad_faith_rank — State Bad Faith Protection Rankings

Composite ranking of all 50 U.S. states + DC by the strength of their insurance bad faith protections from an insured individual's perspective. Synthesized from the UPH/Feinman *50-State Survey of Bad Faith Laws and Remedies* (Jan. 2025), NAIC MC-55, IADC and Wilson Elser 50-state surveys, the Chartwell Law map, and verified state statutes.

> ⚠️ **Not authoritative.** The default weighting is a SWAG (scientific wild-ass guess), not a settled finding. The rubric is an explicitly weight-tunable framework: each factor is scored 0–10 along named levels, combined as a weighted average. The interactive viewer lets researchers and advocates re-weight any factor live, edit individual level values, and copy their tuning as JSON to share or reload. v0.4 introduced float weights in [0,1] and per-factor named levels with editable values.

## Quick start

```
python3 -m http.server 8767 --directory bad_faith_rank
open http://localhost:8767
```

Or, in this repo's harness, the dev server is already configured: open `index.html` directly in a browser, or run via the `bad_faith_rank` launch config.

## What's in this folder

| File | What |
|---|---|
| [`index.html`](index.html) | **Interactive viewer.** Single-file HTML. Three-panel layout: weight sliders + presets + per-factor level editors + tuning copy/load (left); ranking table with tier and structural-cluster pills (center); per-state factor breakdown with rationales and citations (right). All data embedded — no network or build step. |
| [`METHODOLOGY.md`](METHODOLOGY.md) | Full rubric: factor list, anchored scoring rules, level definitions, default weights, source list, score-band tier definitions, structural cluster definitions, limitations. |
| [`data/states_factor_scores.json`](data/states_factor_scores.json) | Per-state per-factor scores with level indices, rationales, and citations. **The primary data artifact** — re-usable in other tools. |
| [`data/factors.json`](data/factors.json) | Factor metadata: id, label, default float weight in [0,1], category, levels (with name, value, explainer). |
| [`data/states_with_clusters.json`](data/states_with_clusters.json) | Enriched per-state data with computed default score, tier, and structural cluster. Embedded into `index.html`. |
| [`data/states_ranked_default.csv`](data/states_ranked_default.csv) | Default-weight ranking as CSV (rank, state, name, score, level-bucketed value per factor). |
| [`scripts/build_ranking.py`](scripts/build_ranking.py) | Merge per-batch scoring JSON into unified per-state scores; compute default-weight ranking. |
| [`scripts/build_clusters.py`](scripts/build_clusters.py) | Assign score-band tiers and structural clusters from factor profiles. |
| [`scripts/build_viewer.py`](scripts/build_viewer.py) | Inject data into HTML template; produce single-file `index.html`. |

Source extracts and intermediate working files are in [`.tmp/bad_faith_ranking/`](../.tmp/bad_faith_ranking/) (frameworks review, penalty/admin reference table, rubric draft, per-batch scoring JSON, the local Feinman 2025 PDF and its extracted text).

## Default ranking (top to bottom)

| Rank | State | Score | Tier | Structural cluster |
|---:|---|---:|---|---|
| 1 | WA Washington | 8.37 | T1 | Multi-Tool Statutory Regime |
| 2 | MA Massachusetts | 7.87 | T1 | Multi-Tool Statutory Regime |
| 3 | PA Pennsylvania | 7.77 | T1 | Multi-Tool Statutory Regime |
| 4 | TX Texas | 7.62 | T1 | Multi-Tool Statutory Regime |
| 5 | NM New Mexico | 7.42 | T1 | Multi-Tool Statutory Regime |
| 6 | CO Colorado | 7.37 | T1 | Multi-Tool Statutory Regime |
| 7 | MT Montana | 7.05 | T1 | Statutory Path, Constrained |
| 8 | RI Rhode Island | 6.87 | T2 | Statutory Path, Constrained |
| 9 | KY Kentucky | 6.57 | T2 | Statutory Path, Constrained |
| 10 | MO Missouri | 6.32 | T2 | Statutory Path, Constrained |
| 11 | WV West Virginia | 6.18 | T2 | Statutory Path, Constrained |
| 12 | CT Connecticut | 6.10 | T2 | Statutory Path, Constrained |
| 13 | NV Nevada | 6.07 | T2 | Statutory Path, Constrained |
| 14 | CA California | 5.90 | T3 | Common-Law Tort Driven |
| 15 | NC North Carolina | 5.80 | T3 | Statutory Path, Constrained |
| 16 | LA Louisiana | 5.62 | T3 | Statutory Path, Constrained |
| 16 | WI Wisconsin | 5.62 | T3 | Common-Law Tort Driven |
| 18 | TN Tennessee | 5.60 | T3 | Statutory Path, Constrained |
| 19 | SC South Carolina | 5.42 | T3 | Statutory Path, Constrained |
| 20 | GA Georgia | 5.35 | T3 | Statutory Path, Constrained |
| 21 | ID Idaho | 5.32 | T3 | Common-Law Tort Driven |
| 22 | AK Alaska | 5.27 | T3 | Common-Law Tort Driven |
| 22 | HI Hawaii | 5.27 | T3 | Common-Law Tort Driven |
| 22 | IA Iowa | 5.27 | T3 | Common-Law Tort Driven |
| 25 | AZ Arizona | 5.22 | T3 | Common-Law Tort Driven |
| 26 | FL Florida | 5.15 | T3 | Statutory Path, Constrained |
| 26 | MD Maryland | 5.15 | T3 | **Mandatory Admin-Channel Hybrid** |
| 28 | AR Arkansas | 5.13 | T3 | Statutory Path, Constrained |
| 29 | OH Ohio | 4.97 | T4 | Common-Law Tort Driven |
| 29 | OK Oklahoma | 4.97 | T4 | Common-Law Tort Driven |
| 31 | ND North Dakota | 4.95 | T4 | Common-Law Tort Driven |
| 32 | IL Illinois | 4.90 | T4 | Statutory Path, Constrained |
| 32 | NJ New Jersey | 4.90 | T4 | Statutory Path, Constrained |
| 34 | DE Delaware | 4.77 | T4 | Common-Law Tort Driven |
| 35 | VT Vermont | 4.72 | T4 | Common-Law Tort Driven |
| 36 | SD South Dakota | 4.70 | T4 | Common-Law Tort Driven |
| 37 | KS Kansas | 4.60 | T4 | Minimal Protection |
| 38 | ME Maine | 4.57 | T4 | Statutory Path, Constrained |
| 39 | WY Wyoming | 4.50 | T4 | Common-Law Tort Driven |
| 40 | MN Minnesota | 4.45 | T4 | Statutory Path, Constrained |
| 41 | IN Indiana | 4.32 | T4 | Common-Law Tort Driven |
| 42 | UT Utah | 4.00 | T4 | Minimal Protection |
| 43 | VA Virginia | 3.92 | T5 | Minimal Protection |
| 44 | OR Oregon | 3.88 | T5 | Common-Law Tort Driven |
| 45 | NE Nebraska | 3.87 | T5 | Common-Law Tort Driven |
| 46 | NH New Hampshire | 3.83 | T5 | Minimal Protection |
| 47 | AL Alabama | 3.73 | T5 | Common-Law Tort Driven |
| 48 | MS Mississippi | 3.67 | T5 | Common-Law Tort Driven |
| 49 | MI Michigan | 3.27 | T5 | Minimal Protection |
| 50 | NY New York | 3.23 | T5 | Minimal Protection |
| 51 | DC District of Columbia | 2.32 | T5 | Minimal Protection |

## How the ranking changes with weights

The interactive viewer ships with six presets, each with a brief explainer in the sidebar:

| Preset | What it emphasizes |
|---|---|
| **Default** | Doctrinal-heavy; balanced statutory + common-law. SWAG starting point. |
| **Doctrine-only** | Procedural and environment factors zeroed; ranks states purely on substantive doctrine. |
| **Statutory teeth** | Up-weights statutory PRoA, statutory penalty/multiplier, attorney-fee shifting. Surfaces sharp codified-remedy regimes. |
| **Access / cost** | Up-weights fee shifting, low pre-suit barriers, administrative-remedy strength. Surfaces states where a real claimant can actually reach a remedy. |
| **Uniform** | Every factor weighted equally — sanity check against any preset's emphasis. |
| **Custom** | Tune freely. Sliders + per-factor level-value editors. Copy/paste tuning JSON to save and share. |

Click any factor in the weights list to expand its named levels and edit individual level values. Drag any slider to retune weights. Use **Copy tuning** to save your weighting and level overrides as JSON, and **Load tuning** to paste a saved JSON back in.

## Five clusters at a glance

| Cluster | n | Examples | What you'd expect to see in repo data |
|---|---:|---|---|
| **S0 Mandatory Admin-Channel Hybrid** | 1 | MD | Strong DOI disposition data (MIA §27-1001 reports already in `md_mia/`); fewer first-party court filings |
| **S1 Multi-Tool Statutory Regime** | 6 | WA, PA, MA, CO, NM, TX | High statutory-notice volume (FL CRN-style mechanism in `fl_crn/`, WA IFCA in `wa_oic/`); high civil-filing volume |
| **S2 Statutory Path, Constrained** | 17 | RI, KY, MO, NV, NC, CT, NJ, TN, FL, GA, WV, LA, IL, MT, ME, AR, MN | Visible pre-suit demand activity; capped damages hold case values down |
| **S3 Common-Law Tort Driven** | 20 | CA, AZ, AK, OK, HI, ID, IA, ND, SD, OH, WI, SC, OR, VT, WY, DE, NE, IN, AL, MS | Concentrated higher-stakes filings; admin complaint volume the dominant signal |
| **S4 Minimal Protection** | 7 | KS, UT, VA, NH, NY, MI, DC | Low bad-faith filing volume; admin complaints are the only visible footprint |

## Limitations

- **Not authoritative.** The default weighting is a SWAG. The whole point of the viewer is that *you* should retune it.
- Source dependence on Feinman 2025; recent statutory changes (FL SB 2A 2022, LA Act 3 2024) reflected, but legislative tracking needs ongoing maintenance.
- Scope: P&C, individual insureds. Health/life/WC excluded.
- Per-factor scores are bucketed to a small number of named levels (3–5 per factor) with uniform spacing on 0–10; ties at the weighted average are real and expected.
- See [`METHODOLOGY.md`](METHODOLOGY.md) for the full discussion.

## Sources (top-level)

- [UPH/Feinman 50-State Survey 2025](https://uphelp.org/wp-content/uploads/2025/03/2025-National-Bad-Faith-Survey.pdf)
- [NAIC Model Law Chart MC-55](https://content.naic.org/sites/default/files/model-law-chart-mc-55-private-rights-of-action-for-unfair-claims-settlement-practices.pdf)
- [IADC 50-State Insurance and Bad Faith Quick Reference](https://www.iadclaw.org/assets/1/7/50_State_Insurance_Bad_Faith_Reference_Guide.pdf)
- [Wilson Elser Punitive Damages Review 2023](https://ecoms.wilsonelser.com/hubfs/Wilson%20Elser%2050-State%20Survey%20Punitive%20Damages%202023-2.pdf)
- [Chartwell Law Bad Faith Claims Map](https://www.chartwelllaw.com/bad-faith-claims-map/)

Per-state statute and case citations are embedded in [`data/states_factor_scores.json`](data/states_factor_scores.json) per-factor.
