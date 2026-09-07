"""ThoracicOncoBench prediction evaluator v0.2.1.

Metrics (intention-to-evaluate: missing/invalid predictions count as incorrect):
- accuracy, macro-F1, per-class precision/recall/F1
- progression recall with 95% Wilson CI
- fatal stable error (progression judged stable) AND progression judged regression,
  combined high-consequence undercall rate, with 95% Wilson CI
- false progression rate (stable/regression judged progression)
- metastasis recall/omission/false-positive and probable-metastasis (met_suspicious) omission
- patient-level clustered bootstrap CIs for headline metrics (--bootstrap)

Usage:
  python scripts/evaluate_predictions.py --predictions path/to/predictions.jsonl \
      [--instances data/longitudinal_change_primary.jsonl] [--split test] \
      [--task longitudinal_change_primary] [--bootstrap 1000]
"""

import argparse
import json
import math
import random
from collections import Counter, defaultdict
from pathlib import Path

LABELS = ["progression", "regression", "stable", "mixed"]


def wilson(successes, n, z=1.96):
    if n == 0:
        return (None, None)
    p = successes / n
    denom = 1 + z * z / n
    center = (p + z * z / (2 * n)) / denom
    half = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / denom
    return (max(0.0, center - half), min(1.0, center + half))


def load_predictions(path):
    preds = {}
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        o = json.loads(line)
        p = o.get("prediction", o)
        preds[o.get("instance_id")] = {
            "change": str(p.get("change", "")).strip().lower(),
            "new_metastatic_disease": p.get("new_metastatic_disease", False),
        }
    return preds


def compute_metrics(rows):
    n = len(rows)
    if n == 0:
        return {}
    correct = sum(1 for r in rows if r["pred"] == r["ref"])
    tp, fp, fn = Counter(), Counter(), Counter()
    for r in rows:
        for lab in LABELS:
            if r["pred"] == lab and r["ref"] == lab:
                tp[lab] += 1
            elif r["pred"] == lab:
                fp[lab] += 1
            elif r["ref"] == lab:
                fn[lab] += 1
    f1s = []
    per_class = {}
    for lab in LABELS:
        prec = tp[lab] / (tp[lab] + fp[lab]) if (tp[lab] + fp[lab]) else None
        rec = tp[lab] / (tp[lab] + fn[lab]) if (tp[lab] + fn[lab]) else None
        f1 = (2 * prec * rec / (prec + rec)) if prec and rec else 0.0
        if tp[lab] + fn[lab] > 0:
            f1s.append(f1)
        per_class[lab] = {"precision": prec, "recall": rec, "f1": f1,
                          "support": tp[lab] + fn[lab]}

    prog_n = tp["progression"] + fn["progression"]
    prog_rec = tp["progression"] / prog_n if prog_n else None
    fatal_stable = sum(1 for r in rows if r["ref"] == "progression" and r["pred"] == "stable")
    fatal_regression = sum(1 for r in rows if r["ref"] == "progression" and r["pred"] == "regression")
    undercall = fatal_stable + fatal_regression
    non_prog_n = sum(1 for r in rows if r["ref"] in ("stable", "regression"))
    false_prog = sum(1 for r in rows if r["ref"] in ("stable", "regression")
                     and r["pred"] == "progression")

    met_pos = [r for r in rows if r["ref_met"]]
    met_hit = sum(1 for r in met_pos if r["pred_met"] is True)
    met_neg_n = sum(1 for r in rows if not r["ref_met"])
    met_fp = sum(1 for r in rows if not r["ref_met"] and r["pred_met"] is True)
    susp = [r for r in rows if r.get("met_suspicious")]
    susp_hit = sum(1 for r in susp if r["pred_met"] is True)

    return {
        "instances": n,
        "accuracy": correct / n,
        "macro_f1": sum(f1s) / len(f1s) if f1s else None,
        "per_class": per_class,
        "progression_support": prog_n,
        "progression_recall": prog_rec,
        "fatal_stable_error_rate": fatal_stable / prog_n if prog_n else None,
        "progression_to_regression_n": fatal_regression,
        "high_consequence_undercall_rate": undercall / prog_n if prog_n else None,
        "high_consequence_undercall_n": undercall,
        "false_progression_rate": false_prog / non_prog_n if non_prog_n else None,
        "false_progression_n": false_prog,
        "metastasis_positive_n": len(met_pos),
        "metastasis_recall": met_hit / len(met_pos) if met_pos else None,
        "metastasis_false_positive_rate": met_fp / met_neg_n if met_neg_n else None,
        "probable_met_suspicious_n": len(susp),
        "probable_met_flagged_rate": susp_hit / len(susp) if susp else None,
    }


def patient_bootstrap(rows, iters, seed):
    rng = random.Random(seed)
    by_patient = defaultdict(list)
    for r in rows:
        by_patient[r["patient_id"]].append(r)
    patients = list(by_patient)
    if len(patients) < 2:
        return None
    keys = ["accuracy", "macro_f1", "progression_recall",
            "high_consequence_undercall_rate", "fatal_stable_error_rate"]
    samples = defaultdict(list)
    for _ in range(iters):
        draw = []
        for _ in patients:
            draw.extend(by_patient[rng.choice(patients)])
        m = compute_metrics(draw)
        for k in keys:
            v = m.get(k)
            if v is not None:
                samples[k].append(v)
    return {k: [sorted(v)[int(0.025 * len(v))], sorted(v)[int(0.975 * len(v))]]
            for k, v in samples.items()}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--predictions", required=True)
    ap.add_argument("--instances", default="data/longitudinal_change_primary.jsonl")
    ap.add_argument("--split", default=None, choices=["train", "validation", "test"])
    ap.add_argument("--task", default=None,
                    choices=["longitudinal_change_primary", "longitudinal_change_secondary",
                             "longitudinal_change_indeterminate"])
    ap.add_argument("--bootstrap", type=int, default=0)
    ap.add_argument("--seed", type=int, default=20260904)
    args = ap.parse_args()

    preds = load_predictions(args.predictions)
    rows = []
    invalid = 0
    for line in open(args.instances, encoding="utf-8"):
        o = json.loads(line)
        if args.split and o.get("split") != args.split:
            continue
        if args.task and o.get("task") != args.task:
            continue
        p = preds.get(o["instance_id"], {})
        pred = str(p.get("change", "")).strip().lower()
        if pred not in LABELS + ["indeterminate"]:
            pred = "__invalid__"
            invalid += 1
        rows.append({
            "patient_id": o["patient_id"],
            "ref": o["label"]["change"],
            "pred": pred,
            "ref_met": o["label"]["new_metastatic_disease"],
            "pred_met": p.get("new_metastatic_disease", False) is True,
            "met_suspicious": o["provenance"].get("flags", {}).get("met_suspicious", False),
        })

    report = compute_metrics(rows)
    report.update({
        "predictions_file": str(Path(args.predictions).name),
        "split": args.split or "all",
        "task_filter": args.task,
        "invalid_or_missing_predictions": invalid,
    })
    n_prog = report.get("progression_support") or 0
    report["progression_recall_95ci_wilson"] = list(wilson(
        int((report["progression_recall"] or 0) * n_prog), n_prog))
    report["fatal_stable_error_rate_95ci_wilson"] = list(wilson(
        report.get("fatal_stable_error_rate") and round(report["fatal_stable_error_rate"] * n_prog) or 0, n_prog))
    report["high_consequence_undercall_95ci_wilson"] = list(wilson(
        report.get("high_consequence_undercall_n", 0), n_prog))
    if args.bootstrap:
        ci = patient_bootstrap(rows, args.bootstrap, args.seed)
        if ci:
            report["patient_clustered_bootstrap_95ci"] = ci
            report["bootstrap_iters"] = args.bootstrap

    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
