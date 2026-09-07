# ThoracicOncoBench

ThoracicOncoBench is a protocolized, clinically anchored benchmark for evaluating large language models on longitudinal thoracic oncology CT report reasoning.

The benchmark is built from finalized chest CT radiology reports produced under the dual-audit workflow of Peking University Cancer Hospital (preliminary report by trainee/attending, senior-radiologist approval before finalization). It evaluates whether models can reproduce the clinically consequential longitudinal conclusions already documented in radiology reports.

ThoracicOncoBench is not an image-level diagnostic benchmark. It does not ask models to interpret CT images. It asks models to reason over finalized report text.

## Current Release (engine v0.4.0)

Open `benchmark_data_browser.html` to browse the complete de-identified dataset
without a server. The standalone page groups records by patient id and defaults
to publication-quality English throughout the interface, report findings,
radiology impressions, questions, reference answers, and auditable provenance.
The original Chinese source text remains available through the language toggle.

The English companion text was produced by model-assisted medical-English
translation with automated consistency checks for completeness, residual CJK
text, measurements and image references, negation, diagnostic uncertainty,
follow-up language, and empty-source invariants. It is a browser presentation
layer only and was not used to derive benchmark labels. It should not be
described as independently human-certified translation.

`data/`:

- `reports_deidentified.jsonl`: de-identified finalized report records (source corpus).
- `reports_english.jsonl`: English report findings and impressions keyed by report id.
- `evidence_english.jsonl`: English renderings of Chinese provenance/evidence phrases.
- `longitudinal_change_instances.jsonl`: all paired-report instances (primary + secondary + indeterminate).
- `longitudinal_change_primary.jsonl`: high-confidence primary longitudinal-change instances.
- `impression_generation_instances.jsonl`: findings-to-impression generation instances.

Root:

- `manifest.json`: build statistics, clinical basis, consistency constraints, split method.
- `label_rule_summary.json`: rule and tier counts across the build.
- `protocol/rules.json`: machine-readable rule dictionary with clinical-basis citations.
- `SCHEMA.md`, `LABEL_PROTOCOL.md`, `DATA_CARD.md`: schema, labeling protocol, dataset documentation.
- `benchmark_data_browser.html`: standalone clickable bilingual data browser.
- `audit/`: release audit report and radiologist adjudication sample (see below).

The current build (findings-only input variant):

- 17,535 de-identified chest CT reports, 9,334 patients.
- 8,011 longitudinal paired-report instances (190 non-positive-interval pairs dropped).
  - 1,968 primary: stable 1,639 / regression 148 / progression 158 / mixed 23; 78 metastasis-positive.
  - 4,744 secondary and 1,299 indeterminate retained for uncertainty research.
- 11,999 impression-generation instances.

## Task 1: Longitudinal Change Assessment

Input (findings only — the dual-audited impression is reserved as the reference source and must never be given to evaluated models):

- prior report findings
- current report findings
- days from the patient's first report for both

Output:

- `change`: progression | regression | stable | mixed | indeterminate
- `new_metastatic_disease`: boolean

Labels follow the impression-priority, RECIST 1.1-informed, iRECIST-conservative protocol defined in `LABEL_PROTOCOL.md`. Progression/regression are scoped to malignant disease burden; effusion, pneumothorax, atelectasis, infection, fibrosis, and postoperative change are retained as confounders but cannot independently define tumor response. Every instance exposes full provenance: the impression sentences used as the conclusion, all trigger sentences and terms with strength, metastasis trigger status, and RECIST-informed measurement evidence including axis and uncertainty flags.

## Task 2: Impression Generation

Input: report findings. Output: the radiologist-authored final impression. This evaluates report-level summarization against the dual-audited clinical impression.

## Label Philosophy and Validity

The finalized radiology report is the clinical source document, and its impression is the audited final synthesis of the reporting radiologist — adjudicated prospectively by the institutional dual-audit workflow at the time of care. The deterministic engine transcribes these adjudicated conclusions under a prespecified protocol with hard consistency constraints verified at build time. **No additional human annotation is performed or required.**

Label validity rests on five pillars (see `LABEL_PROTOCOL.md`, Validity Framework): prospectively adjudicated source documents; guideline anchoring of every rule (RECIST 1.1 / iRECIST / institutional impression priority, with per-rule citations at `protocol/rules.json`); implementation-fidelity testing (regression tests 28/28, perturbation fidelity 100/100); internal multi-channel convergence (90.4% of primary labels supported by >=2 concordant evidence channels); and full per-label auditability (provenance + open lexicon).

Safe manuscript phrasing:

> Reference labels were derived, without additional human annotation, by a deterministic protocol that transcribes prospectively adjudicated radiologist conclusions from dual-audited finalized reports, with rules anchored to RECIST 1.1 and iRECIST; engine fidelity and internal convergence statistics are reported in place of post-hoc annotation-based reliability.

An optional blinded two-radiologist adjudication package is exported in `audit/` for clinical collaborators or external auditors; release claims do not depend on it.

## Rebuilding

No third-party dependencies (Python 3.10+ standard library):

```bash
python scripts/build_benchmark.py --input-dir data --output-dir .
```

For a public release, set a private salt before building:

```bash
set THORACIC_BENCH_SALT=replace-with-private-release-salt
python scripts/build_benchmark.py --input-dir data --output-dir .
```

Do not publish the salt used with private institutional identifiers.

## Prediction Format

JSONL records (nested or flat both accepted):

```json
{"instance_id":"inst_xxx","prediction":{"change":"stable","new_metastatic_disease":false}}
```

## Evaluation

```bash
python scripts/evaluate_predictions.py --predictions path/to/predictions.jsonl
python scripts/evaluate_predictions.py --instances data/longitudinal_change_primary.jsonl --predictions path/to/predictions.jsonl --split test
python scripts/evaluate_predictions.py --instances data/longitudinal_change_primary.jsonl --predictions baselines/majority_stable_primary_predictions.jsonl
```

Metrics (intention-to-evaluate; missing/invalid predictions count as incorrect): accuracy, macro-F1, per-class precision/recall/F1, progression recall, fatal stable error (progression judged stable) and progression judged regression, combined high-consequence undercall rate, false progression rate, metastasis recall/false-positive, and probable-metastasis (met_suspicious) flagging rate — key rates with 95% Wilson CIs. `--bootstrap N` adds patient-level clustered bootstrap 95% CIs for headline metrics. `--task` allows scoring the secondary and indeterminate subsets as well. For impression generation, `scripts/evaluate_impression.py` reports ROUGE-L F1 and character-level F1.

Recommended evaluation protocol: use the full primary set as the primary analysis with patient-clustered bootstrap CIs (consecutive pairs share reports within a patient); report the test split as a reference number only — its progression subset is too small for inferential claims.

Majority-stable baseline on the current primary set: 78.6% accuracy (patient-bootstrap 95% CI 0.765-0.806), 0.220 macro-F1, 0% progression recall, 100% high-consequence undercall rate.

The benchmark release contains only the protocolized reference labels and
benchmark baselines. External model evaluations are maintained outside this
directory so that the benchmark package remains independent and clean.

## Release Audit and Radiologist Adjudication

Every release build must pass the deterministic audit (checks C1-C10: label-impression consistency, metastasis-label consistency, negated triggers, morphology false positives, interval positivity, input leakage, vocabulary, split disjointness, identifier uniqueness). The audit also computes the machine-only validity statistics: the RECIST-informed single-lesion threshold vs impression-conclusion concordance (78.9% exact agreement on 215 instances carrying directional measurements), the multi-channel convergence analysis (90.4% of primary labels with >=2 concordant evidence channels), and the count of primary instances whose findings lack explicit change language (130; a natural reading-inference challenge subset):

```bash
python scripts/audit_labels.py --instances data/longitudinal_change_primary.jsonl --reports data/reports_deidentified.jsonl --output-dir audit
python scripts/perturbation_tests.py --instances data/longitudinal_change_primary.jsonl --output audit/perturbation_report.json
```

The perturbation suite is the differential-validity test of the protocol implementation: 100 real corpus sentences are negated, hedged, comparative-marker-stripped, or measurement-role-swapped, and the engine must respond as RECIST 1.1/iRECIST semantics prescribe (current: 100/100).

An optional blinded adjudication package (328 cases; randomized order, engine labels withheld: `adjudication_blinded.csv` + `ADJUDICATION_GUIDE.md`, fill-in `adjudication_template.csv`, private join key `adjudication_analysis_key.csv`) is exported for clinical collaborators or external auditors. If used, `python scripts/agreement_stats.py --filled audit/adjudication_template.csv --key audit/adjudication_analysis_key.csv` reports inter-radiologist agreement/kappa, engine-vs-adjudicated agreement per class and within the postoperative stratum, and the engine-error instance list. The current build passes all checks with zero violations.

## Regression Tests

```bash
python tests/test_engine.py
```

Locks expected engine behavior for ten known-issue instances from the superseded v0.1 build, twelve measurement-extraction cases (role-aware prior/current assignment, long/short-axis diameters, thresholds), and four oncologic-scope guard cases.

## Release Caution

The generated benchmark is de-identified by hashing patient/report identifiers and redacting absolute dates, long numbers, and phone-number-like strings in report text. Before public distribution, perform institutional privacy review and rebuild with a private salt. Full report text may remain controlled-access clinical text depending on local governance; a public release can include schema, code, manifest statistics, scorer, predictions, and a small reviewed sample while keeping full text under a data-use agreement.
