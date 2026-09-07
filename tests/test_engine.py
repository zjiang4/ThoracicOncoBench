"""Regression tests for label_engine v0.2.x.

Cases lock the expected behavior for: (a) ten known-issue instances from the
superseded v0.1 build (impression-priority, adjectival false positives,
metastasis-flag consistency, uncertainty downgrade), and (b) twelve
RECIST-informed measurement-extraction cases (role-aware prior/current
assignment, long-axis diameters, thresholds).

Run: python tests/test_engine.py
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
from label_engine import _extract_measurements, label_pair, split_sentences

CASES = json.loads((Path(__file__).parent / "test_engine_cases.json").read_text(encoding="utf-8"))


def test_labels(fails):
    for c in CASES["label_cases"]:
        res = label_pair("", c["current_findings"], c["current_impression"])
        exp = c["expect"]
        got = {"change": res.change, "new_metastatic_disease": res.new_metastatic_disease,
               "evidence_tier": res.evidence_tier, "primary_eligible": res.primary_eligible}
        if got != exp:
            fails.append(f"LABEL {c['name']}: expect {exp}, got {got}")


def test_measurements(fails):
    for c in CASES["measurement_cases"]:
        got = _extract_measurements(split_sentences(c["sentence"]), "findings")
        if c["direction"] is None:
            if got:
                fails.append(f"MEAS {c['sentence'][:30]}: expect no pair, got {got}")
            continue
        if not got:
            fails.append(f"MEAS {c['sentence'][:30]}: expect {c['direction']}, got none")
            continue
        m = got[0]
        if (m["direction"] != c["direction"] or m["prior_mm"] != c["prior"]
                or m["current_mm"] != c["current"]):
            fails.append(f"MEAS {c['sentence'][:30]}: expect {c['direction']} "
                         f"{c['prior']}->{c['current']}, got {m['direction']} "
                         f"{m['prior_mm']}->{m['current_mm']}")

    small_node = _extract_measurements(
        split_sentences("纵隔淋巴结较前增大，原约6x4mm，现约14x8mm"), "findings")[0]
    if small_node["measurable_by_recist"]:
        fails.append("MEAS small node: <15 mm short axis incorrectly marked measurable")
    large_node = _extract_measurements(
        split_sentences("纵隔淋巴结较前增大，原约12x10mm，现约20x16mm"), "findings")[0]
    if not large_node["measurable_by_recist"] or large_node["measurement_axis"] != "short_axis":
        fails.append("MEAS large node: expected measurable short-axis node")


def test_non_oncologic_changes_do_not_become_progression(fails):
    cases = [
        ("右侧胸腔积液较前增多，右肺膨胀不全加重。", "progression"),
        ("双肺炎症较前加重，建议抗炎治疗后复查。", "progression"),
        ("左肺术后，局部肺不张较前增大。", "progression"),
    ]
    for findings, bad_label in cases:
        res = label_pair("", findings, "")
        if res.change == bad_label:
            fails.append(f"NON_ONC {findings}: non-oncologic change became {bad_label}")
        if res.change not in ("stable", "indeterminate"):
            fails.append(f"NON_ONC {findings}: unexpected label {res.change}")

    res = label_pair("", "左肺上叶肿块较前增大。", "")
    if res.change != "progression":
        fails.append(f"ONC positive control: expected progression, got {res.change}")


def test_v04_conservative_boundary_rules(fails):
    cases = [
        ("右肺新发约5mm结节，建议追查。", "", "progression", "suspicious", False),
        ("右肺占位较前略增大，建议复查。", "", "progression", "suspicious", False),
    ]
    for findings, impression, change, tier, primary in cases:
        res = label_pair("", findings, impression)
        if (res.change, res.evidence_tier, res.primary_eligible) != (change, tier, primary):
            fails.append(f"V04 boundary {findings}: got {(res.change, res.evidence_tier, res.primary_eligible)}")

    cm = _extract_measurements(split_sentences("病灶原约2.5x1.3cm，现约3.3x1.5cm"), "findings")
    if not cm or cm[0]["prior_mm"] != 25.0 or cm[0]["current_mm"] != 33.0:
        fails.append(f"V04 cm normalization failed: {cm}")

    conflict = label_pair("", "右肺结节较前增大，原约9x8mm，现约15x11mm。", "右肺多发小结节同前。")
    if (conflict.change, conflict.primary_rule, conflict.primary_eligible) != (
            "indeterminate", "QUALITY-INDETERMINATE-CONFLICT", False):
        fails.append(f"V04 stable-impression conflict failed: {conflict.change}, {conflict.primary_rule}")


def main():
    fails = []
    test_labels(fails)
    test_measurements(fails)
    test_non_oncologic_changes_do_not_become_progression(fails)
    test_v04_conservative_boundary_rules(fails)
    for f in fails:
        print("FAIL", f)
    total = len(CASES["label_cases"]) + len(CASES["measurement_cases"]) + 6
    print(f"{total - len(fails)}/{total} passed")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
