# ThoracicOncoBench Clean Release v0.4.0

Release date: 2026-09-06

This directory is the clean, self-contained benchmark release for the manuscript.
It uses the conservative v0.4.0 report-derived label protocol. External model
evaluations are stored in a separate sibling directory and are not part of the
benchmark package.

## Included

- v0.4.0 benchmark data and de-identified reports
- deterministic label engine, builder, evaluator, audit scripts, and tests
- standalone `benchmark_data_browser.html` with patient grouping, expandable records,
  visible reference answers, and complete English-default/Chinese-switchable clinical text
- provider-neutral English report and evidence translation files used by the browser
- automated English-translation release audit; the English layer is model-assisted,
  is not independently human-certified, and is not used to derive reference labels
- RECIST 1.1/iRECIST-informed protocol and data card
- zero-violation release audit and 100/100 perturbation report
- `comparisons/majority_stable_primary_predictions_v04.jsonl`: current majority baseline

## Primary reference set

- 1,968 primary instances
- stable 1,639
- progression 158
- regression 148
- mixed 23
- new-metastatic-disease positive 78

## Excluded by design

- exposed API keys or credentials
- raw clinical identifiers and absolute dates
- the obsolete v0.3 primary dataset as a reference set

The audit command may additionally generate optional blinded adjudication files
under `audit/`; those files are not required for benchmark scoring and should be
removed before any public release if external adjudication is not part of the
manuscript.

For public distribution, set a private `THORACIC_BENCH_SALT` before rebuilding
identifiers and do not publish that salt.
