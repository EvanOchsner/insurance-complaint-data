"""Merge per-batch factor-score JSON files into a single per-state ranking dataset.

Inputs:
  .tmp/bad_faith_ranking/scores_batch1.json  (AL..ID; 12-factor schema, F11 will be ignored)
  .tmp/bad_faith_ranking/scores_batch2.json  (IL..MO; 11-factor schema, no F11)
  .tmp/bad_faith_ranking/scores_batch3.json  (MT..PA; 11-factor schema, no F11)
  .tmp/bad_faith_ranking/scores_batch4.json  (RI..WY; 11-factor schema, no F11)

Outputs:
  bad_faith_rank/data/states_factor_scores.json   per-state per-factor scores + rationales + cites
  bad_faith_rank/data/factors.json                factor metadata (id, label, default weight, scoring rule summary)
  bad_faith_rank/data/states_ranked_default.csv   default-weight ranking
"""
import json
import csv
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
TMP = REPO / ".tmp" / "bad_faith_ranking"
OUT_DATA = REPO / "bad_faith_rank" / "data"
OUT_DATA.mkdir(parents=True, exist_ok=True)

# Factor metadata. Order = display order in viewer. F11 dropped in v0.3.
FACTORS = [
    {"id": "f1a_first_party_cause",      "label": "First-party cause of action",                      "default_weight": 8,  "category": "doctrinal",  "inverse": False},
    {"id": "f1b_third_party_cause",      "label": "Third-party / duty-to-settle cause of action",     "default_weight": 4,  "category": "doctrinal",  "inverse": False},
    {"id": "f2_statutory_proa",          "label": "Statutory private right of action",                "default_weight": 14, "category": "doctrinal",  "inverse": False},
    {"id": "f3_liability_standard",      "label": "Liability standard",                               "default_weight": 8,  "category": "doctrinal",  "inverse": False},
    {"id": "f4_extracontractual_damages","label": "Extra-contractual damages",                        "default_weight": 12, "category": "doctrinal",  "inverse": False},
    {"id": "f5_punitive_damages",        "label": "Punitive damages",                                 "default_weight": 8,  "category": "doctrinal",  "inverse": False},
    {"id": "f6_statutory_penalty",       "label": "Statutory penalty / multiplier",                   "default_weight": 12, "category": "doctrinal",  "inverse": False},
    {"id": "f7_attorney_fees",           "label": "Attorney-fee shifting",                            "default_weight": 10, "category": "doctrinal",  "inverse": False},
    {"id": "f8_pre_suit_barriers",       "label": "Pre-suit barriers (inverse: more barriers = worse)","default_weight": 6,  "category": "procedural", "inverse": True},
    {"id": "f9_admin_remedy",            "label": "Administrative remedy strength",                   "default_weight": 8,  "category": "procedural", "inverse": False},
    {"id": "f10_recent_appellate_trend", "label": "Recent appellate trend",                           "default_weight": 10, "category": "environment","inverse": False},
]
FACTOR_IDS = {f["id"] for f in FACTORS}

def load_batches():
    states = {}
    for n in (1, 2, 3, 4):
        p = TMP / f"scores_batch{n}.json"
        with open(p) as fh:
            data = json.load(fh)
        for entry in data:
            code = entry["state"]
            if code in states:
                raise ValueError(f"duplicate state {code} in batch {n}")
            states[code] = entry
    if len(states) != 51:
        raise ValueError(f"expected 51 states, got {len(states)}: {sorted(states)}")
    return states

def normalize_entry(entry):
    """Drop f11 if present (batch 1), validate factor coverage."""
    scores = entry.get("scores", {})
    scores.pop("f11_inverse_industry_signal", None)
    missing = FACTOR_IDS - set(scores.keys())
    extra = set(scores.keys()) - FACTOR_IDS
    if missing:
        raise ValueError(f"state {entry['state']} missing factors: {missing}")
    if extra:
        # Should not happen after the f11 pop above
        print(f"warning: state {entry['state']} has extra factors (ignored): {extra}", file=sys.stderr)
    return entry

def weighted_score(state_scores, weights):
    """Weighted average across all factors, normalized to 0-10."""
    num = 0.0
    den = 0.0
    for f in FACTORS:
        w = weights.get(f["id"], f["default_weight"])
        if w <= 0:
            continue
        s = state_scores[f["id"]]["score"]
        num += s * w
        den += w
    return num / den if den > 0 else 0.0

def main():
    states = load_batches()
    for code, entry in states.items():
        normalize_entry(entry)

    default_weights = {f["id"]: f["default_weight"] for f in FACTORS}

    # Build per-state ranking under default weights
    ranked = []
    for code, entry in states.items():
        score = weighted_score(entry["scores"], default_weights)
        ranked.append({
            "state": code,
            "state_name": entry["state_name"],
            "score": round(score, 3),
        })
    ranked.sort(key=lambda r: -r["score"])

    # Assign ranks with ties (1-based, dense ranking would compress; using competition / "1224")
    prev_score = None
    rank = 0
    for i, row in enumerate(ranked, start=1):
        if row["score"] != prev_score:
            rank = i
            prev_score = row["score"]
        row["rank"] = rank

    # Write outputs
    states_out = {
        "version": "0.3",
        "scope": "First- and third-party bad faith for individual (non-commercial) P&C insureds; 50 states + DC.",
        "rubric_version": "v0.3 (Factor 11 removed; weights F2=14, F4=12, F6=12, F10=10)",
        "states": list(states.values()),
    }
    with open(OUT_DATA / "states_factor_scores.json", "w") as fh:
        json.dump(states_out, fh, indent=2)

    with open(OUT_DATA / "factors.json", "w") as fh:
        json.dump(FACTORS, fh, indent=2)

    with open(OUT_DATA / "states_ranked_default.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["rank", "state", "state_name", "weighted_score"] + [f["id"] for f in FACTORS])
        for row in ranked:
            entry = states[row["state"]]
            factor_scores = [entry["scores"][f["id"]]["score"] for f in FACTORS]
            w.writerow([row["rank"], row["state"], row["state_name"], row["score"]] + factor_scores)

    print(f"wrote {OUT_DATA}/states_factor_scores.json ({len(states)} states)")
    print(f"wrote {OUT_DATA}/factors.json ({len(FACTORS)} factors)")
    print(f"wrote {OUT_DATA}/states_ranked_default.csv")
    print()
    print("Top 10 (default weights):")
    for row in ranked[:10]:
        print(f"  {row['rank']:3d}. {row['state']:3s} {row['state_name']:25s}  {row['score']:5.2f}")
    print()
    print("Bottom 10 (default weights):")
    for row in ranked[-10:]:
        print(f"  {row['rank']:3d}. {row['state']:3s} {row['state_name']:25s}  {row['score']:5.2f}")
    print()
    print(f"score range: {ranked[-1]['score']:.2f} (worst) .. {ranked[0]['score']:.2f} (best)")
    print(f"median: {sorted([r['score'] for r in ranked])[len(ranked)//2]:.2f}")

if __name__ == "__main__":
    main()
