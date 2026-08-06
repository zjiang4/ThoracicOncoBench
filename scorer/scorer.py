"""
ThoracicOnco-LLMBench — 冻结阅卷脚本 (Scorer)
=================================================
用法:
  python scorer.py --predictions model_predictions.jsonl --benchmark benchmark.jsonl --output results.json

predictions.jsonl 格式 (每行一条, id 对应 benchmark):
  {"id": "T1-00001", "output": {"overall_change": "stable", "new_metastasis_signal": false}}
  {"id": "T234-00801", "output": {"impression": "...", "cTNM": {"cT":"2","cN":"0","cM":"0"}, "structured": {...}}}
  {"id": "T4-noimp-01096", "output": {"impression": "..."}}

输出 results.json: 各任务的总分 + 分项 + 错误分析
"""

import json, re, argparse, sys, os
from collections import defaultdict, Counter
from pathlib import Path


# ============ 工具函数 ============
def norm_tnm(v):
    """规范化 TNM 值: '2.0' / '2' / 'T2' / 2 -> '2'"""
    if v is None:
        return None
    s = str(v).strip()
    if s in ("", "nan", "None", "null"):
        return None
    m = re.search(r"(\d+)", s)
    return m.group(1) if m else None


def norm_text(t):
    if t is None:
        return ""
    return re.sub(r"\s+", "", str(t)).lower()


def char_jaccard(a, b):
    """字符级 Jaccard 相似度 (中文文本近似, BERTScore 不可用时的降级方案)"""
    a, b = norm_text(a), norm_text(b)
    if not a or not b:
        return 0.0
    sa, sb = set(a), set(b)
    return len(sa & sb) / len(sa | sb)


def char_f1(a, b):
    """字符级 P/R/F1 (近似)"""
    a, b = norm_text(a), norm_text(b)
    if not a or not b:
        return {"p": 0, "r": 0, "f1": 0}
    sa, sb = set(a), set(b)
    inter = len(sa & sb)
    p = inter / len(sb) if sb else 0
    r = inter / len(sa) if sa else 0
    f1 = 2 * p * r / (p + r) if (p + r) > 0 else 0
    return {"p": round(p, 4), "r": round(r, 4), "f1": round(f1, 4)}


# ============ ROUGE (中文, rouge-chinese) ============
_ROUGE = None


def get_rouge():
    global _ROUGE
    if _ROUGE is None:
        try:
            from rouge_chinese import Rouge

            _ROUGE = Rouge()
        except Exception:
            _ROUGE = False
    return _ROUGE


def rouge_l(ref, hyp):
    """返回 ROUGE-L F1; 失败降级为 char_jaccard"""
    ref, hyp = norm_text(ref), norm_text(hyp)
    if not ref or not hyp:
        return None
    r = get_rouge()
    if r:
        try:
            scores = r.get_scores(" ".join(list(hyp)), " ".join(list(ref)))
            return round(scores[0]["rouge-l"]["f"], 4)
        except Exception:
            pass
    return round(char_jaccard(ref, hyp), 4)


BERTSCORE_AVAILABLE = False


def get_bertscore():
    global BERTSCORE_AVAILABLE
    if not BERTSCORE_AVAILABLE:
        try:
            import bert_score

            BERTSCORE_AVAILABLE = bert_score
        except Exception:
            BERTSCORE_AVAILABLE = False
    return BERTSCORE_AVAILABLE


# ============ T1: 变化评估打分 ============
def score_t1(insts, preds):
    """T1 变化评估: overall_change 分类 + 致命错误"""
    valid = [
        (i, preds.get(i["id"], {}).get("output", {})) for i in insts if i["id"] in preds
    ]
    results = {"n_total": len(insts), "n_scored": len(valid)}
    if not valid:
        return results

    y_true, y_pred = [], []
    fatal_errors = 0  # 模型判 stable 但 gold 是 progression
    fatal_errors_def = 0
    for inst, out in valid:
        gold = inst["gold"]["overall_change"]
        pred = out.get("overall_change", "indeterminate")
        # 规范化 pred
        pred = str(pred).strip().lower()
        # 映射同义词
        syn = {
            "进展": "progression",
            "progress": "progression",
            "worse": "progression",
            "progressive": "progression",
            "稳定": "stable",
            "same": "stable",
            "no change": "stable",
            "unchanged": "stable",
            "退缩": "regression",
            "regress": "regression",
            "improve": "regression",
            "improved": "regression",
            "better": "regression",
            "混合": "mixed",
            "新发": "progression",
        }
        if pred in syn:
            pred = syn[pred]
        if pred not in [
            "progression",
            "stable",
            "regression",
            "mixed",
            "indeterminate",
        ]:
            pred = "indeterminate"
        y_true.append(gold)
        y_pred.append(pred)
        # 致命错误: 模型漏判 progression (模型说 stable, 实际 progression)
        if gold == "progression" and pred in ["stable"]:
            fatal_errors += 1
        # 极致命: 模型漏判新发转移
        if inst["gold"].get("new_metastasis_signal") and pred in [
            "stable",
            "regression",
        ]:
            fatal_errors_def += 1

    # 分类报告
    labels = sorted(set(y_true) | set(y_pred))
    cm = Counter(zip(y_true, y_pred))
    per_class = {}
    for lab in labels:
        tp = sum(1 for t, p in zip(y_true, y_pred) if t == lab and p == lab)
        fp = sum(1 for t, p in zip(y_true, y_pred) if t != lab and p == lab)
        fn = sum(1 for t, p in zip(y_true, y_pred) if t == lab and p != lab)
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0
        per_class[lab] = {
            "precision": round(prec, 4),
            "recall": round(rec, 4),
            "f1": round(f1, 4),
            "support": tp + fn,
        }
    macro_f1 = (
        round(sum(c["f1"] for c in per_class.values()) / len(per_class), 4)
        if per_class
        else 0
    )
    acc = round(sum(1 for t, p in zip(y_true, y_pred) if t == p) / len(y_true), 4)

    n_progression = sum(1 for t in y_true if t == "progression")
    n_metastasis = sum(
        1 for inst, _ in valid if inst["gold"].get("new_metastasis_signal")
    )

    results.update(
        {
            "accuracy": acc,
            "macro_f1": macro_f1,
            "per_class": per_class,
            "confusion_matrix": {f"{t}->{p}": c for (t, p), c in cm.items()},
            "fatal_errors_stable_when_progression": fatal_errors,
            "fatal_errors_missed_metastasis": fatal_errors_def,
            "fatal_error_rate_overall": round(fatal_errors / len(valid), 4),
            "fatal_error_rate_among_progression": round(fatal_errors / n_progression, 4)
            if n_progression
            else None,
            "metastasis_miss_rate": round(fatal_errors_def / n_metastasis, 4)
            if n_metastasis
            else None,
            "n_progression": n_progression,
            "n_metastasis": n_metastasis,
        }
    )
    return results


# ============ T3: TNM 分期打分 ============
def score_t3(insts, preds):
    """T3 分期: cTNM vs pTNM exact-match + 分量
    只评 initial 场景（术前影像 ↔ 手术 pTNM 时间正确对齐），
    postop/metastatic/surveillance 场景的 pTNM 来自既往手术，与当前影像时间错配，排除。"""
    valid = []
    excluded_time_misaligned = 0
    for i in insts:
        if i["id"] not in preds:
            continue
        ptnm = i["gold"].get("pathology_pTNM", {})
        if not ptnm.get("available"):
            continue
        if norm_tnm(ptnm.get("pT")) is None and norm_tnm(ptnm.get("pN")) is None:
            continue
        # 时间对齐检查：只评 initial 场景
        ctx = i.get("input", {}).get("clinical_context", "")
        if ctx not in ("initial_mass", "initial_ggo"):
            excluded_time_misaligned += 1
            continue
        out = preds[i["id"]].get("output", {})
        ctnm = out.get("cTNM", out.get("tnm", {}))
        if not isinstance(ctnm, dict):
            ctnm = {"cT": ctnm} if ctnm else {}
        valid.append((i, ctnm))

    if not valid:
        return {"n_scored": 0, "_note": "无可用 pTNM 金标准或模型未输出 cTNM"}

    per_comp = {
        "T": {"correct": 0, "total": 0},
        "N": {"correct": 0, "total": 0},
        "M": {"correct": 0, "total": 0},
    }
    exact = 0
    for inst, ctnm in valid:
        gold = inst["gold"]["pathology_pTNM"]
        all_ok = True
        for comp in ["T", "N", "M"]:
            g = norm_tnm(gold.get("p" + comp))
            p = norm_tnm(ctnm.get("c" + comp) or ctnm.get(comp))
            if g is not None:
                per_comp[comp]["total"] += 1
                if g == p:
                    per_comp[comp]["correct"] += 1
                else:
                    all_ok = False
            elif p is None:
                pass
            else:
                all_ok = False
        if all_ok:
            exact += 1

    return {
        "n_scored": len(valid),
        "exact_match": round(exact / len(valid), 4),
        "per_component_accuracy": {
            c: round(v["correct"] / v["total"], 4) if v["total"] > 0 else None
            for c, v in per_comp.items()
        },
        "per_component_n": {c: v["total"] for c, v in per_comp.items()},
    }


# ============ T4: 印象生成打分 ============
def score_t4(insts, preds, task_label="impression_generation"):
    """T4: ROUGE-L + char F1 + BERTScore(可选)"""
    valid = []
    for i in insts:
        if i["id"] not in preds:
            continue
        ref = None
        if "impression_reference" in i["gold"]:
            ref = i["gold"]["impression_reference"]
        elif "current_impression" in i["gold"]:
            ref = i["gold"]["current_impression"]
        elif i["input"].get("impression"):
            ref = i["input"]["impression"]
        if not ref:
            continue
        out = preds[i["id"]].get("output", {})
        hyp = out.get("impression") or out.get("impression_text") or out.get("output")
        if not hyp:
            continue
        valid.append((ref, hyp))

    if not valid:
        return {"n_scored": 0, "_note": "无可用 impression 参考或模型未输出"}

    rouges, f1s, jaccards = [], [], []
    for ref, hyp in valid:
        r = rouge_l(ref, hyp)
        if r is not None:
            rouges.append(r)
        cf = char_f1(ref, hyp)
        f1s.append(cf["f1"])
        jaccards.append(char_jaccard(ref, hyp))

    def mean(xs):
        return round(sum(xs) / len(xs), 4) if xs else 0

    result = {
        "n_scored": len(valid),
        "rouge_l_f1_mean": mean(rouges),
        "char_f1_mean": mean(f1s),
        "char_jaccard_mean": mean(jaccards),
    }

    # BERTScore (可选, 需 torch; 失败则跳过)
    bs = get_bertscore()
    if bs:
        try:
            from bert_score import score as bs_score

            refs = [norm_text(r) for r, _ in valid]
            hyps = [norm_text(h) for _, h in valid]
            P, R, F = bs_score(hyps, refs, lang="zh", verbose=False)
            result["bertscore_f1_mean"] = round(F.mean().item(), 4)
        except Exception as e:
            result["bertscore_note"] = f"BERTScore failed: {e}"
    else:
        result["bertscore_note"] = "torch/bert_score not installed, skipped"

    return result


# ============ 主入口 ============
def main():
    ap = argparse.ArgumentParser(description="ThoracicOnco-LLMBench Scorer")
    ap.add_argument("--predictions", required=True, help="模型输出 JSONL")
    ap.add_argument(
        "--benchmark",
        default=os.path.join(
            os.path.dirname(__file__), "..", "data", "benchmark.jsonl"
        ),
        help="benchmark.jsonl",
    )
    ap.add_argument("--output", default="results.json", help="输出结果 JSON")
    args = ap.parse_args()

    bench = [json.loads(l) for l in open(args.benchmark, encoding="utf-8")]
    preds = {}
    for line in open(args.predictions, encoding="utf-8"):
        d = json.loads(line)
        preds[d["id"]] = d

    # 按任务分组
    by_task = defaultdict(list)
    for inst in bench:
        by_task[inst["task"]].append(inst)

    results = {
        "benchmark": "ThoracicOnco-LLMBench v1.0",
        "n_benchmark": len(bench),
        "n_predictions": len(preds),
        "coverage": round(len([i for i in bench if i["id"] in preds]) / len(bench), 4),
    }

    # T1
    t1_insts = by_task.get("change_assessment", [])
    results["T1_change_assessment"] = score_t1(t1_insts, preds)

    # T2/T3/T4 单次 (T3 只对有 pTNM 的子集, T4 只对有 impression 参考的子集)
    t234_insts = by_task.get("structured_extraction_and_clinical_reasoning", [])
    results["T3_tnm_staging"] = score_t3(t234_insts, preds)
    results["T4_impression_generation"] = score_t4(
        t234_insts + by_task.get("impression_generation_no_reference", []), preds
    )

    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(results, f, ensure_ascii=False, indent=2)

    print(json.dumps(results, ensure_ascii=False, indent=2))
    print(f"\n结果已写入 {args.output}")


if __name__ == "__main__":
    main()
