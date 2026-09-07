# Data Card

## Dataset Name

ThoracicOncoBench (engine v0.4.0)

## Intended Use

ThoracicOncoBench is intended for evaluating large language models on report-level thoracic oncology reasoning:

- longitudinal change assessment across paired chest CT reports (findings-only input)
- new metastatic disease flagging from report text
- radiology impression generation from findings text
- safety analysis using clinically meaningful error categories (fatal stable error, metastasis omission)

## Not Intended For

- image-level CT interpretation
- autonomous diagnostic or treatment decisions
- a replacement for radiologist or oncologist review
- claims that deterministic report extraction produces clinical ground truth

## Source Data

Institutional chest CT radiology reports from Peking University Cancer Hospital, produced under the institutional dual-audit workflow (trainee/attending preliminary report, senior-radiologist approval). The current build:

- 17,535 report records, 9,334 hashed patients, dated 2015-2024 in the source system
- findings text, final impression text when available, examination metadata

## Processed Benchmark Contents

- `data/reports_deidentified.jsonl`
- `data/longitudinal_change_instances.jsonl` (8,011: 1,968 primary / 4,744 secondary / 1,299 indeterminate)
- `data/longitudinal_change_primary.jsonl`
- `data/impression_generation_instances.jsonl` (11,999)
- `manifest.json`, `label_rule_summary.json`, `protocol/rules.json`
- `audit/audit_report.json`, `audit/adjudication_blinded.csv`, `audit/adjudication_template.csv`, `audit/adjudication_analysis_key.csv`, `audit/ADJUDICATION_GUIDE.md`
- `tests/test_engine.py` and `tests/test_engine_cases.json` (engine regression tests)

## De-Identification

- patient and report identifiers replaced with salted SHA-256 hashes
- absolute dates in report text replaced by `[DATE]`
- long numeric identifiers replaced by `[NUM]`
- phone-number-like strings replaced by `[PHONE]`
- relative timing preserved as `days_from_first` and `interval_days`

Rebuild with a private salt (`THORACIC_BENCH_SALT`) before public release; do not publish the salt.

## Label Construction

Longitudinal labels are produced by the impression-priority, RECIST 1.1-informed engine (`scripts/label_engine.py`), fully specified in `LABEL_PROTOCOL.md`:

1. The dual-audited final impression's explicit **oncologic** change conclusion is authoritative (impression priority); non-oncologic interval changes are not tumor response endpoints.
2. When the impression is silent, RECIST 1.1-informed thresholds apply to report-documented paired disease-target measurements (>=20% + >=5 mm increase; >=30% decrease), using long axis for non-nodal lesions and short axis for lymph nodes, then explicit comparative findings language (comparative co-text required; bare adjectives never count).
3. iRECIST-conservative handling: equivocal statements are downgraded out of the primary set.
4. Hard consistency constraints: metastasis-positive implies progression or mixed; a stable impression plus explicit disease-relevant findings change is quarantined as indeterminate/conflict; all pairs have positive intervals.

**No additional human annotation was performed.** Label validity rests on the five-pillar framework in `LABEL_PROTOCOL.md`: prospectively adjudicated source documents (institutional dual audit at report finalization), per-rule guideline anchoring (RECIST 1.1 / iRECIST, `protocol/rules.json` `rule_anchors`), implementation-fidelity testing (regression tests 28/28; perturbation fidelity 100/100), internal multi-channel convergence (90.4% of primary labels with >=2 concordant evidence channels), and full per-label provenance with an open lexicon. An optional blinded two-radiologist adjudication package (328 cases) is exported in `audit/` for external audit; release claims do not depend on it.

Every label carries full provenance (impression conclusion sentences, triggers with strength, metastasis trigger status, measurement evidence, rule ids). The build passes ten deterministic audit checks with zero violations (`audit/audit_report.json`).

Model input contains findings only. The impression is the reference-standard source and must never be given to evaluated models. The v0.4.0 scope gate also prevents non-oncologic changes (effusion, pneumothorax, atelectasis, infection, fibrosis, postoperative change) from independently defining tumor response; generic new nodules, slight changes, and stable-impression conflicts are retained outside the primary set.

## Reference Standard Language

Recommended: "impression-priority, RECIST 1.1-informed, protocol-concordant reference labels derived from dual-audited finalized radiology reports"

Avoid: "image-level gold standard", "algorithm-derived ground truth"

## Splits

Assigned deterministically at the hashed-patient level (md5 mod 100): 70% train / 15% validation / 15% test. No patient appears across splits. Model comparison should use the test split (345 primary instances) or the full primary set with the split stated.

## Known Limitations

- Report-derived evaluation: measures faithful reasoning over finalized report text, not image interpretation. About 99% of primary current-findings contain explicit comparison language, so the task is predominantly concordance with documented conclusions; the 130 instances lacking such language among the audited primary build (flag `findings_explicit_change_language: false`) form a natural reading-inference challenge subset.
- RECIST-informed, not RECIST-compliant: routine reports lack formal target-lesion sums and nadir measurements; quantitative evidence uses paired single-lesion measurements in sentences containing exactly one prior-marked and one current-marked measurement, with long-axis selection for non-nodal lesions and short-axis selection for lymph nodes (conservative pairing; multi-lesion sentences are skipped). Across 215 instances carrying directional measurements, the single-lesion threshold agrees with the overall report label in 78.9% of cases (see `audit/audit_report.json`).
- The engine's implementation fidelity is established by machine-only testing (unit regression, perturbation differential validity, build-time consistency checks) rather than by post-hoc human adjudication; per-label error rate is therefore not empirically quantified by annotators, which is disclosed as a design property of the no-annotation protocol. The optional blinded adjudication package can quantify it if external collaborators choose to run it.
- Consecutive report pairs share the middle report within a patient; use patient-clustered inference (the evaluator provides patient-level bootstrap CIs).
- The primary set excludes impression-silent, non-oncologic-only, or hedged cases by design (4,744 secondary + 1,299 indeterminate retained and evaluable via `--task`); the hardest clinical cases therefore sit outside the primary endpoint, and secondary-set performance should be reported alongside.
- The pathology/outcomes registry described in the legacy manuscript is not linkable to the current corpus (see `linkage/anzhen_linkage_check.json`); pathology-confirmed TNM staging is deferred until linkage is restored.
- The metastasis-positive primary subset (93) is small; metastasis endpoints carry wide confidence intervals, and the probable-metastasis (`met_suspicious`) flagging rate is reported as a secondary diagnostic.

## Ethical and Governance Notes

Clinical report text may remain sensitive after technical de-identification. Public sharing should follow institutional review, data-use agreements, and journal policy: controlled access for full text; public release for code, schema, manifest, scorer, aggregate results, and a small reviewed sample.
