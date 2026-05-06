"""Define score-band tiers and structural clusters from factor scores.

Score-band tiers are derived from default-weight scores and natural breaks.
Structural clusters are derived from the *factor profile* (which protections
exist) and are independent of weights — they capture likely causal drivers
of observed bad-faith activity differences.
"""
import json
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DATA = REPO / "bad_faith_rank" / "data"

# ---- Score-band tier definitions ----
# Cut-points selected from natural breaks in default-weight distribution.
TIER_BANDS = [
    {"id": "T1", "label": "Tier 1 — Strongest",        "min_score": 7.0, "color": "#1a9850"},
    {"id": "T2", "label": "Tier 2 — Strong",           "min_score": 6.0, "color": "#66bd63"},
    {"id": "T3", "label": "Tier 3 — Moderate",         "min_score": 5.0, "color": "#fee08b"},
    {"id": "T4", "label": "Tier 4 — Weak",             "min_score": 4.0, "color": "#fdae61"},
    {"id": "T5", "label": "Tier 5 — Weakest",          "min_score": 0.0, "color": "#d73027"},
]

def assign_tier(score):
    for band in TIER_BANDS:
        if score >= band["min_score"]:
            return band["id"]
    return TIER_BANDS[-1]["id"]

# ---- Structural cluster definitions ----
# Independent of weights. Based on factor signature (which protections present).
# A state is assigned to the FIRST matching cluster, in order.
CLUSTERS = [
    {
        "id": "S0_admin_hybrid",
        "label": "Mandatory Admin-Channel Hybrid",
        "description": "Statute requires a pre-suit administrative complaint to the state DOI as a condition of filing a bad-faith suit. The DOI's findings carry weight, and procedural barriers are unusually high. Currently a class of one (Maryland §27-1001 / §3-1701).",
        "drivers": "Bad-faith disputes channel through the regulator first; DOI dispositions are a meaningful primary signal; court filings are filtered.",
        "examples_expected": ["MD"],
        "predicate": lambda s: s["f9_admin_remedy"]["score"] >= 8 and s["f8_pre_suit_barriers"]["score"] <= 1,
    },
    {
        "id": "S1_multi_tool_statutory",
        "label": "Multi-Tool Statutory Regime",
        "description": "Robust statutory cause of action with built-in remedies — typically a multiplier or percent-penalty + one-way attorney fees + a clear standard. Insureds can litigate without relying on common-law tort.",
        "drivers": "Statutory teeth predict higher litigation volume and more pre-suit settlement; CRN/demand mechanisms generate large public databases of allegations.",
        "examples_expected": ["WA", "PA", "MA", "CO", "NM", "TX"],
        "predicate": lambda s: s["f2_statutory_proa"]["score"] >= 7 and s["f6_statutory_penalty"]["score"] >= 5 and s["f7_attorney_fees"]["score"] >= 5,
    },
    {
        "id": "S2_statute_constrained",
        "label": "Statutory Path, Constrained",
        "description": "A statutory bad-faith path exists but is narrower than the multi-tool regimes — capped damages (IL §155, VA §38.2-209), strict construction (TN §56-7-105), narrow scope (RI §9-1-33 first-party only), demand-letter prerequisites that gate filing, or a single-tool subset (e.g., percent-penalty without fee shifting, or fee shifting without multiplier).",
        "drivers": "Procedural prerequisites (CRNs, demand letters) generate visible plaintiff-side activity; statutory caps hold settlement values down; common-law tort either absent or preempted by the statute.",
        "examples_expected": ["RI", "KY", "MO", "NV", "NC", "CT", "NJ", "TN", "FL", "GA", "WV", "LA", "IL", "MT", "ME", "AR", "MN"],
        "predicate": lambda s: (s["f2_statutory_proa"]["score"] >= 4) or (s["f2_statutory_proa"]["score"] == 3 and s["f6_statutory_penalty"]["score"] >= 5),
    },
    {
        "id": "S3_common_law_tort",
        "label": "Common-Law Tort Driven",
        "description": "Recognized common-law tort cause of action for first-party bad faith (or contract+tort hybrid), but no meaningful statutory PRoA. Damages and standards depend on judicial doctrine.",
        "drivers": "Litigation is concentrated in larger-loss cases where contingency-fee economics work; lower-volume case-by-case footprint; admin-side complaint volume is the more visible signal.",
        "examples_expected": ["CA", "AZ", "AK", "OK", "HI", "ID", "ND", "OH", "IA", "WI", "SC", "AL", "MS", "OR", "VT", "WY", "DE", "SD", "NE", "IN"],
        "predicate": lambda s: s["f1a_first_party_cause"]["score"] >= 5,
    },
    {
        "id": "S4_minimal_protection",
        "label": "Minimal Protection",
        "description": "No robust common-law tort AND no meaningful statutory PRoA. Insureds are largely limited to contract damages, narrow regulatory penalties, or attorney-fee statutes that do not compensate for non-payment.",
        "drivers": "Bad-faith litigation is rare and low-stakes; admin complaint volume is the dominant footprint; insurer behavior is constrained more by reputation/market than by law.",
        "examples_expected": ["NY", "MI", "DC", "NH", "UT", "VA", "KS"],
        "predicate": lambda s: True,  # catch-all
    },
]

def assign_cluster(scores):
    for c in CLUSTERS:
        if c["predicate"](scores):
            return c["id"]
    return CLUSTERS[-1]["id"]

def main():
    with open(DATA / "states_factor_scores.json") as fh:
        data = json.load(fh)

    factors = json.load(open(DATA / "factors.json"))
    factor_by_id = {f["id"]: f for f in factors}
    factor_ids = [f["id"] for f in factors]
    default_weights = {f["id"]: f["default_weight"] for f in factors}

    def level_value(scores, fid):
        f = factor_by_id[fid]
        idx = scores[fid].get("level")
        if idx is None:
            # legacy fallback: snap raw score to nearest level value
            raw = scores[fid]["score"]
            best_idx, best_d = 0, abs(raw - f["levels"][0]["value"])
            for i, lvl in enumerate(f["levels"][1:], start=1):
                d = abs(raw - lvl["value"])
                if d < best_d:
                    best_d, best_idx = d, i
            idx = best_idx
        return f["levels"][idx]["value"]

    # Compute default-weight score for each state, assign tier and cluster.
    # Uses level-bucketed values (matching the viewer); cluster predicates still use raw scores.
    out_states = []
    for entry in data["states"]:
        scores = entry["scores"]
        num = sum(level_value(scores, fid) * default_weights[fid] for fid in factor_ids)
        den = sum(default_weights[fid] for fid in factor_ids)
        weighted = num / den if den > 0 else 0.0

        tier = assign_tier(weighted)
        cluster = assign_cluster(scores)

        out_states.append({
            "state": entry["state"],
            "state_name": entry["state_name"],
            "default_score": round(weighted, 3),
            "tier": tier,
            "structural_cluster": cluster,
            "scores": scores,
        })

    out_states.sort(key=lambda r: -r["default_score"])

    # Write enriched data
    enriched = {
        "version": data["version"],
        "scope": data["scope"],
        "rubric_version": data["rubric_version"],
        "tier_bands": TIER_BANDS,
        "structural_clusters": [{k: v for k, v in c.items() if k != "predicate"} for c in CLUSTERS],
        "states": out_states,
    }
    with open(DATA / "states_with_clusters.json", "w") as fh:
        json.dump(enriched, fh, indent=2)
    print(f"wrote {DATA}/states_with_clusters.json")

    # Reports
    print()
    print("Score-band tiers (default weights):")
    for band in TIER_BANDS:
        members = [s["state"] for s in out_states if s["tier"] == band["id"]]
        print(f"  {band['id']} {band['label']:30s} (n={len(members):2d}): {', '.join(members)}")

    print()
    print("Structural clusters:")
    for c in CLUSTERS:
        members = [(s["state"], s["default_score"]) for s in out_states if s["structural_cluster"] == c["id"]]
        if not members:
            continue
        members_str = ", ".join(f"{m[0]}({m[1]:.2f})" for m in members)
        print(f"  {c['id']:30s} {c['label']:35s} (n={len(members):2d})")
        print(f"    {members_str}")

if __name__ == "__main__":
    main()
