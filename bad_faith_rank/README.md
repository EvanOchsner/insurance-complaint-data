# bad_faith_rank — State Bad-Faith Protection Ranking

Composite ranking of all 50 U.S. states + DC by the strength of their insurance bad-faith protections from an insured individual's perspective. Synthesized from the UPH/Feinman *50-State Survey of Bad Faith Laws and Remedies* (Jan. 2025), NAIC MC-55, IADC and Wilson Elser 50-state surveys, the Chartwell Law map, and verified state statutes.

The ranking is **explicitly weight-tunable**: 11 enumerated factors, each scored 0–10 per state, combined as a weighted average. The interactive viewer lets a user re-tune any weight live and see the ranking update.

## Quick start

```
python3 -m http.server 8767 --directory bad_faith_rank
open http://localhost:8767
```

Or, in this repo's harness, the dev server is already configured: open `index.html` directly in a browser, or run via the `bad_faith_rank` launch config.

## What's in this folder

| File | What |
|---|---|
| [`index.html`](index.html) | **Interactive viewer.** Single-file HTML. Three-panel layout: weight sliders + presets + color-mode toggle (left); ranking table with tier and structural-cluster pills (center); per-state factor breakdown with rationales and citations (right). All data embedded — no network or build step. |
| [`METHODOLOGY.md`](METHODOLOGY.md) | Full rubric: 11 factors, anchored scoring rules, default weights and rationale, source list, score-band tier definitions, structural cluster definitions, limitations. |
| [`data/states_factor_scores.json`](data/states_factor_scores.json) | Per-state per-factor scores with rationales and citations. **The primary data artifact** — re-usable in other tools. |
| [`data/factors.json`](data/factors.json) | Factor metadata: id, label, default weight, category. |
| [`data/states_with_clusters.json`](data/states_with_clusters.json) | Enriched per-state data with computed default score, tier, and structural cluster. Embedded into `index.html`. |
| [`data/states_ranked_default.csv`](data/states_ranked_default.csv) | Default-weight ranking as CSV (rank, state, name, score, all 11 factor scores). |
| [`scripts/build_ranking.py`](scripts/build_ranking.py) | Merge per-batch scoring JSON into unified per-state scores; compute default-weight ranking. |
| [`scripts/build_clusters.py`](scripts/build_clusters.py) | Assign score-band tiers and structural clusters from factor profiles. |
| [`scripts/build_viewer.py`](scripts/build_viewer.py) | Inject data into HTML template; produce single-file `index.html`. |

Source extracts and intermediate working files are in [`.tmp/bad_faith_ranking/`](../.tmp/bad_faith_ranking/) (frameworks review, penalty/admin reference table, rubric draft, per-batch scoring JSON, the local Feinman 2025 PDF and its extracted text).

## Default ranking (top to bottom)

| Rank | State | Score | Tier | Structural cluster |
|---:|---|---:|---|---|
| 1 | WA Washington | 7.96 | T1 | Multi-Tool Statutory |
| 2 | PA Pennsylvania | 7.78 | T1 | Multi-Tool Statutory |
| 3 | MA Massachusetts | 7.60 | T1 | Multi-Tool Statutory |
| 4 | CO Colorado | 7.34 | T1 | Multi-Tool Statutory |
| 5 | NM New Mexico | 7.16 | T1 | Multi-Tool Statutory |
| 6 | TX Texas | 7.12 | T1 | Multi-Tool Statutory |
| 7 | MT Montana | 6.32 | T2 | Statute-Constrained |
| 7 | RI Rhode Island | 6.32 | T2 | Statute-Constrained |
| 9 | KY Kentucky | 6.18 | T2 | Statute-Constrained |
| 10 | CA California | 5.82 | T3 | Common-Law Tort |
| 10 | MO Missouri | 5.82 | T3 | Statute-Constrained |
| 12 | NV Nevada | 5.80 | T3 | Statute-Constrained |
| 13 | NC North Carolina | 5.58 | T3 | Statute-Constrained |
| 14 | CT Connecticut | 5.56 | T3 | Statute-Constrained |
| 15 | WI Wisconsin | 5.52 | T3 | Common-Law Tort |
| 16 | SC South Carolina | 5.44 | T3 | Common-Law Tort |
| 17 | NJ New Jersey | 5.28 | T3 | Statute-Constrained |
| 18 | TN Tennessee | 5.26 | T3 | Statute-Constrained |
| 19 | FL Florida | 5.24 | T3 | Statute-Constrained |
| 20 | AK Alaska | 5.20 | T3 | Common-Law Tort |
| 21 | WV West Virginia | 5.18 | T3 | Statute-Constrained |
| 22 | LA Louisiana | 5.14 | T3 | Statute-Constrained |
| 23 | MD Maryland | 5.06 | T3 | **Mandatory Admin-Channel Hybrid** |
| 24 | HI Hawaii | 5.04 | T3 | Common-Law Tort |
| 25 | AZ Arizona | 4.92 | T4 | Common-Law Tort |
| 26 | GA Georgia | 4.88 | T4 | Statute-Constrained |
| 27 | ID Idaho | 4.86 | T4 | Common-Law Tort |
| 28 | OK Oklahoma | 4.84 | T4 | Common-Law Tort |
| 29 | IL Illinois | 4.82 | T4 | Statute-Constrained |
| 30 | IA Iowa | 4.76 | T4 | Common-Law Tort |
| 30 | ND North Dakota | 4.76 | T4 | Common-Law Tort |
| 32 | AR Arkansas | 4.74 | T4 | Statute-Constrained |
| 33 | SD South Dakota | 4.66 | T4 | Common-Law Tort |
| 34 | ME Maine | 4.54 | T4 | Statute-Constrained |
| 35 | DE Delaware | 4.52 | T4 | Common-Law Tort |
| 36 | VT Vermont | 4.44 | T4 | Common-Law Tort |
| 36 | WY Wyoming | 4.44 | T4 | Common-Law Tort |
| 38 | OH Ohio | 4.40 | T4 | Common-Law Tort |
| 39 | KS Kansas | 4.30 | T4 | Minimal Protection |
| 40 | MN Minnesota | 4.20 | T4 | Statute-Constrained |
| 41 | OR Oregon | 4.14 | T4 | Common-Law Tort |
| 42 | NE Nebraska | 3.98 | T5 | Common-Law Tort |
| 43 | IN Indiana | 3.96 | T5 | Common-Law Tort |
| 44 | UT Utah | 3.86 | T5 | Minimal Protection |
| 45 | VA Virginia | 3.82 | T5 | Minimal Protection |
| 46 | AL Alabama | 3.52 | T5 | Common-Law Tort |
| 47 | MS Mississippi | 3.48 | T5 | Common-Law Tort |
| 48 | NH New Hampshire | 3.38 | T5 | Minimal Protection |
| 49 | NY New York | 3.22 | T5 | Minimal Protection |
| 50 | MI Michigan | 3.14 | T5 | Minimal Protection |
| 51 | DC District of Columbia | 2.24 | T5 | Minimal Protection |

## How the ranking changes with weights

The interactive viewer ships with four weight presets that produce notably different rankings, illustrating the rubric's sensitivity to choice of weights:

| Preset | Reweighting | Effect on top of ranking |
|---|---|---|
| **Default (v0.3)** | Doctrinal-heavy; balanced statutory + common-law | WA, PA, MA, CO, NM, TX |
| **Doctrine-only** | F8/F9/F10 zeroed | WA (8.71), MA (8.42), PA (8.13), TX (7.71), NM (7.53) |
| **Statutory teeth** | F2 → 25, F6 → 22, F7 → 18; common-law factors down-weighted | WA & MA tied (8.63), PA (8.42), TX (7.79), NM (7.57); CA falls sharply |
| **Access / cost** | F7 → 22, F8 → 14, F9 → 14 (fee shifting + barriers + admin remedy) | WA (8.10), PA (7.97), MA (7.54), CO (7.38), NM (7.21) |

Drag any individual slider to test the contribution of a single factor.

## Five clusters at a glance

| Cluster | n | Examples | What you'd expect to see in repo data |
|---|---:|---|---|
| **S0 Mandatory Admin-Channel Hybrid** | 1 | MD | Strong DOI disposition data (MIA §27-1001 reports already in `md_mia/`); fewer first-party court filings |
| **S1 Multi-Tool Statutory Regime** | 6 | WA, PA, MA, CO, NM, TX | High statutory-notice volume (FL CRN-style mechanism in `fl_crn/`, WA IFCA in `wa_oic/`); high civil-filing volume |
| **S2 Statutory Path, Constrained** | 17 | RI, KY, MO, NV, NC, CT, NJ, TN, FL, GA, WV, LA, IL, MT, ME, AR, MN | Visible pre-suit demand activity; capped damages hold case values down |
| **S3 Common-Law Tort Driven** | 20 | CA, AZ, AK, OK, HI, ID, IA, ND, SD, OH, WI, SC, OR, VT, WY, DE, NE, IN, AL, MS | Concentrated higher-stakes filings; admin complaint volume the dominant signal |
| **S4 Minimal Protection** | 7 | KS, UT, VA, NH, NY, MI, DC | Low bad-faith filing volume; admin complaints are the only visible footprint |

## Limitations

- Source dependence on Feinman 2025; recent statutory changes (FL SB 2A 2022, LA Act 3 2024) reflected, but legislative tracking needs ongoing maintenance.
- Scope: P&C, individual insureds. Health/life/WC excluded.
- Per-factor scores are integers 0–10; ties at the weighted average are real.
- See [`METHODOLOGY.md`](METHODOLOGY.md) for the full discussion.

## Sources (top-level)

- [UPH/Feinman 50-State Survey 2025](https://uphelp.org/wp-content/uploads/2025/03/2025-National-Bad-Faith-Survey.pdf)
- [NAIC Model Law Chart MC-55](https://content.naic.org/sites/default/files/model-law-chart-mc-55-private-rights-of-action-for-unfair-claims-settlement-practices.pdf)
- [IADC 50-State Insurance and Bad Faith Quick Reference](https://www.iadclaw.org/assets/1/7/50_State_Insurance_Bad_Faith_Reference_Guide.pdf)
- [Wilson Elser Punitive Damages Review 2023](https://ecoms.wilsonelser.com/hubfs/Wilson%20Elser%2050-State%20Survey%20Punitive%20Damages%202023-2.pdf)
- [Chartwell Law Bad Faith Claims Map](https://www.chartwelllaw.com/bad-faith-claims-map/)

Per-state statute and case citations are embedded in [`data/states_factor_scores.json`](data/states_factor_scores.json) per-factor.
