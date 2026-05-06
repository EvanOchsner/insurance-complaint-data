"""Merge per-batch factor-score JSON files into a single per-state ranking dataset.

Inputs:
  .tmp/bad_faith_ranking/scores_batch1.json  (AL..ID; 12-factor schema, F11 will be ignored)
  .tmp/bad_faith_ranking/scores_batch2.json  (IL..MO; 11-factor schema, no F11)
  .tmp/bad_faith_ranking/scores_batch3.json  (MT..PA; 11-factor schema, no F11)
  .tmp/bad_faith_ranking/scores_batch4.json  (RI..WY; 11-factor schema, no F11)

Outputs:
  bad_faith_rank/data/states_factor_scores.json   per-state per-factor scores + level indices + rationales + cites
  bad_faith_rank/data/factors.json                factor metadata (id, label, default float weight, levels)
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


def uniform_levels(values_and_text):
    """Build a levels list with values evenly spaced on 0-10.
    Input: list of (name, explainer) pairs ordered low->high.
    """
    n = len(values_and_text)
    out = []
    for i, (name, explainer) in enumerate(values_and_text):
        value = round(i * 10 / (n - 1), 4)
        out.append({"name": name, "value": value, "explainer": explainer})
    return out


# Factor metadata. Order = display order in viewer. F11 dropped in v0.3.
# Default weights are floats in [0,1] (sum = 1.0).
FACTORS = [
    {
        "id": "f1a_first_party_cause",
        "label": "First-party cause of action",
        "default_weight": 0.08,
        "category": "doctrinal",
        "levels": uniform_levels([
            ("None recognized", "No common-law tort or statutory cause of action for first-party bad faith."),
            ("Narrow / statute-only, no PRoA", "Limited remedy available only via statute (e.g., IL §155, NY Bi-Economy) without a freestanding tort PRoA."),
            ("Tort recognized, significant limits", "Common-law tort exists but is narrowed by judicial doctrine, scope limits, or higher burden."),
            ("Tort well-established, broadly available", "Tort cause of action is firmly recognized for first-party insureds with reasonable scope and damages."),
            ("Firm + broad damages + lenient standard", "Tort firmly established with broad damages and lenient liability standard (CA Gruenberg/Egan, MT, AZ Noble)."),
        ]),
    },
    {
        "id": "f1b_third_party_cause",
        "label": "Third-party / duty-to-settle cause of action",
        "default_weight": 0.04,
        "category": "doctrinal",
        "levels": uniform_levels([
            ("No duty-to-settle cause of action", "Liability insurer is not exposed to extra-contractual liability for failure to settle within limits."),
            ("Limited Stowers/Crisci doctrine", "A narrow doctrinal route exists but with significant constraints on damages or standard."),
            ("Standard duty-to-settle doctrine", "Mainstream Stowers/Crisci-line cause of action; full excess judgment generally recoverable."),
            ("Strong duty-to-settle, broad damages", "Robust doctrine with low burden, broad damages, and clear plaintiff path (CA Crisci, TX Stowers)."),
        ]),
    },
    {
        "id": "f2_statutory_proa",
        "label": "Statutory private right of action",
        "default_weight": 0.14,
        "category": "doctrinal",
        "levels": uniform_levels([
            ("No statutory PRoA", "Statute is regulatory-only; no private right of action under it (CA post-Moradi-Shalal, OR, MN)."),
            ("Limited PRoA, narrow scope", "PRoA exists but tied to specific narrow conduct, or only first-party OR third-party (not both)."),
            ("Broad PRoA, arduous hurdles", "PRoA reaches both first- and third-party but with significant procedural hurdles."),
            ("Broad PRoA, modest hurdles", "Broadly available across both with modest cure/notice (e.g., FL §624.155 60-day CRN)."),
            ("Broad + low hurdles + mandatory remedies", "Broadly available, low hurdles, mandatory remedies (WA IFCA, TX Ch. 541/542)."),
        ]),
    },
    {
        "id": "f3_liability_standard",
        "label": "Liability standard",
        "default_weight": 0.08,
        "category": "doctrinal",
        "levels": uniform_levels([
            ("Actual malice / clear-and-convincing", "Plaintiff must prove subjective bad intent, often by clear-and-convincing evidence."),
            ("Reckless or willful", "Standard requires reckless disregard or knowing wrongdoing; the practical burden is high."),
            ("No reasonable basis", "Plaintiff need only show insurer lacked a reasonable basis for the denial or underpayment."),
            ("Negligence-equivalent or strict", "Negligence-like or strict-liability-like standard for certain statutory unfair claim practices."),
        ]),
    },
    {
        "id": "f4_extracontractual_damages",
        "label": "Extra-contractual damages",
        "default_weight": 0.12,
        "category": "doctrinal",
        "levels": uniform_levels([
            ("Contract damages only", "No extra-contractual damages; insured limited to policy proceeds and prejudgment interest."),
            ("Narrow consequentials only", "Limited consequential damages in narrow circumstances; emotional distress not recoverable."),
            ("Standard consequentials", "Consequential and emotional-distress damages available; excess-of-policy capped or unavailable."),
            ("Full consequentials + excess (third-party)", "Broad consequential damages and full excess judgment available in third-party context."),
            ("Broad damages, no cap", "All categories available with no statutory cap; expansive judicial doctrine."),
        ]),
    },
    {
        "id": "f5_punitive_damages",
        "label": "Punitive damages",
        "default_weight": 0.08,
        "category": "doctrinal",
        "levels": uniform_levels([
            ("Unavailable", "Punitive damages categorically unavailable in bad-faith actions."),
            ("Available, strict / hard caps", "Available only on clear-and-convincing 'malice' showing with low statutory cap."),
            ("Available, moderate caps", "Generally available on standard malice/recklessness showing; meaningful but capped (e.g., 3x compensatory)."),
            ("Broadly available, no cap", "Available on standard showing with no statutory cap or a very high cap."),
        ]),
    },
    {
        "id": "f6_statutory_penalty",
        "label": "Statutory penalty / multiplier",
        "default_weight": 0.12,
        "category": "doctrinal",
        "levels": uniform_levels([
            ("None", "No statutory penalty, multiplier, or premium-interest provision."),
            ("Modest interest premium", "Statute adds a modest interest premium on overdue payments."),
            ("Significant interest or modest %", "12%+ interest or a modest percent penalty layered on the underlying claim."),
            ("Multiplier ≥1.5x or large %", "Statutory multiplier of 1.5x+ or large percent penalty (GA 50%, TN 25%, NM treble via UPA)."),
            ("Treble or 2–3x, low friction", "Treble damages (WA IFCA) or 2–3x multiplier with minimal procedural friction."),
        ]),
    },
    {
        "id": "f7_attorney_fees",
        "label": "Attorney-fee shifting",
        "default_weight": 0.10,
        "category": "doctrinal",
        "levels": uniform_levels([
            ("No fee shifting", "American rule applies; insureds pay their own fees regardless of outcome."),
            ("Narrow / discretionary fee shift", "Fees available only in narrow circumstances or at court discretion; not routinely awarded."),
            ("Statutory fee shift, conditions apply", "One-way fee shift to prevailing insured under specified statutory conditions."),
            ("Broad one-way fee shift", "Fees routinely available to prevailing insured under bad-faith statute or common-law doctrine."),
            ("Mandatory fees + costs + multipliers", "Mandatory fee award plus expert costs; some jurisdictions allow lodestar multipliers."),
        ]),
    },
    {
        "id": "f8_pre_suit_barriers",
        "label": "Pre-suit barriers",
        "default_weight": 0.06,
        "category": "procedural",
        "levels": uniform_levels([
            ("Heavy mandatory exhaustion + cure", "Mandatory long cure period plus dual exhaustion plus strict notice (e.g., MD admin-channel hybrid)."),
            ("Mandatory cure period", "Mandatory 30–60 day cure period with formal notice/demand requirement."),
            ("Light notice, no cure", "Some pre-suit notice required but no mandatory cure window."),
            ("No pre-suit barrier", "Insured may file immediately upon denial; no notice or cure required."),
        ]),
    },
    {
        "id": "f9_admin_remedy",
        "label": "Administrative remedy strength",
        "default_weight": 0.08,
        "category": "procedural",
        "levels": uniform_levels([
            ("Minimal admin role", "DOI does not investigate individual claim disputes or take substantive action on them."),
            ("Logging only, no findings", "DOI tracks complaints but does not issue substantive findings or take enforcement action on individual claims."),
            ("Substantive findings + fining authority", "DOI investigates claims, issues findings, and has meaningful fining authority over insurer conduct."),
            ("Quasi-adjudicatory channel", "DOI provides a structured pre-suit or parallel quasi-adjudication channel with weighted findings (e.g., MD §27-1001)."),
        ]),
    },
    {
        "id": "f10_recent_appellate_trend",
        "label": "Recent appellate trend",
        "default_weight": 0.10,
        "category": "environment",
        "levels": uniform_levels([
            ("Sustained narrowing", "Recent legislation or appellate decisions have narrowed insured-side remedies (FL SB 2A, LA Act 3, TX HB 1774)."),
            ("Stable / mixed", "No clear directional trend over the last ~10 years; doctrinal status quo."),
            ("Sustained broadening", "Recent legislation or appellate decisions have expanded insured-side remedies."),
        ]),
    },
]
FACTOR_IDS = {f["id"] for f in FACTORS}


def snap_to_level(raw_score, levels):
    """Return the index of the level whose value is closest to raw_score."""
    best_idx, best_dist = 0, abs(raw_score - levels[0]["value"])
    for i, lvl in enumerate(levels[1:], start=1):
        d = abs(raw_score - lvl["value"])
        if d < best_dist:
            best_dist, best_idx = d, i
    return best_idx


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
    """Drop f11 if present (batch 1), validate factor coverage, snap each score to nearest level."""
    scores = entry.get("scores", {})
    scores.pop("f11_inverse_industry_signal", None)
    missing = FACTOR_IDS - set(scores.keys())
    extra = set(scores.keys()) - FACTOR_IDS
    if missing:
        raise ValueError(f"state {entry['state']} missing factors: {missing}")
    if extra:
        print(f"warning: state {entry['state']} has extra factors (ignored): {extra}", file=sys.stderr)
    # assign level index per factor based on raw score
    factor_by_id = {f["id"]: f for f in FACTORS}
    for fid, fs in scores.items():
        levels = factor_by_id[fid]["levels"]
        raw = fs["score"]
        idx = snap_to_level(raw, levels)
        fs["level"] = idx
    return entry


def weighted_score_from_levels(state_scores, weights):
    """Weighted average using the level value, normalized to 0-10."""
    num = 0.0
    den = 0.0
    factor_by_id = {f["id"]: f for f in FACTORS}
    for f in FACTORS:
        w = weights.get(f["id"], f["default_weight"])
        if w <= 0:
            continue
        idx = state_scores[f["id"]]["level"]
        val = factor_by_id[f["id"]]["levels"][idx]["value"]
        num += val * w
        den += w
    return num / den if den > 0 else 0.0


def main():
    states = load_batches()
    for code, entry in states.items():
        normalize_entry(entry)

    default_weights = {f["id"]: f["default_weight"] for f in FACTORS}

    # Build per-state ranking under default weights using level-snapped values
    ranked = []
    for code, entry in states.items():
        score = weighted_score_from_levels(entry["scores"], default_weights)
        ranked.append({
            "state": code,
            "state_name": entry["state_name"],
            "score": round(score, 3),
        })
    ranked.sort(key=lambda r: -r["score"])

    # Assign ranks with ties (1-based competition ranking)
    prev_score = None
    rank = 0
    for i, row in enumerate(ranked, start=1):
        if row["score"] != prev_score:
            rank = i
            prev_score = row["score"]
        row["rank"] = rank

    # Write outputs
    states_out = {
        "version": "0.4",
        "scope": "First- and third-party bad faith for individual (non-commercial) P&C insureds; 50 states + DC.",
        "rubric_version": "v0.4 (per-factor named levels with editable values; weights as floats in [0,1]; F8 inverse flag dropped — raw scores already follow '10 = strongest consumer protection')",
        "states": list(states.values()),
    }
    with open(OUT_DATA / "states_factor_scores.json", "w") as fh:
        json.dump(states_out, fh, indent=2)

    with open(OUT_DATA / "factors.json", "w") as fh:
        json.dump(FACTORS, fh, indent=2)

    # CSV: per-state default-weighted score plus per-factor level VALUE (post-bucketing)
    factor_by_id = {f["id"]: f for f in FACTORS}
    with open(OUT_DATA / "states_ranked_default.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(["rank", "state", "state_name", "weighted_score"] + [f["id"] for f in FACTORS])
        for row in ranked:
            entry = states[row["state"]]
            factor_vals = []
            for f in FACTORS:
                fs = entry["scores"][f["id"]]
                lvl = factor_by_id[f["id"]]["levels"][fs["level"]]
                factor_vals.append(lvl["value"])
            w.writerow([row["rank"], row["state"], row["state_name"], row["score"]] + factor_vals)

    print(f"wrote {OUT_DATA}/states_factor_scores.json ({len(states)} states)")
    print(f"wrote {OUT_DATA}/factors.json ({len(FACTORS)} factors)")
    print(f"wrote {OUT_DATA}/states_ranked_default.csv")
    print()
    print("Top 10 (default weights, level-bucketed):")
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
