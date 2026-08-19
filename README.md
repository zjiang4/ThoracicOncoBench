# ThoracicOncoBench

ThoracicOncoBench is a clinically anchored benchmark for evaluating large language models on longitudinal thoracic-oncology CT-report interpretation.

## What Is Included

- `data/benchmark_sample_en.jsonl`: small English-format example for reproducing the input/output schema.
- `scorer/scorer.py`: frozen scoring implementation used for the released benchmark outputs.
- `results/`: aggregate model-level results for the 0820 analysis package.
- `figures/`: five figures regenerated from the 0820 files with intention-to-evaluate scoring.
- `docs/0820_reproducibility.md`: task definitions, reference-standard provenance, scoring rules, and limitations.
- `examples/infer_example.py`: minimal inference example.

The complete manuscript is intentionally not stored in this repository. This repository contains the essential project assets needed to understand, reproduce, and audit the benchmark.

## Clinical Reference Standards

The benchmark was assembled at Peking University Cancer Hospital, a national-level tertiary oncology institution. Reports and benchmark reference answers were generated within the hospital's clinical workflow and underwent 2-radiologist verification or a documented second audit. The benchmark contains 800 longitudinal change-assessment pairs, 1,095 structured extraction/staging reports, and 100 impression-generation cases. Pathology-linked TNM concordance was evaluated on 213 temporally aligned cases.

Pathology-confirmed pTNM reflects the AJCC edition used during clinical care: AJCC 7 through December 2017 and AJCC 8 from January 2018 onward. No retrospective restaging was performed.

## 0820 Headline Results

- T1 accuracy: 63.75%–77.625%; macro-F1: 0.526–0.658.
- T1 progression recall: 50.96%–73.08%.
- Progression-to-stable errors: 10.58%–18.27% of 104 progression cases.
- Exact-match clinical-to-pathologic TNM concordance: 0.47%–25.82%.
- Component concordance: T 0.47%–43.19%, N 4.69%–67.61%, M 0.94%–75.12%.

For metastasis-positive pairs, the reported endpoint is the proportion of dual-verified cases with documented new metastasis whose T1 longitudinal change label was not `progression`. This is an endpoint within the T1 task, not a separate binary metastasis-classification task.

## Reproducibility Notes

All 15 models were evaluated once with temperature 0.6, top_p 0.95, prompt version `v1 (infer_v2.py)`, and API seeds not controlled. Parse failures and schema-invalid outputs were counted as incorrect in the primary intention-to-evaluate analysis.

## License

See `LICENSE` for terms. Patient-level source data are not included in this public repository.
