"""Perturbation fidelity suite v0.2.2 (machine-only, no human annotation).

Differential-validity testing of the label engine against guideline semantics:
real trigger sentences sampled from the built benchmark are programmatically
transformed (negation insertion, hedge insertion, comparative-marker removal,
measurement role swap, metastasis hedge), and the engine's response is asserted
against the expected RECIST 1.1 / iRECIST behavior.

Output: audit/perturbation_report.json with per-transformation pass rates.

Usage:
  python scripts/perturbation_tests.py --instances data/longitudinal_change_primary.jsonl \
      --output audit/perturbation_report.json
"""

import argparse
import json
import random
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from label_engine import _extract_measurements, _scan_directional, _scan_metastasis, split_sentences

PROG_COMPARE = ("增大", "增多", "增粗")


def sample_triggers(rows, rng, category, term_filter=None, exclude_inherent=True, n=20):
    inherent = ("进展", "复发", "加重", "恶化", "好转", "缓解")
    picks = []
    seen = set()
    for o in rows:
        for t in o["provenance"].get("triggers", []):
            if t["category"] != category or t["section"] != "findings":
                continue
            if t["strength"] != "definitive":
                continue
            if exclude_inherent and any(h in t["term"] for h in inherent):
                continue
            if term_filter and not any(f in t["term"] for f in term_filter):
                continue
            k = (t["term"], t["sentence"])
            if k in seen:
                continue
            seen.add(k)
            picks.append(t)
    rng.shuffle(picks)
    return picks[:n]


def t1_negation(rows, rng, out, fails):
    cases = [t for t in sample_triggers(rows, rng, "progression", PROG_COMPARE, n=40)
             if t["sentence"].count(t["term"]) == 1][:20]
    for t in cases:
        s = t["sentence"]
        mod = s.replace(t["term"], "未见" + t["term"], 1)
        evs = _scan_directional([mod], "findings")
        if any(e.category == "progression" and e.strength == "definitive"
               and e.term == t["term"] for e in evs):
            fails.append({"test": "T1_negation", "sentence": s, "modified": mod})
    out["T1_negation_insertion_before_progression_verb"] = {"n": len(cases)}
    return len(cases)


def t2_hedge(rows, rng, out, fails):
    cases = sample_triggers(rows, rng, "progression", exclude_inherent=False)
    for t in cases:
        s = t["sentence"]
        mod = s + "，性质待定，建议追查"
        evs = _scan_directional([mod], "findings")
        if any(e.category == "progression" and e.strength == "definitive" for e in evs):
            fails.append({"test": "T2_hedge", "sentence": s, "modified": mod})
    out["T2_hard_uncertainty_downgrades_progression"] = {"n": len(cases)}
    return len(cases)


def t3_compare_removal(rows, rng, out, fails):
    cases = [t for t in sample_triggers(rows, rng, "progression", PROG_COMPARE, n=60)
             if t["sentence"].count(t["term"]) == 1 and t["sentence"].count("较前") == 1][:20]
    for t in cases:
        s = t["sentence"]
        mod = s.replace("较前", "", 1)
        evs = _scan_directional([mod], "findings")
        if any(e.category == "progression" and e.strength == "definitive"
               and e.term == t["term"] for e in evs):
            fails.append({"test": "T3_compare_removal", "sentence": s, "modified": mod})
    out["T3_bare_adjective_without_compare_marker_does_not_trigger"] = {"n": len(cases)}
    return len(cases)


def t4_role_swap(rows, rng, out, fails):
    cases = []
    seen = set()
    for o in rows:
        for m in o["provenance"].get("measurement_evidence", []):
            if m["direction"] not in ("progression", "regression"):
                continue
            if abs(m["relative_change"]) < 0.4:
                continue
            if ("原" not in m["sentence"]) or ("现" not in m["sentence"]):
                continue
            k = m["sentence"]
            if k in seen:
                continue
            seen.add(k)
            cases.append(m)
    rng.shuffle(cases)
    cases = cases[:20]
    for m in cases:
        mod = m["sentence"].replace("原", "#P#").replace("现", "原").replace("#P#", "现")
        got = _extract_measurements([mod], "findings")
        if not got or got[0]["direction"] == m["direction"]:
            fails.append({"test": "T4_role_swap", "sentence": m["sentence"], "modified": mod,
                          "original_direction": m["direction"],
                          "got": got[0]["direction"] if got else None})
    out["T4_prior_current_marker_swap_flips_direction"] = {"n": len(cases)}
    return len(cases)


def t6_met_hedge(rows, rng, out, fails):
    cases = []
    seen = set()
    for o in rows:
        for t in o["provenance"].get("metastasis_triggers", []):
            if not t.get("definitive") or t.get("negated"):
                continue
            s = t["sentence"]
            if "考虑转移" not in s or s in seen:
                continue
            if re.search(r"考虑转移(较前|进展|增多|增大)", s):
                continue
            seen.add(s)
            cases.append(t)
    rng.shuffle(cases)
    cases = cases[:20]
    for t in cases:
        mod = t["sentence"].replace("考虑转移", "考虑转移可能大", 1)
        trigs = _scan_metastasis([mod], t["section"])
        if any(x["definitive"] for x in trigs):
            fails.append({"test": "T6_met_hedge", "sentence": t["sentence"], "modified": mod})
    out["T6_hedged_metastasis_loses_definitive_status"] = {"n": len(cases)}
    return len(cases)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--instances", default="data/longitudinal_change_primary.jsonl")
    ap.add_argument("--output", default="audit/perturbation_report.json")
    ap.add_argument("--seed", type=int, default=20260904)
    args = ap.parse_args()

    rows = [json.loads(l) for l in open(args.instances, encoding="utf-8")]
    rng = random.Random(args.seed)
    out = {}
    fails = []
    total = 0
    for fn in (t1_negation, t2_hedge, t3_compare_removal, t4_role_swap, t6_met_hedge):
        total += fn(rows, rng, out, fails)
    report = {
        "suite": "perturbation fidelity v0.2.2",
        "purpose": ("machine-only differential-validity testing: transformed real sentences must "
                    "change engine output in the direction prescribed by RECIST 1.1 (negated new "
                    "lesion/enlargement is not progression) and iRECIST (hedged statements are not "
                    "unequivocal progression)"),
        "tests": out,
        "total_checks": total,
        "failures": fails,
        "pass_rate": (total - len(fails)) / total if total else None,
        "seed": args.seed,
    }
    Path(args.output).parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    print(json.dumps({"total": total, "failures": len(fails),
                      "pass_rate": report["pass_rate"]}, ensure_ascii=False))


if __name__ == "__main__":
    main()
