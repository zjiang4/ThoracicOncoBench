# Schema (engine v0.4.0)

## `reports_deidentified.jsonl`

One de-identified report per line.

- `report_id`: salted hash report identifier
- `patient_id`: salted hash patient identifier
- `source_file`, `exam_type`, `exam_subtype`: source metadata
- `report_index`: chronological index within the patient
- `days_from_first`: days since the patient's first report, or null
- `report_year`
- `findings`: de-identified findings text
- `impression`: de-identified final impression text
- `flags`: `has_findings`, `has_impression`, `explicit_comparison`, `measurement_present`

## `longitudinal_change_instances.jsonl` / `longitudinal_change_primary.jsonl`

One paired-report instance per line. The primary file is the subset with `task == "longitudinal_change_primary"`.

Top-level fields:

- `instance_id`, `task`, `split`, `patient_id`
- `current_report_id`, `prior_report_id`, `current_report_index`, `prior_report_index`
- `interval_days` (strictly positive)
- `input`, `label`, `provenance`

Task values: `longitudinal_change_primary`, `longitudinal_change_secondary`, `longitudinal_change_indeterminate`.

Input object (variant `findings_only_v1` — impressions are reserved as the reference source and must not be given to evaluated models):

- `variant`: "findings_only_v1"
- `prior_report.findings`, `prior_report.days_from_first`
- `current_report.findings`, `current_report.days_from_first`
- `question`

Label object:

- `change`: progression | regression | stable | mixed | indeterminate
- `new_metastatic_disease`: boolean
- `confidence`: high | standard | low
- `primary_eligible`: boolean
- `evidence_tier`: definitive | quantitative | directional | suspicious | weak | indeterminate
- `primary_rule`: main protocol rule responsible for the label
- `protocol_rule_ids`: all protocol and quality rules fired

Provenance object:

- `reference_source`, `labeling_protocol`, `parser_version`
- `primary_rule_description`
- `flags`: explicit_comparison, impression_present, impression_conclusion, uncertainty_language, postoperative_language, inflammatory_language, measurement_present, met_suspicious, findings_explicit_change_language
- `impression_conclusion`: list of {sentence, progression, regression, stable, uncertain} — the impression sentences used as the authoritative conclusion
- `triggers`: list of {category, section, sentence, term, strength}
- `metastasis_triggers`: list of {term, section, sentence, negated, uncertain, new_or_progressing, definitive}
- `measurement_evidence`: list of {section, sentence, prior_mm, current_mm, absolute_change_mm, relative_change, direction, rule_id}

## `impression_generation_instances.jsonl`

- `instance_id`, `task`, `split`, `patient_id`, `report_id`, `report_index`
- `input.findings`, `input.question`
- `label.reference_impression`, `label.reference_source`

## English browser companion files

These files support the standalone bilingual browser and are not alternate
benchmark labels or model-evaluation outputs.

The English fields are model-assisted medical-English translations with
automated consistency checks. They are provided for access and inspection,
not as independently human-certified translations, and do not alter the
Chinese source records or report-derived reference labels.

`reports_english.jsonl`:

- `report_id`: joins to `reports_deidentified.jsonl`
- `findings_en`: English rendering of the complete report findings
- `impression_en`: English rendering of the radiologist-authored final impression

`evidence_english.jsonl`:

- `source_id`: stable hash of the Chinese evidence phrase
- `source_text`: source phrase used for the browser join
- `text_en`: English rendering used in auditable provenance views

## `label_rule_summary.json`

Rule visibility summary: parser version, protocol rule dictionary, primary-rule counts by label and task, label counts by evidence tier, metastasis-positive primary count.

## `protocol/rules.json`

Machine-readable rule dictionary with the clinical basis (RECIST 1.1, iRECIST, institutional dual-audit impression priority).

## Prediction Schema

Nested:

```json
{"instance_id":"inst_xxx","prediction":{"change":"progression","new_metastatic_disease":true}}
```

Flat (also accepted):

```json
{"instance_id":"inst_xxx","change":"progression","new_metastatic_disease":true}
```

## Scoring Command

```bash
python scripts/evaluate_predictions.py --predictions predictions.jsonl
python scripts/evaluate_predictions.py --instances data/longitudinal_change_primary.jsonl --predictions predictions.jsonl --split test
python scripts/evaluate_predictions.py --instances data/longitudinal_change_instances.jsonl --task longitudinal_change_secondary --predictions predictions.jsonl
python scripts/evaluate_predictions.py --instances data/longitudinal_change_primary.jsonl --predictions predictions.jsonl --bootstrap 1000
```

Defaults: instances `data/longitudinal_change_primary.jsonl`, split `all`, no task filter. Intention-to-evaluate: missing/invalid predictions are scored as incorrect. Reported endpoints include progression recall, fatal stable error, progression-judged-regression, combined high-consequence undercall rate, false progression rate, metastasis recall/false-positive, probable-metastasis flagging rate (Wilson CIs), and optional patient-clustered bootstrap CIs.

## Audit Command

```bash
python scripts/audit_labels.py --instances data/longitudinal_change_primary.jsonl --reports data/reports_deidentified.jsonl --output-dir audit
```

Outputs `audit/audit_report.json` (checks C1-C10, distributions, threshold-vs-impression concordance analysis, no-change-language subset), the blinded adjudication package (`adjudication_blinded.csv` randomized without engine labels, `adjudication_template.csv` fill-in file, `adjudication_analysis_key.csv` private join key, `ADJUDICATION_GUIDE.md`), and `adjudication_sample.jsonl` (auditor-facing combined view). Analysis of the filled package: `python scripts/agreement_stats.py --filled audit/adjudication_template.csv --key audit/adjudication_analysis_key.csv`.
