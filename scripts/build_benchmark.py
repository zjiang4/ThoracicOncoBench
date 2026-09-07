"""ThoracicOncoBench benchmark builder v0.4.0.

Rebuilds longitudinal-change and impression-generation instances from
de-identified report records using label_engine v0.4.0.

Usage:
  python scripts/build_benchmark.py --input-dir benchmark_fix/data --output-dir benchmark_fix
"""

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from label_engine import PARSER_VERSION, RULE_ANCHORS, RULE_DESCRIPTIONS, label_pair

BUILDER_VERSION = "v0.4.0"

LONGITUDINAL_QUESTION = (
    "You are given the findings sections of two consecutive chest CT reports from the same patient. "
    "Classify the overall tumor-burden-related longitudinal change documented in the current findings relative to the prior "
    "findings as progression, regression, stable, mixed, or indeterminate, and state whether new "
    "metastatic disease is documented."
)
IMPRESSION_QUESTION = "Generate the radiology impression from the chest CT findings."


def _hash_id(text):
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def _split_for(patient_id):
    n = int(hashlib.md5(patient_id.encode("utf-8")).hexdigest()[:8], 16) % 100
    if n < 70:
        return "train"
    if n < 85:
        return "validation"
    return "test"


def load_reports(input_dir):
    reports = []
    with open(input_dir / "reports_deidentified.jsonl", encoding="utf-8") as f:
        for line in f:
            reports.append(json.loads(line))
    return reports


def build_longitudinal(reports):
    by_patient = defaultdict(list)
    for r in reports:
        by_patient[r["patient_id"]].append(r)
    for p in by_patient:
        by_patient[p].sort(key=lambda r: (r["report_index"], r.get("days_from_first") or 0))

    instances, dropped_nonpositive_interval = [], 0
    for pid, rlist in by_patient.items():
        for prior, current in zip(rlist, rlist[1:]):
            interval = (current.get("days_from_first") or 0) - (prior.get("days_from_first") or 0)
            if interval <= 0:
                dropped_nonpositive_interval += 1
                continue
            res = label_pair(prior.get("findings") or "", current.get("findings") or "",
                             current.get("impression") or "", current.get("flags") or {})
            if res.primary_eligible:
                task = "longitudinal_change_primary"
            elif res.change == "indeterminate":
                task = "longitudinal_change_indeterminate"
            else:
                task = "longitudinal_change_secondary"
            inst = {
                "instance_id": "inst_" + _hash_id(f"{pid}|{prior['report_id']}|{current['report_id']}"),
                "task": task,
                "split": _split_for(pid),
                "patient_id": pid,
                "prior_report_id": prior["report_id"],
                "current_report_id": current["report_id"],
                "prior_report_index": prior["report_index"],
                "current_report_index": current["report_index"],
                "interval_days": interval,
                "input": {
                    "variant": "findings_only_v1",
                    "prior_report": {"findings": prior.get("findings") or "",
                                     "days_from_first": prior.get("days_from_first")},
                    "current_report": {"findings": current.get("findings") or "",
                                       "days_from_first": current.get("days_from_first")},
                    "question": LONGITUDINAL_QUESTION,
                },
                "label": {
                    "change": res.change,
                    "new_metastatic_disease": res.new_metastatic_disease,
                    "confidence": res.confidence,
                    "primary_eligible": res.primary_eligible,
                    "evidence_tier": res.evidence_tier,
                    "primary_rule": res.primary_rule,
                    "protocol_rule_ids": res.protocol_rule_ids,
                },
                "provenance": {
                    "reference_source": "dual-audited finalized radiology report (oncologic-scope protocol v0.4.0)",
                    "labeling_protocol": "RECIST 1.1/iRECIST-informed conservative deterministic engine with oncologic-scope and conflict gating",
                    "parser_version": PARSER_VERSION,
                    "primary_rule_description": RULE_DESCRIPTIONS.get(res.primary_rule, ""),
                    "flags": res.flags,
                    "triggers": res.triggers,
                    "metastasis_triggers": res.metastasis_triggers,
                    "measurement_evidence": res.measurement_evidence,
                    "impression_conclusion": res.impression_conclusion,
                },
            }
            instances.append(inst)
    return instances, dropped_nonpositive_interval


def build_impression(reports):
    instances = []
    for r in reports:
        if not (r.get("flags") or {}).get("has_findings"):
            continue
        if not (r.get("flags") or {}).get("has_impression"):
            continue
        instances.append({
            "instance_id": "inst_" + _hash_id(f"imp|{r['report_id']}"),
            "task": "impression_generation",
            "split": _split_for(r["patient_id"]),
            "patient_id": r["patient_id"],
            "report_id": r["report_id"],
            "report_index": r["report_index"],
            "input": {
                "findings": r.get("findings") or "",
                "question": IMPRESSION_QUESTION,
            },
            "label": {
                "reference_impression": r.get("impression") or "",
                "reference_source": "radiologist_authored_final_impression",
            },
            "provenance": {
                "reference_source": "finalized_radiology_report",
                "parser_version": PARSER_VERSION,
                "flags": r.get("flags") or {},
            },
        })
    return instances


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--input-dir", default="data")
    ap.add_argument("--output-dir", default=".")
    args = ap.parse_args()
    input_dir, out_dir = Path(args.input_dir), Path(args.output_dir)
    data_dir = out_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    reports = load_reports(input_dir)
    long_instances, dropped = build_longitudinal(reports)
    imp_instances = build_impression(reports)

    primary = [i for i in long_instances if i["task"] == "longitudinal_change_primary"]

    def dump(path, rows):
        with open(path, "w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")

    dump(data_dir / "longitudinal_change_instances.jsonl", long_instances)
    dump(data_dir / "longitudinal_change_primary.jsonl", primary)
    dump(data_dir / "impression_generation_instances.jsonl", imp_instances)

    baseline_dir = out_dir / "baselines"
    baseline_dir.mkdir(parents=True, exist_ok=True)
    with open(baseline_dir / "majority_stable_primary_predictions.jsonl", "w", encoding="utf-8") as f:
        for i in primary:
            f.write(json.dumps({"instance_id": i["instance_id"],
                                "prediction": {"change": "stable", "new_metastatic_disease": False}},
                               ensure_ascii=False) + "\n")

    protocol_dir = out_dir / "protocol"
    protocol_dir.mkdir(parents=True, exist_ok=True)
    with open(protocol_dir / "rules.json", "w", encoding="utf-8") as f:
        json.dump({
            "parser_version": PARSER_VERSION,
            "clinical_basis": [
                "RECIST 1.1 (Eisenhauer et al., Eur J Cancer 2009): new lesion = progressive disease; >=20% + >=5 mm increase = progression; >=30% decrease = regression.",
                "iRECIST (Seymour et al., Lancet Oncol 2017): only unequivocal new/progressive disease counts; equivocal statements are downgraded.",
                "Institutional dual-audit reporting workflow: finalized impression is the authoritative radiologist synthesis; explicit conflicting findings are retained as indeterminate rather than silently discarded.",
                "Oncologic-scope gate: non-oncologic interval changes (effusion, pneumothorax, atelectasis, infection, fibrosis, postoperative change) cannot independently define tumor response.",
            ],
            "rules": RULE_DESCRIPTIONS,
            "rule_anchors": RULE_ANCHORS,
        }, f, ensure_ascii=False, indent=2)

    tier_counts = Counter(i["label"]["evidence_tier"] for i in long_instances)
    label_all = Counter(i["label"]["change"] for i in long_instances)
    label_primary = Counter(i["label"]["change"] for i in primary)
    primary_rule_counts = Counter(i["label"]["primary_rule"] for i in long_instances)
    rule_counts = Counter(rid for i in long_instances for rid in i["label"]["protocol_rule_ids"])
    task_counts = Counter(i["task"] for i in long_instances)
    split_counts = Counter(i["split"] for i in long_instances)
    primary_split = Counter(i["split"] for i in primary)
    met_primary = Counter(i["label"]["new_metastatic_disease"] for i in primary)

    summary = {
        "parser_version": PARSER_VERSION,
        "label_counts_by_evidence_tier": {
            t: dict(Counter(i["label"]["change"] for i in long_instances if i["label"]["evidence_tier"] == t))
            for t in sorted(tier_counts)
        },
        "primary_rule_counts_by_label": {
            lab: dict(Counter(i["label"]["primary_rule"] for i in long_instances if i["label"]["change"] == lab))
            for lab in sorted(label_all)
        },
        "primary_rule_counts_by_task": {
            t: dict(Counter(i["label"]["primary_rule"] for i in long_instances if i["task"] == t))
            for t in sorted(task_counts)
        },
        "protocol_rules": RULE_DESCRIPTIONS,
        "metastasis_positive_primary": dict(met_primary),
    }
    with open(out_dir / "label_rule_summary.json", "w", encoding="utf-8") as f:
        json.dump(summary, f, ensure_ascii=False, indent=2)

    manifest = {
        "builder_version": BUILDER_VERSION,
        "parser_version": PARSER_VERSION,
        "created_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "input_variant": "findings_only_v1",
        "input_variant_note": "Model input contains findings sections only; the dual-audited impression is reserved as the reference-standard source and must not be fed to evaluated models.",
        "clinical_basis": [
            "RECIST 1.1 (Eisenhauer et al., Eur J Cancer 2009)",
            "iRECIST (Seymour et al., Lancet Oncol 2017)",
            "Institutional dual-audit reporting workflow (impression priority)",
            "Oncologic-scope gate for malignant disease burden",
        ],
        "consistency_constraints": [
            "new_metastatic_disease=true requires label in {progression, mixed}",
            "stable impression plus explicit oncologic findings change is labeled indeterminate/conflict",
            "non-oncologic changes cannot independently define progression/regression",
            "definitive new-metastasis evidence vs stable impression => indeterminate (excluded from primary)",
        ],
        "longitudinal_change": {
            "total_instances": len(long_instances),
            "dropped_nonpositive_interval_pairs": dropped,
            "task_counts": dict(task_counts),
            "evidence_tier_counts": dict(tier_counts),
            "label_counts_all": dict(label_all),
            "primary_instances": len(primary),
            "primary_label_counts": dict(label_primary),
            "primary_split_counts": dict(primary_split),
            "primary_metastasis_positive": dict(met_primary),
            "split_counts": dict(split_counts),
            "primary_rule_counts": dict(primary_rule_counts),
            "protocol_rule_counts": dict(rule_counts),
            "measurement_evidence_count": sum(1 for i in long_instances if i["provenance"]["measurement_evidence"]),
            "primary_measurement_evidence_count": sum(1 for i in primary if i["provenance"]["measurement_evidence"]),
        },
        "impression_generation": {
            "total_instances": len(imp_instances),
            "split_counts": dict(Counter(i["split"] for i in imp_instances)),
        },
        "source": {
            "report_count": len(reports),
            "patient_count": len({r["patient_id"] for r in reports}),
            "reports_with_impression": sum(1 for r in reports if (r.get("flags") or {}).get("has_impression")),
            "reports_with_explicit_comparison": sum(1 for r in reports if (r.get("flags") or {}).get("explicit_comparison")),
        },
        "split_method": "deterministic md5(patient_id) mod 100: <70 train, <85 validation, else test",
        "release_notes": [
            "Labels are impression-priority, RECIST 1.1-informed, protocol-concordant report-derived labels, not image-level gold standards.",
            "v0.4.0 adds cm/厘米 normalization, stable-impression conflict quarantine, and conservative handling of generic new nodules and slight/follow-up-qualified changes; v0.3.0 safeguards remain active.",
            "Model input is findings-only; impressions are reserved as the reference source.",
            "Patient and report identifiers are hashed; absolute dates in report text are redacted.",
            "Set THORACIC_BENCH_SALT to a private value before creating a public release build.",
        ],
    }
    with open(out_dir / "manifest.json", "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=2)

    print(json.dumps({
        "reports": len(reports),
        "longitudinal_instances": len(long_instances),
        "primary": len(primary),
        "primary_labels": dict(label_primary),
        "primary_met_pos": dict(met_primary),
        "dropped_nonpositive_interval": dropped,
        "impression_instances": len(imp_instances),
    }, ensure_ascii=False))


if __name__ == "__main__":
    main()
