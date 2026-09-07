"""Impression-generation evaluator v0.3.0.

Metrics for findings-to-impression predictions against the radiologist-authored
reference impression, both computed on characters (Chinese text):

- ROUGE-L F1 (longest-common-subsequence based, sentence level)
- character-level F1 (distinct character multiset overlap)

Intention-to-evaluate: missing or empty predictions score 0.

Usage:
  python scripts/evaluate_impression.py --predictions path/to/predictions.jsonl \
      [--instances data/impression_generation_instances.jsonl] [--split test]
"""

import argparse
import json
import math
from collections import Counter
from pathlib import Path


def lcs_len(a, b):
    if not a or not b:
        return 0
    prev = [0] * (len(b) + 1)
    for i in range(1, len(a) + 1):
        cur = [0] * (len(b) + 1)
        ai = a[i - 1]
        for j in range(1, len(b) + 1):
            cur[j] = prev[j - 1] + 1 if ai == b[j - 1] else max(prev[j], cur[j - 1])
        prev = cur
    return prev[-1]


def rouge_l_f1(ref, hyp):
    if not ref or not hyp:
        return 0.0
    l = lcs_len(ref, hyp)
    if l == 0:
        return 0.0
    p = l / len(hyp)
    r = l / len(ref)
    return 2 * p * r / (p + r)


def char_f1(ref, hyp):
    if not ref or not hyp:
        return 0.0
    rc, hc = Counter(ref), Counter(hyp)
    overlap = sum((rc & hc).values())
    if overlap == 0:
        return 0.0
    p = overlap / len(hyp)
    r = overlap / len(ref)
    return 2 * p * r / (p + r)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--predictions", required=True)
    ap.add_argument("--instances", default="data/impression_generation_instances.jsonl")
    ap.add_argument("--split", default=None, choices=["train", "validation", "test"])
    args = ap.parse_args()

    preds = {}
    for line in open(args.predictions, encoding="utf-8"):
        line = line.strip()
        if not line:
            continue
        o = json.loads(line)
        p = o.get("prediction", o)
        preds[o.get("instance_id")] = (p.get("impression") or p.get("output") or "").strip()

    n = 0
    missing = 0
    rl_sum = cf_sum = 0.0
    by_ref_len = Counter()
    for line in open(args.instances, encoding="utf-8"):
        o = json.loads(line)
        if args.split and o.get("split") != args.split:
            continue
        n += 1
        ref = (o["label"].get("reference_impression") or "").strip()
        hyp = preds.get(o["instance_id"], "")
        if not hyp:
            missing += 1
        rl_sum += rouge_l_f1(ref, hyp)
        cf_sum += char_f1(ref, hyp)
        by_ref_len["empty_ref" if not ref else "nonempty_ref"] += 1

    se = lambda xs: (math.sqrt(xs / n) if n else None)
    report = {
        "predictions_file": str(Path(args.predictions).name),
        "instances": n,
        "split": args.split or "all",
        "missing_or_empty_predictions": missing,
        "rouge_l_f1_mean": rl_sum / n if n else None,
        "char_f1_mean": cf_sum / n if n else None,
        "reference_availability": dict(by_ref_len),
    }
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
