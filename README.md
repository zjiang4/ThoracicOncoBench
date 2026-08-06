# ThoracicOncoBench

A benchmark for evaluating large language models on longitudinal thoracic oncologic imaging report interpretation.

## Overview

ThoracicOncoBench is a pathology-anchored benchmark constructed from 17,355 consecutive chest CT reports (9,334 patients, 2015–2024) at a National Cancer Center, linked to a prospectively maintained oncology outcomes registry with surgical pathology and survival data. It evaluates 15 large language models across four task families using hospital-validated reference standards — no additional annotation required.

## Key Findings

- All 15 models missed **27%–49%** of true disease progressions
- T-category staging accuracy was only **0.5%–43.2%** despite explicit textual descriptions
- Fatal error rates (progression judged as stable) ranged from **10.6% to 18.3%**
- **No model was uniformly superior** across all tasks
- Medical-specialized models did **not** consistently outperform general-purpose models

## Benchmark Structure

| Task | N | Input | Output | Gold Standard |
|------|---|-------|--------|---------------|
| T1: Change Assessment | 800 | Paired findings (prior + current) | Change category + metastasis flag | Negation-aware extraction from radiologist descriptors |
| T2/T3: Extraction & Staging | 1,095 | Single findings text | Structured JSON + cTNM | Pathology-confirmed pTNM (n=213 temporally aligned) |
| T4: Impression Generation | 100 | Findings without impression | Free-text impression | Pathology + survival outcomes |

## Quick Start

```bash
# 1. Run your model on the benchmark
python examples/infer_example.py --endpoint nvidia --model your-model --out my_predictions.jsonl

# 2. Score your predictions
python scorer/scorer.py --predictions my_predictions.jsonl --output my_results.json

# 3. View results
cat my_results.json
```

## Repository Contents

```
ThoracicOncoBench/
├── README.md                           # This file
├── data/
│   ├── benchmark.jsonl                 # Full benchmark: 1,995 instances
│   └── benchmark_sample_en.jsonl       # 15-case English-described sample
├── scorer/
│   └── scorer.py                       # Frozen evaluation script
├── examples/
│   └── infer_example.py                # Reference inference script (OpenAI-compatible API)
├── results/
│   ├── table1_overall_ranking.csv      # 15-model performance ranking
│   ├── table2_t1_per_class.csv         # T1 per-class precision/recall
│   ├── table3_t3_components.csv        # T3 T/N/M component accuracy
│   ├── table4_t4_impression.csv        # T4 ROUGE-L and char-F1
│   ├── table5_fatal_errors.csv         # Fatal error analysis
│   └── tableA_confusion_matrices.json  # Full confusion matrices
└── figures/
    ├── figure1_study_design.png        # Study flow chart
    ├── figure2_confusion_matrices.png   # T1 confusion matrices (4 models)
    ├── figure3_tnm_bar.png             # TNM per-component grouped bar chart
    ├── figure4_tradeoff_scatter.png     # Sensitivity-specificity scatter
    └── figure5_fatal_bar.png           # Fatal error stacked bar chart
```

## Evaluated Models (15)

| Category | Models |
|----------|--------|
| Frontier | GPT-5.4, Gemini-3.5-flash, Baichuan-M3 |
| General | Nemotron-3-Ultra, Qwen3.5-397B, DiffusionGemma-26B, Step-3.7-flash, DeepSeek-V4, Minimax-M2.7 |
| Medical-specialized | MedSeek, HuatuoGPT, AntAngelMed, MediPhi, MediX, QwQ-Med-3 |

## Evaluation Metrics

| Metric | Task | Description |
|--------|------|-------------|
| Macro-F1 | T1 | Macro-averaged F1 across 4 change categories |
| Progression Recall | T1 | Fraction of true progressions correctly identified |
| Fatal Error Rate | T1 | Fraction of progression cases judged "stable" (with 95% Wilson CI) |
| Exact-Match | T3 | All three TNM components correct |
| Per-Component Accuracy | T3 | Individual T, N, M accuracy vs pathology pTNM |
| ROUGE-L F1 | T4 | Lexical similarity to radiologist impression |

## Data Format

Each benchmark instance is a JSON object. See `data/benchmark_sample_en.jsonl` for annotated examples with English task descriptions.

## License

MIT License. The benchmark data contains de-identified patient information. Users must comply with applicable data protection regulations.

## Citation

```
[To be added upon publication]
```
