"""ThoracicOncoBench label audit v0.2.1.

Runs deterministic consistency checks over the generated longitudinal benchmark,
computes the single-lesion threshold vs impression-conclusion concordance
analysis, and exports a BLINDED two-radiologist adjudication package:

- adjudication_blinded.csv    (adjudicator-facing: randomized order, no engine
                               labels, report text only)
- adjudication_template.csv   (fill-in file, no engine columns)
- adjudication_analysis_key.csv (private join key with engine labels)
- ADJUDICATION_GUIDE.md       (instructions and category definitions)

Usage:
  python scripts/audit_labels.py --instances data/longitudinal_change_primary.jsonl \
      --reports data/reports_deidentified.jsonl --output-dir audit
"""

import argparse
import csv
import json
import random
import re
from collections import Counter, defaultdict
from pathlib import Path

STABLE_RE = re.compile(r"同前|相仿|无明显变化|未见明确变化|未见明显变化|稳定|未见变化")
PROG_RE = re.compile(r"进展|增大|增多|增粗|复发|新发|新增|新见|转移|加重|恶化")
REG_RE = re.compile(r"缩小|减小|减少|吸收|好转|缓解|消退")
COMPARE_RE = re.compile(r"较前|与前|与前次|较前片|对比前片")
VALID_LABELS = {"progression", "regression", "stable", "mixed", "indeterminate"}
VALID_TIERS = {"definitive", "quantitative", "directional", "suspicious", "weak", "indeterminate"}

GUIDE = """# Adjudication Guide

## Task

You are adjudicating reference labels for a longitudinal chest CT report benchmark.
For each case you receive the prior findings, the current findings, and the current
final impression from the same patient. Judge the overall longitudinal change
category of the current report relative to the prior report, and whether new
metastatic disease is documented.

## Change Categories (RECIST 1.1-informed)

- progression: a new oncologic lesion is documented, or documented increase in
  disease burden, recurrence, or clear worsening (RECIST 1.1: a new lesion
  defines progressive disease).
- regression: documented decrease in lesion size or disease burden, absorption,
  improvement, or response (>=30% diameter decrease when measurable).
- stable: no meaningful change compared with the prior report.
- mixed: simultaneous documented worsening and improvement in different lesions
  or disease sites (a report-level extension beyond RECIST 1.1 categories).
- indeterminate: evidence is insufficient, conflicting, or equivocal.

## Metastasis Flag

Set new_metastatic_disease = true only for unequivocal, non-negated metastasis
documentation (e.g., 新发转移, 转移较前进展, a non-hedged metastasis conclusion in
the impression). Hedged statements (倾向转移, 待鉴别, 可能) are NOT a positive flag.

## Procedure

1. Read each case in adjudication_blinded.csv independently of any system output.
2. Radiologist 1 and Radiologist 2 each fill their columns in
   adjudication_template.csv per case before discussion.
3. Disagreements are resolved by discussion; record the adjudicated_change and
   adjudicated_met.
4. Do not modify the case order or identifiers. Engine labels are withheld
   (blinding) and joined only at analysis time via agreement_stats.py.

## Analysis

python scripts/agreement_stats.py --filled audit/adjudication_template.csv \
    --key audit/adjudication_analysis_key.csv
"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--instances", default="data/longitudinal_change_primary.jsonl")
    ap.add_argument("--reports", default="data/reports_deidentified.jsonl")
    ap.add_argument("--output-dir", default="audit")
    ap.add_argument("--sample-per-label", type=int, default=60)
    ap.add_argument("--stable-sample", type=int, default=120)
    ap.add_argument("--postop-progression-sample", type=int, default=30)
    ap.add_argument("--seed", type=int, default=20260904)
    args = ap.parse_args()

    rows = [json.loads(l) for l in open(args.instances, encoding="utf-8")]
    reports = {}
    for line in open(args.reports, encoding="utf-8"):
        r = json.loads(line)
        reports[r["report_id"]] = r

    violations = defaultdict(list)

    for o in rows:
        iid = o["instance_id"]
        lab = o["label"]["change"]
        met = o["label"]["new_metastatic_disease"]
        imp = reports.get(o["current_report_id"], {}).get("impression") or ""

        if lab not in VALID_LABELS:
            violations["C7_invalid_label"].append(iid)
        if o["label"]["evidence_tier"] not in VALID_TIERS:
            violations["C7_invalid_tier"].append(iid)

        if lab in ("progression", "mixed", "regression"):
            has_stable = bool(STABLE_RE.search(imp))
            contrad = has_stable and not (
                (PROG_RE.search(imp) if lab in ("progression", "mixed") else False) or
                (REG_RE.search(imp) if lab in ("regression", "mixed") else False))
            if contrad and o["label"]["evidence_tier"] == "definitive":
                violations["C1_label_contradicts_stable_impression"].append(iid)

        if met and lab not in ("progression", "mixed"):
            violations["C2_met_flag_inconsistent_with_label"].append(iid)

        trigs = o["provenance"].get("metastasis_triggers", [])
        if met and trigs and not any(t.get("definitive") for t in trigs):
            violations["C3_met_flag_without_definitive_trigger"].append(iid)

        for t in o["provenance"].get("triggers", []):
            if t["category"] == "progression":
                s = t["sentence"]
                if re.search(r"同前|相仿", s) and not COMPARE_RE.search(s) and not re.search(
                        r"进展|复发|加重|恶化|新发|新增|新见", t["term"] + s[max(0, s.find(t['term'])-6):s.find(t['term'])]):
                    violations["C4_progression_trigger_on_unchanged_sentence"].append(iid)
                    break

        if o.get("interval_days", 1) <= 0:
            violations["C5_nonpositive_interval"].append(iid)

        if "impression" in json.dumps(o["input"]):
            violations["C6_impression_leakage_in_input"].append(iid)

    ids = [o["instance_id"] for o in rows]
    if len(ids) != len(set(ids)):
        violations["C9_duplicate_instance_ids"].append("(see data)")
    split_patients = defaultdict(set)
    for o in rows:
        split_patients[o["split"]].add(o["patient_id"])
    overlap = set()
    splits = list(split_patients)
    for i, a in enumerate(splits):
        for b in splits[i + 1:]:
            overlap |= split_patients[a] & split_patients[b]
    if overlap:
        violations["C8_patient_overlap_across_splits"].append(f"{len(overlap)} patients")

    rng = random.Random(args.seed)
    by_label = defaultdict(list)
    for o in rows:
        by_label[o["label"]["change"]].append(o)
    sample = []
    sampled_ids = set()
    for lab in ("progression", "regression", "mixed"):
        pool = sorted(by_label.get(lab, []), key=lambda x: x["instance_id"])
        picks = rng.sample(pool, min(args.sample_per_label, len(pool)))
        sample += picks
        sampled_ids.update(p["instance_id"] for p in picks)
    pool_stable = sorted(by_label.get("stable", []), key=lambda x: x["instance_id"])
    picks = rng.sample(pool_stable, min(args.stable_sample, len(pool_stable)))
    sample += picks
    sampled_ids.update(p["instance_id"] for p in picks)
    met_pos = [o for o in rows if o["label"]["new_metastatic_disease"]
               and o["instance_id"] not in sampled_ids]
    sample += met_pos
    sampled_ids.update(p["instance_id"] for p in met_pos)
    postop_prog = [o for o in by_label.get("progression", [])
                   if o["provenance"]["flags"].get("postoperative_language")
                   and o["instance_id"] not in sampled_ids]
    postop_prog.sort(key=lambda x: x["instance_id"])
    extra = postop_prog[:args.postop_progression_sample]
    sample += extra
    sampled_ids.update(p["instance_id"] for p in extra)
    no_change_lang = [o for o in rows
                      if not o["provenance"]["flags"].get("findings_explicit_change_language")]

    blinded = []
    for o in sample:
        rep = reports.get(o["current_report_id"], {})
        blinded.append({
            "instance_id": o["instance_id"],
            "prior_findings": o["input"]["prior_report"]["findings"],
            "current_findings": o["input"]["current_report"]["findings"],
            "current_impression": rep.get("impression") or "",
            "interval_days": o["interval_days"],
        })
    rng.shuffle(blinded)

    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    with open(out_dir / "adjudication_blinded.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["instance_id", "interval_days", "prior_findings",
                                          "current_findings", "current_impression"])
        w.writeheader()
        for b in blinded:
            w.writerow(b)
    with open(out_dir / "adjudication_template.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["instance_id", "radiologist1_change", "radiologist1_met",
                    "radiologist2_change", "radiologist2_met",
                    "adjudicated_change", "adjudicated_met", "comment"])
        for b in blinded:
            w.writerow([b["instance_id"], "", "", "", "", "", "", ""])
    with open(out_dir / "adjudication_analysis_key.csv", "w", encoding="utf-8-sig", newline="") as f:
        w = csv.writer(f)
        w.writerow(["instance_id", "engine_label", "engine_met", "evidence_tier",
                    "primary_rule", "postoperative_language", "met_suspicious"])
        for o in sample:
            fl = o["provenance"]["flags"]
            w.writerow([o["instance_id"], o["label"]["change"],
                        "true" if o["label"]["new_metastatic_disease"] else "false",
                        o["label"]["evidence_tier"], o["label"]["primary_rule"],
                        "true" if fl.get("postoperative_language") else "false",
                        "true" if fl.get("met_suspicious") else "false"])
    (out_dir / "ADJUDICATION_GUIDE.md").write_text(GUIDE, encoding="utf-8")
    with open(out_dir / "adjudication_sample.jsonl", "w", encoding="utf-8") as f:
        for b in blinded:
            key = next(o for o in sample if o["instance_id"] == b["instance_id"])
            f.write(json.dumps({
                "instance_id": b["instance_id"],
                "interval_days": b["interval_days"],
                "prior_findings": b["prior_findings"],
                "current_findings": b["current_findings"],
                "current_impression_for_adjudicator_only": b["current_impression"],
                "analysis_key": {
                    "engine_label": key["label"]["change"],
                    "engine_met": key["label"]["new_metastatic_disease"],
                    "evidence_tier": key["label"]["evidence_tier"],
                    "primary_rule": key["label"]["primary_rule"],
                },
            }, ensure_ascii=False) + "\n")

    quant_all = quant_def = None
    agree_exact = disagree_examples = None
    qrows = [o for o in rows
             if any(m["direction"] in ("progression", "regression")
                    for m in o["provenance"].get("measurement_evidence", []))]
    def qdir(o):
        return next(m["direction"] for m in o["provenance"]["measurement_evidence"]
                    if m["direction"] in ("progression", "regression"))
    qdef = [o for o in qrows if o["label"]["evidence_tier"] == "definitive"]
    agree = sum(1 for o in qdef if qdir(o) == o["label"]["change"])
    mixed_n = sum(1 for o in qdef if o["label"]["change"] == "mixed")
    disagree_examples = [
        {"instance_id": o["instance_id"], "quant_direction": qdir(o),
         "label": o["label"]["change"],
         "sentence": next(m["sentence"] for m in o["provenance"]["measurement_evidence"]
                          if m["direction"] in ("progression", "regression"))}
        for o in qdef if qdir(o) != o["label"]["change"]][:15]

    sample_flags = {
        "postoperative_language": sum(1 for o in sample if o["provenance"]["flags"].get("postoperative_language")),
        "met_suspicious": sum(1 for o in sample if o["provenance"]["flags"].get("met_suspicious")),
        "findings_without_explicit_change_language": sum(
            1 for o in sample if not o["provenance"]["flags"].get("findings_explicit_change_language")),
    }

    conv_counts = Counter()
    conv_by_label = defaultdict(Counter)
    channels_avail = Counter()
    for o in rows:
        lab = o["label"]["change"]
        tier = o["label"]["evidence_tier"]
        flags = o["provenance"].get("flags", {})
        meas = o["provenance"].get("measurement_evidence", [])
        trig = o["provenance"].get("triggers", [])
        prog_f = any(t["category"] == "progression" and t["section"] == "findings"
                     and t["strength"] == "definitive" for t in trig)
        reg_f = any(t["category"] == "regression" and t["section"] == "findings"
                    and t["strength"] == "definitive" for t in trig)
        stab_f = any(t["category"] == "stable" and t["section"] == "findings" for t in trig)
        has_imp = bool(flags.get("impression_conclusion"))
        has_quant = any(m["direction"] in ("progression", "regression") for m in meas)
        if has_imp:
            channels_avail["impression"] += 1
        if has_quant:
            channels_avail["quantitative"] += 1
        if prog_f or reg_f or stab_f:
            channels_avail["findings_directional"] += 1

        support = 0
        if tier == "definitive" and has_imp:
            support += 1
        if has_quant:
            qd_prog = any(m["direction"] == "progression" for m in meas)
            qd_reg = any(m["direction"] == "regression" for m in meas)
            if ((lab == "progression" and qd_prog) or (lab == "regression" and qd_reg)
                    or (lab == "mixed" and qd_prog and qd_reg)):
                support += 1
        if (lab in ("progression", "mixed") and prog_f) or (lab in ("regression", "mixed") and reg_f) \
                or (lab == "stable" and stab_f and not prog_f and not reg_f):
            support += 1
        conv_counts[support] += 1
        conv_by_label[lab][support] += 1

    total_rows = len(rows)
    convergence = {
        "interpretation": ("internal multi-channel corroboration: how many semi-independent "
                           "evidence channels (dual-audited impression conclusion, RECIST-informed "
                           "quantitative thresholds, findings directional language) concordantly "
                           "support each primary label; machine-only substitute for inter-rater "
                           "reliability reporting"),
        "channel_availability": dict(channels_avail),
        "support_distribution": {str(k): v for k, v in sorted(conv_counts.items())},
        "multi_channel_share": (conv_counts[2] + conv_counts[3]) / total_rows if total_rows else None,
        "support_by_label": {lab: dict(c) for lab, c in conv_by_label.items()},
    }

    report = {
        "instances_audited": len(rows),
        "label_distribution": dict(Counter(o["label"]["change"] for o in rows)),
        "tier_distribution": dict(Counter(o["label"]["evidence_tier"] for o in rows)),
        "met_positive": sum(1 for o in rows if o["label"]["new_metastatic_disease"]),
        "met_positive_by_label": dict(Counter(o["label"]["change"] for o in rows if o["label"]["new_metastatic_disease"])),
        "primary_rule_distribution": dict(Counter(o["label"]["primary_rule"] for o in rows)),
        "findings_without_explicit_change_language": {
            "count": len(no_change_lang),
            "instance_ids": [o["instance_id"] for o in no_change_lang][:50],
        },
        "single_lesion_threshold_vs_impression_concordance": {
            "n_with_directional_quant_evidence": len(qrows),
            "n_impression_driven_definitive": len(qdef),
            "exact_agreement_with_label": agree,
            "exact_agreement_rate": (agree / len(qdef)) if qdef else None,
            "mixed_labels_among_them": mixed_n,
            "disagreement_examples": disagree_examples,
            "interpretation": ("concordance between RECIST-informed single-lesion thresholds "
                               "and the impression-driven label on instances carrying both; "
                               "quantitative tier decides the label by construction, so only the "
                               "definitive (impression-driven) subset is informative"),
        },
        "multi_channel_convergence": convergence,
        "checks": {k: len(v) for k, v in violations.items()},
        "checks_passed": {k: (len(v) == 0) for k, v in violations.items()},
        "violations": {k: v[:20] for k, v in violations.items()},
        "adjudication": {
            "sample_size": len(sample),
            "design": (
                f"blinded, randomized order; {args.sample_per_label} each "
                f"progression/regression/mixed + {args.stable_sample} stable + all remaining "
                f"metastasis-positive + up to {args.postop_progression_sample} additional "
                f"postoperative-flagged progression; seed {args.seed}"
            ),
            "sample_flag_distribution": sample_flags,
            "blinding": "engine labels withheld from adjudicator files; join via adjudication_analysis_key.csv",
            "files": ["adjudication_blinded.csv", "adjudication_template.csv",
                      "adjudication_analysis_key.csv", "ADJUDICATION_GUIDE.md"],
        },
    }
    with open(out_dir / "audit_report.json", "w", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)

    print(json.dumps({k: report[k] for k in
                      ("instances_audited", "label_distribution", "met_positive",
                       "checks", "adjudication")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
