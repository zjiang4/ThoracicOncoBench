"""Release checks for the English-default standalone data browser."""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
from pathlib import Path


CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")


def load_builder(path: Path):
    spec = importlib.util.spec_from_file_location("data_browser_builder", path)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def walk_english(value, path: str, failures: list[dict]) -> None:
    if isinstance(value, dict):
        for key, item in value.items():
            walk_english(item, f"{path}.{key}", failures)
    elif isinstance(value, list):
        for index, item in enumerate(value):
            walk_english(item, f"{path}[{index}]", failures)
    elif isinstance(value, str) and CJK_RE.search(value):
        failures.append({"path": path, "value": value[:240]})


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--benchmark-dir", type=Path, required=True)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    builder = load_builder(args.benchmark_dir / "scripts" / "build_data_browser.py")
    data = builder.payload(args.benchmark_dir / "data")
    failures = []

    for patient in data["patients"]:
        for report in patient["reports"]:
            if not report["findings_en"].strip():
                failures.append({"path": f"{report['report_id']}.findings_en", "value": "empty"})
            walk_english(report["findings_en"], f"{report['report_id']}.findings_en", failures)
            walk_english(report["impression_en"], f"{report['report_id']}.impression_en", failures)
        for instance in patient["longitudinal"]:
            walk_english(instance["question_en"], f"{instance['instance_id']}.question_en", failures)
            walk_english(instance["provenance_en"], f"{instance['instance_id']}.provenance_en", failures)
        for instance in patient["impressions"]:
            walk_english(instance["question_en"], f"{instance['instance_id']}.question_en", failures)
            walk_english(instance["answer_en"], f"{instance['instance_id']}.answer_en", failures)

    html_path = args.benchmark_dir / "benchmark_data_browser.html"
    html = html_path.read_text(encoding="utf-8") if html_path.exists() else ""
    required_html = [
        '<html lang="en">',
        'let lang="en"',
        '>All tasks</option>',
        '>All reference answers</option>',
        '>English</button>',
        '>Expand all</button>',
    ]
    missing_html_markers = [marker for marker in required_html if marker not in html]
    result = {
        "patients": data["meta"]["patient_count"],
        "reports": data["meta"]["report_count"],
        "translated_reports": data["meta"]["translated_report_count"],
        "translated_evidence_phrases": data["meta"]["translated_evidence_count"],
        "english_field_failures": failures[:100],
        "english_field_failure_count": len(failures),
        "missing_html_markers": missing_html_markers,
    }
    if args.output:
        args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(result, ensure_ascii=False))
    if failures or missing_html_markers:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
