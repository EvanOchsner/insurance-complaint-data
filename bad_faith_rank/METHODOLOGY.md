# Bad Faith Protection Ranking — Methodology

**Version 0.4** · 2026-05-06 · 51 jurisdictions (50 states + DC)

> ⚠️ **Not an authoritative ranking.** The default weighting is a SWAG, not a settled scientific finding.
> The viewer is a tool for researchers and advocates to re-weight factors and adjust per-factor level values
> to reach their own conclusions, then copy and share the resulting tuning. v0.4 introduces named per-factor
> *levels* (with editable values) and float weights in [0,1].

## Scope

This ranking measures the strength of state-level **bad faith protections from the perspective of an insured individual**. Specifically:

- **First-party** bad-faith claims (insured vs. own insurer over the insured's own loss).
- **Third-party / duty-to-settle** claims (the insured's *liability* insurer fails to settle within policy limits, exposing its own insured to an excess judgment — *Stowers* / *Crisci* doctrine).

**Out of scope:**
- Direct actions by injured strangers against the tortfeasor's insurer (rare / sui generis).
- Large-commercial bad-faith doctrines (different judicial treatment).
- Workers' compensation bad faith (barred by exclusivity in most states).
- Health-line and life-line bad faith (some states have distinct regimes — e.g., CA DMHC, NY DFS health rules — that this ranking does not capture).

The ranking centers on **personal-line P&C** (auto, homeowners, commercial property for individuals).

## Why no off-the-shelf ranking is used

Existing frameworks describe but do not rank:

- **UPH/Feinman, "50 State Survey of Bad Faith Laws and Remedies" (Jan. 2025)** — the leading descriptive reference, narrative per state, no scores. ([uphelp.org](https://uphelp.org/claim-guidance-publications/50-state-bad-faith-survey/))
- **NAIC Model Law Chart MC-55** — categorical (PRoA yes/no) per state, no composite. ([naic.org](https://content.naic.org/sites/default/files/model-law-chart-mc-55-private-rights-of-action-for-unfair-claims-settlement-practices.pdf))
- **IADC 50-State Insurance and Bad Faith Quick Reference** (defense-side, descriptive). ([iadclaw.org](https://www.iadclaw.org/assets/1/7/50_State_Insurance_Bad_Faith_Reference_Guide.pdf))
- **Wilson Elser Punitive Damages 50-State Survey (2023)** (descriptive). ([ecoms.wilsonelser.com](https://ecoms.wilsonelser.com/hubfs/Wilson%20Elser%2050-State%20Survey%20Punitive%20Damages%202023-2.pdf))
- **Chartwell Law Bad Faith Claims Map** (per-state interactive, descriptive). ([chartwelllaw.com](https://www.chartwelllaw.com/bad-faith-claims-map))
- **Stephen Ashley, *Bad Faith Actions: Liability and Damages*** (treatise; paywalled).
- **Mealey's Litigation Report: Insurance Bad Faith** (case-tracking; paywalled).

Industry-side and academic rankings exist but are oblique to bad-faith specifically: ATRA Judicial Hellholes (tort-reform-aligned, conflates non-insurance torts), R Street Insurance Regulation Report Card (regulation broadly, not bad-faith), CFA Auto Insurance Regulation: What Works (rate regulation, not bad-faith).

This rubric **synthesizes** the descriptive sources above into 11 factor scores per jurisdiction.

See `.tmp/bad_faith_ranking/01_existing_frameworks.md` for the complete review of available frameworks.

## Rubric

Each factor is scored **0–10** for each state with anchored scoring rules. **Higher = more protective of the insured.** Default weights sum to 100; the interactive viewer (`index.html`) lets users re-tune any weight live. Weighted score = Σ(score × weight) / Σ(weight), normalized to 0–10 regardless of weight choice.

### Doctrinal factors (74 of 100 default weight)

| # | Factor | Weight | What it measures |
|---|---|---:|---|
| 1a | First-party cause of action | 8 | Common-law tort and/or statutory cause of action by an insured against own insurer over insured's own loss |
| 1b | Third-party / duty-to-settle | 4 | *Stowers*-line / *Crisci*-line cause of action against liability insurer for failure to settle within limits |
| 2 | Statutory PRoA | 14 | Statutory private right of action under UCSPA-equivalent / dedicated bad-faith statute. Scored higher when the statute reaches both first- and third-party scenarios |
| 3 | Liability standard | 8 | Plaintiff's burden — "actual malice" hardest, "no reasonable basis" easier |
| 4 | Extra-contractual damages | 12 | Consequential, emotional-distress, and above-policy-limit damages; full excess judgment in third-party context |
| 5 | Punitive damages | 8 | Availability and standard (preponderance vs. clear-and-convincing); cap structure |
| 6 | Statutory penalty / multiplier | 12 | Built-in statutory teeth: interest premium, multiplier, percent penalty (e.g., WA IFCA treble, PA §8371 prime+3% + punitive, CO 2x, GA 50%, TN 25%, NM treble via UPA, IL §155 capped, MA c. 93A 2x/3x) |
| 7 | Attorney-fee shifting | 10 | One-way fee shift to prevailing insured |

### Procedural / access factors (14 of 100 default weight)

| # | Factor | Weight | What it measures |
|---|---|---:|---|
| 8 | Pre-suit barriers | 6 | Notice, demand, cure-period, exhaustion requirements that gate filing. (Convention is uniform across factors: 10 = strongest consumer protection. F8 levels go from "heavy mandatory exhaustion + cure" at 0 to "no pre-suit barrier" at 10.) |
| 9 | Administrative remedy strength | 8 | Whether the state DOI investigates individual claim disputes with substantive findings, has fining authority, and (rarely) provides a structured pre-suit/parallel quasi-adjudication channel |

### Environment factor (10 of 100 default weight)

| # | Factor | Weight | What it measures |
|---|---|---:|---|
| 10 | Recent appellate trend | 10 | Direction of change in last ~10 years — sustained narrowing (FL SB 2A 2022, LA Act 3 2024, WA *Perez-Crisantos* 2017, TX HB 1774 2017, MD/Wisconsin steady) vs. broadening |

**Total default weight: 100.**

### Removed in v0.3 — Factor 11 "Inverse-industry signal"

An earlier draft included an "inverse-industry signal" factor pulling ATRA Judicial Hellholes presence and R Street Insurance Regulation grades. **Removed** because:

1. ATRA Hellholes is not bad-faith-specific — it conflates asbestos venues, class-action treatment, jury verdicts in unrelated torts.
2. R Street grades regulation broadly (solvency, rate-filing) where bad-faith doctrine is not a meaningful input.
3. Circularity risk with Factors 2, 6, 7 — strong statutory remedies are themselves a reason a state lands on Hellholes.
4. Source is ideologically loaded.

Its 8 weight points were redistributed: +2 each to F2 (statutory PRoA), F4 (extracontractual damages), F6 (statutory penalty), F10 (recent appellate trend).

## Scoring rules

Each factor uses a 5-anchor scale (0, 3, 5, 7, 10) with intermediate values 1, 2, 4, 6, 8, 9 reserved for nuance. The full anchored rules are in `.tmp/bad_faith_ranking/04_rubric_DRAFT.md`. Examples:

**F1a (First-party cause of action):** 0 = none recognized · 3 = narrow / statute-only without PRoA (NY *Bi-Economy* limited; IL §155 only) · 5 = tort recognized but with significant doctrinal limits · 7 = tort well-established, broadly available · 10 = tort firmly established with broad damages and lenient standard (CA *Gruenberg*/*Egan*, MT, AZ *Noble*).

**F2 (Statutory PRoA):** 0 = no statutory PRoA, statute regulatory-only (CA post-*Moradi-Shalal*, OR, MN) · 3 = limited PRoA tied to specific narrow conduct, OR reaches only first- or third-party · 5 = PRoA reaches both, arduous procedural hurdles · 7 = broadly available across both, modest hurdles (FL §624.155 with 60-day CRN cure) · 10 = broadly available, low hurdles, mandatory remedies (WA IFCA, TX Ch. 541/542).

**F6 (Statutory penalty/multiplier):** 0 = none · 3 = modest interest premium · 5 = significant interest (12%+) or modest percent penalty · 7 = multiplier ≥ 1.5x or large percent penalty (GA §33-4-6 50%, TN §56-7-105 25%, NM §59A-16-30 treble via UPA) · 10 = treble (WA IFCA), or 2–3x with low procedural friction.

**F8 (Pre-suit barriers):** 0 = mandatory long-cure + dual exhaustion + strict notice · 3 = mandatory cure period (30–60 days) with narrow notice · 5 = pre-suit notice required, modest cure · 7 = light notice, no cure · 10 = no pre-suit barrier. (Same convention as every other factor: 10 = strongest consumer protection.)

### v0.4 — Per-factor levels with editable values

Each factor declares a small number of named levels (3–5) uniformly spaced on the 0–10 range. Each level has a name and a 1-sentence explainer. Per-state scores are snapped to the nearest level at build time; the viewer ranks states using the level value rather than the raw score. This achieves three goals:

1. **Consistency across factors.** Spacing is uniform within each factor, so a "level 1 of 4" carries the same numeric weight regardless of factor.
2. **Auditability.** Users can see exactly which states sit at each level, with named labels and explainers, instead of trying to interpret bare integers.
3. **Tunability.** The viewer lets users edit any level's numeric value; rankings update live for every state at that level.

Re-bucketing was a pure rounding step: each per-state raw score is replaced by its nearest level value. Most movement is small. The default ranking under v0.4 is in [`data/states_ranked_default.csv`](data/states_ranked_default.csv).

## Sources of per-state scores

Each per-factor score in [`data/states_factor_scores.json`](data/states_factor_scores.json) carries:

- An integer score 0–10
- A 1–2 sentence rationale
- A portable citation (statute, case, or specific Feinman page)

Scoring synthesized from:

1. **UPH/Feinman 50-State Survey 2025** — narrative per-state coverage of statute adoption, common-law cause of action, damages, attorney's fees, statutory penalties, recent developments. Used as descriptive anchor for all 51 jurisdictions. PDF SHA-256: `d918589eab1c5d1cb5dec81ea9d599ce700012ffa100e3f0ec5d035e460ca9cb`.
2. **NAIC MC-55** — categorical PRoA presence/absence.
3. **IADC 50-State Quick Reference Guide** — defense-side cross-check.
4. **Wilson Elser Punitive Damages 50-State Survey (2023)** — punitive damages and cap structure.
5. **Chartwell Law Bad Faith Claims Map** — descriptive cross-check.
6. **Specific state statutes and cases** — verified via Justia, FindLaw, state legislature sites.

The per-state penalty / admin reference table at [`.tmp/bad_faith_ranking/03_penalty_admin_data.md`](../.tmp/bad_faith_ranking/03_penalty_admin_data.md) was independently constructed and reconciled with Feinman where they diverged.

## Default ranking (full)

The default ranking under v0.3 default weights is in [`data/states_ranked_default.csv`](data/states_ranked_default.csv) and is reproduced at the end of this document. The interactive viewer (`index.html`) lets users explore alternative weightings live.

## Cluster definitions

Two cluster typologies are produced.

### Score-band tiers (weight-dependent — change live with sliders)

| Tier | Range | Description |
|---|---|---|
| **T1 — Strongest** | ≥ 7.0 | States with statutory multi-tools, fee shifting, broad damages, robust admin, no recent narrowing |
| **T2 — Strong** | 6.0–6.99 | States with most multi-tool elements but missing one or two |
| **T3 — Moderate** | 5.0–5.99 | Mixed regimes — strong on one axis, weak on others |
| **T4 — Weak** | 4.0–4.99 | Limited statutory remedies; common-law tort may exist but rarely litigated |
| **T5 — Weakest** | < 4.0 | No first-party tort + no PRoA + minimal damages; insureds limited to contract remedies |

Band cut-points were chosen from natural breaks in the default-score distribution (median 4.88, range 2.24–7.96). Tier bands recompute live as the user retunes weights.

### Structural clusters (weight-independent — fixed regardless of slider position)

These reflect the **factor profile** (which protections exist), not the score. They capture *likely causal drivers* of differences in observable bad-faith activity (regulator complaints, civil filings, statutory notices like FL CRNs and WA IFCA notices).

| Cluster | Members (default-score) | Description | Drivers of observable activity |
|---|---|---|---|
| **S0 — Mandatory Admin-Channel Hybrid** | MD (5.06) | Statute requires a pre-suit administrative complaint to the state DOI. DOI findings carry weight. | Bad-faith disputes channel through the regulator first; DOI dispositions are the primary signal; court filings filtered. Maryland's MIA §27-1001 publishes annual disposition data. |
| **S1 — Multi-Tool Statutory Regime** | WA (7.96), PA (7.78), MA (7.60), CO (7.34), NM (7.16), TX (7.12) | Robust statutory PRoA + statutory penalty + one-way fees. Insureds litigate without relying on common-law tort. | Statutory teeth predict higher litigation volume and more pre-suit settlement. CRN/demand mechanisms generate large public databases of plaintiff allegations (FL CRN, WA IFCA notices, MA c. 93A demands). |
| **S2 — Statutory Path, Constrained** | MT (6.32), RI (6.32), KY (6.18), MO (5.82), NV (5.80), NC (5.58), CT (5.56), NJ (5.28), TN (5.26), FL (5.24), WV (5.18), LA (5.14), GA (4.88), IL (4.82), AR (4.74), ME (4.54), MN (4.20) | Statutory path exists but is narrower — capped damages (IL §155, VA §38.2-209), strict construction (TN §56-7-105), narrow scope (RI §9-1-33 first-party only), demand-letter prerequisites that gate filing. | Procedural prerequisites generate visible plaintiff-side activity (e.g., FL CRN database); statutory caps hold settlement values down. |
| **S3 — Common-Law Tort Driven** | CA (5.82), WI (5.52), SC (5.44), AK (5.20), HI (5.04), AZ (4.92), ID (4.86), OK (4.84), IA (4.76), ND (4.76), SD (4.66), DE (4.52), VT (4.44), WY (4.44), OH (4.40), OR (4.14), NE (3.98), IN (3.96), AL (3.52), MS (3.48) | Recognized common-law tort cause of action; no meaningful statutory PRoA. Damages and standards depend on judicial doctrine. | Litigation concentrated in larger-loss cases where contingency-fee economics work; lower-volume case-by-case footprint; admin complaint volume is the more visible signal. |
| **S4 — Minimal Protection** | KS (4.30), UT (3.86), VA (3.82), NH (3.38), NY (3.22), MI (3.14), DC (2.24) | No robust common-law tort AND no meaningful statutory PRoA. | Bad-faith litigation rare; admin complaint volume is the dominant footprint; insurer behavior constrained more by reputation/market than law. |

### Why two typologies?

A state's **score-band tier** answers "how protective is this state in aggregate, under my weights?" A state's **structural cluster** answers "what *kind* of protection regime is this, and what type of bad-faith footprint should I expect to see in regulator and court data?" Two states in the same structural cluster (e.g., FL and IL both in S2) can have different scores but produce similar *types* of observable activity — e.g., visible pre-suit demand databases. Two states in the same score-band but different structural cluster (e.g., CA and FL both around 5.2-5.8) achieve similar protection through different mechanisms — and would produce different data footprints in this repo's downstream datasets.

## Limitations

1. **Source dependence on Feinman 2025.** Where Feinman's 2025 narrative is thin on a dimension, the score defaults to 5 with "insufficient detail" noted. See per-state rationales for low-confidence flags.
2. **Recent statutory changes.** FL SB 2A (Dec 2022) and LA Act 3 (eff. 7/1/2024) substantially restructured those states' regimes. Scores reflect post-reform state. Legislative tracking would need ongoing maintenance.
3. **Health and life lines excluded.** Some states (CA, NY, TX, IL) have distinct health-line regimes that this ranking does not capture. A health-specific ranking would reorder the top of the table notably.
4. **Workers' comp excluded.** Most states bar bad-faith via WC exclusivity.
5. **Score precision.** Per-factor scores are anchored 0–10 integers. Score equality on the weighted average (e.g., MT/RI tied at 6.32) is real, not approximated.
6. **F10 (recent appellate trend) carries some judgment.** Where Feinman silent, defaulted to 5.
7. **Direct-action and class-action structures are not separately scored.** A state's friendliness to bad-faith class actions could affect insurer behavior independently; this ranking does not capture it.

## Reproducibility

```
# 1. Rebuild ranking from per-batch JSON
python3 bad_faith_rank/scripts/build_ranking.py

# 2. Compute tiers and structural clusters
python3 bad_faith_rank/scripts/build_clusters.py

# 3. Rebuild HTML viewer
python3 bad_faith_rank/scripts/build_viewer.py
```

All data is in `bad_faith_rank/data/`. Source extracts are in `.tmp/bad_faith_ranking/`. Re-tuning weights does not require re-running scripts — the viewer's sliders update the ranking client-side.
