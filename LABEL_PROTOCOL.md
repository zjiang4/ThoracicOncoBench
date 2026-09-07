# Label Protocol v0.4.0

## Overview

ThoracicOncoBench uses impression-priority, RECIST 1.1-informed, protocol-concordant report-derived labels.

The finalized radiology report is the clinical source document. Every report in the corpus was produced under the institutional dual-audit workflow: a preliminary report by a trainee or attending radiologist, reviewed and approved by a senior radiologist before finalization. The finalized impression therefore represents the audited final synthesis of the reporting radiologist, and the labeling protocol treats it as the authoritative longitudinal conclusion.

The current protocol covers report-level longitudinal change, not image-level diagnosis.

## Clinical Basis

The labeling engine is grounded in three authorities, in the following order of precedence:

1. **Dual-audited final impression (impression priority with conflict quarantine).** When the finalized impression contains an explicit **oncologic** change conclusion (progression/worsening, improvement, stability, or both), that conclusion is used as the primary synthesis. If findings contain an explicit disease-relevant RECIST-eligible change that conflicts with a stable impression, the pair is labeled `indeterminate`/`conflict` rather than silently discarding the finding. Changes limited to effusion, pneumothorax, atelectasis, infection, fibrosis, or postoperative findings are not tumor progression endpoints.
2. **RECIST 1.1** (Eisenhauer EA et al. *New response evaluation criteria in solid tumours: revised RECIST guideline (version 1.1)*. Eur J Cancer 2009;45:228-247):
   - a new malignant lesion defines progressive disease;
   - >=20% increase in diameter with >=5 mm absolute increase supports progression;
   - >=30% decrease in diameter supports regression;
   - absence of meaningful change supports stable disease.
   Because routine reports do not provide formal target-lesion sums or nadir measurements, paired single-lesion measurements extracted from report sentences are applied as RECIST-informed thresholds, not RECIST-compliant response assessments.
3. **iRECIST** (Seymour L et al. *iRECIST: guidelines for response criteria for use in trials testing immunotherapeutics*. Lancet Oncol 2017;18:e143-e152): only unequivocal new or progressive disease counts as progression. Equivocal statements (待排, 待鉴别, 不除外, 可能, 倾向, 性质待定) are downgraded out of the primary set.
4. **Oncologic-scope gate.** Progression/regression evidence must identify a malignant disease target (primary tumor, recurrence, malignant-appearing lesion, metastatic lesion, or disease-relevant lymph node/pleural lesion). Generic interval change in physiology, postoperative anatomy, or inflammation is retained only as a confounder flag.

## Label Decision Procedure

The engine (`scripts/label_engine.py`, parser v0.4.0) executes the following ordered procedure for each consecutive report pair:

1. **Extract the impression conclusion.** Each impression sentence is classified as documenting progression, regression, or stability, with negation and uncertainty screening. A change paired with recommendation/monitoring language (追查, 复查, 随访, 请结合, 密切观察) is treated as equivocal rather than unequivocal.
2. **Impression priority with conflict quarantine.** If the impression contains at least one definite conclusion, the label follows the impression: concurrent worsening and improvement -> `mixed`; worsening -> `progression`; improvement -> `regression`; otherwise `stable`. A stable impression plus explicit disease-relevant findings change is quarantined as `indeterminate`/`conflict` for secondary review. Evidence tier: `definitive` only when no conflict exists.
3. **Quantitative evidence.** If the impression is silent, paired prior/current disease-target measurements extracted from findings sentences are evaluated with RECIST-informed thresholds (>=20% and >=5 mm increase -> progression-supporting; >=30% decrease -> regression-supporting). Extraction is role-aware (原/术前/由 markers vs 现/目前/增至 markers, in either order), uses the long axis for non-nodal lesions and the short axis for lymph nodes, and pairs only sentences containing exactly one prior-marked and one current-marked measurement. This is report-level supportive evidence, not a full RECIST assessment, because formal target-lesion sums, nadir, and image review are unavailable. Evidence tier: `quantitative`.
4. **Directional findings evidence.** Otherwise, explicit comparative statements in findings are aggregated. Change verbs (增大, 增多, 增粗, 缩小, 减小, 减少, 吸收, 消退) count only with comparative co-text (较前, 与前次, ...); bare descriptive adjectives (增大淋巴结, 体积缩小) never count. Inherently longitudinal verbs (进展, 复发, 加重, 好转, 缓解) count without co-text. Concurrent worsening and improvement -> `mixed`. Evidence tier: `directional`.
5. **Uncertainty downgrade.** Generic new nodules/lesions without explicit malignant or metastatic context, and changes described as slight/minor or paired with follow-up language, are not unequivocal RECIST progression; they are downgraded to tier `suspicious` (secondary set).
6. **Indeterminate.** No explicit comparison, or conflicting definitive evidence.

## Validity Framework (no additional human annotation)

No new human labeling was performed, and none is required by the protocol. Label validity rests on five pillars:

1. **Prospectively adjudicated source documents.** Every report was finalized under the institutional dual-audit workflow (trainee/attending draft, senior-radiologist approval); the impression is the adjudicated expert conclusion, made at the time of clinical care — before benchmark construction. The engine deterministically transcribes these adjudicated conclusions; it does not create new clinical judgments.
2. **Guideline-anchored deterministic protocol.** Every rule maps to a specific clause of RECIST 1.1 (new lesion = PD; >=20% + >=5 mm; >=30%; stable disease), iRECIST (only unequivocal progression qualifies), or the institutional reporting standard (impression priority). The machine-readable mapping is released at `protocol/rules.json` (`rule_anchors`).
3. **Implementation-fidelity testing.** Engine behavior is locked by regression tests (`tests/test_engine.py`, 28 cases) and by a machine-only perturbation fidelity suite (`scripts/perturbation_tests.py`): 100 real corpus sentences are programmatically negated, hedged, comparative-marker-stripped, or role-swapped, and the engine must respond exactly as the guideline semantics prescribe (current pass rate: 100/100).
4. **Internal multi-channel convergence.** Three semi-independent evidence channels (impression conclusion, RECIST-informed quantitative thresholds, findings directional language) must concordantly support each label; 90.4% of primary labels have >=2 concordant channels (`audit/audit_report.json`, `multi_channel_convergence`). This is the machine-only analogue of inter-rater reliability.
5. **Full auditability.** Every label ships with the deciding impression sentences, all trigger sentences with strength, metastasis-trigger status, measurement pairs, and rule ids. The complete lexicon and rule dictionary are public, enabling community audit of any single label without data access restrictions beyond the clinical text itself.

A blinded two-radiologist adjudication package is additionally exported (`audit/`, optional). It is offered as an optional external audit for clinical collaborators or reviewers; the protocol and release claims do not depend on it.

## Label Set Notes

`mixed` is a report-level extension beyond RECIST 1.1, which has no mixed-response category: it is defined as concurrent documented worsening and improvement in different lesions or disease sites, consistent with routine radiology reporting practice, and is adjudicated with the same definitions given to human readers (see `audit/ADJUDICATION_GUIDE.md`).

## New Metastatic Disease

`new_metastatic_disease = true` requires **definitive, non-negated, unequivocal** metastasis documentation:

- a new/progressing metastasis statement (新发转移, 转移较前进展, 新增转移灶, 骨质破坏 with new/progression co-text), or
- a non-hedged metastasis conclusion in the dual-audited impression (e.g., 考虑转移 as the impression's working conclusion), or
- new-lesion documentation in an oncologic disease site without benign, postoperative, or inflammatory explanation. A generic new small nodule without explicit malignant/metastatic context is not sufficient and is retained as suspicious/indeterminate.

Bare anatomical site mentions (骨, 肝, 胸膜) do not trigger the flag. Negated statements (未见转移, 未见骨质破坏) are recorded as negative evidence. Hedged statements (倾向转移, 转移与炎性待鉴别, 考虑转移可能大) set a `met_suspicious` flag but do not set the label flag.

## Hard Consistency Constraints

The engine enforces, and the release audit verifies, that in the primary set:

- `new_metastatic_disease = true` implies label ∈ {`progression`, `mixed`} (RECIST 1.1: new lesion defines progressive disease). A metastasis-positive regression becomes `mixed`; a metastasis-positive stable becomes `indeterminate` (conflict).
- A stable impression plus explicit disease-relevant findings change is quarantined as `indeterminate`/`conflict` and excluded from the primary set.
- All metastasis-positive primary instances carry at least one definitive (non-negated) metastasis trigger.
- Every pair has `interval_days > 0`.
- Model input contains findings sections only; the impression is reserved as the reference source and never appears in the model input.

## Negation, Uncertainty, and Confounder Handling

- **Negation** (未, 无, 除外, 排除, and compounds) within a 12-character window before a trigger voids that trigger. Negated progression statements (未见新发结节, 未新增病灶) are recorded as stability evidence.
- **Hard uncertainty** (可能, 可疑, 待排, 待鉴别, 待查, 待定, 不除外, 倾向, 性质待定) downgrades a sentence's evidence out of the primary set (iRECIST: only unequivocal progression counts).
- **Soft recommendations** (追查, 复查, 随访, 请结合, 密切观察) attached to a change claim make that claim equivocal; they do not by themselves establish progression or regression.
- **Postoperative/inflammatory co-text** (术后, 陈旧, 纤维, 瘢痕, 炎性, 感染, 结核, 放疗) downgrades findings-level progression evidence to suspicious unless the impression concludes progression.
- **Oncologic-scope gate:** progression/regression triggers are ignored when their local context is limited to non-oncologic findings (胸水, 积气/气胸, 肺不张, 实变/斑片影, 炎症/感染, 纤维化, 术后改变). If no disease-relevant conclusion remains, the pair is `indeterminate` rather than forced to stable.

## Primary Eligibility

An instance enters the primary benchmark when:

- evidence tier is `definitive` (impression conclusion) or `quantitative` (RECIST-informed threshold met), and
- the label is not `indeterminate`, and
- explicit comparison language is present, and
- no hard consistency constraint is violated.

All other labeled instances are retained as `longitudinal_change_secondary`. Instances with no reliable protocol mapping are retained as `longitudinal_change_indeterminate`. Both are available for uncertainty-handling research.

## Provenance

Every longitudinal instance records:

- the impression sentences used as the conclusion (`provenance.impression_conclusion`)
- every trigger with section, sentence, matched term, and strength (`provenance.triggers`)
- metastasis triggers with negation/uncertainty/definitive status (`provenance.metastasis_triggers`)
- paired measurements with RECIST-informed direction, axis choice, and uncertainty/scope flags (`provenance.measurement_evidence`)
- the primary rule and all protocol rules fired (`label.primary_rule`, `label.protocol_rule_ids`)

Provenance is intended for auditors and must not be fed to evaluated models.

## Rule Dictionary

Machine-readable rule definitions with clinical-basis citations are at `protocol/rules.json`. Core rules: `RECIST-PD-IMPRESSION`, `RECIST-PD-NEW-LESION`, `RECIST-PD-QUANTITATIVE`, `RECIST-PD-DIRECTIONAL`, `RECIST-PR-IMPRESSION`, `RECIST-PR-QUANTITATIVE`, `RECIST-PR-DIRECTIONAL`, `RECIST-SD-IMPRESSION`, `RECIST-SD-DIRECTIONAL`, `RECIST-MIXED-IMPRESSION`, `RECIST-MIXED-DIRECTIONAL`, `MEASUREMENT-BELOW-RECIST-INFORMED-THRESHOLD`, `QUALITY-ONCOLOGIC-SCOPE`, and `QUALITY-NONONCOLOGIC-DOWNGRADE`, plus consistency constraints.

## Release Audit

`scripts/audit_labels.py` runs ten deterministic checks (C1-C10) over every release build, including label-impression consistency, metastasis-label consistency, negated-only triggers, morphology false positives, non-positive intervals, input leakage, split disjointness, and identifier uniqueness. A build passes only with zero violations.

The audit additionally reports (a) the concordance between RECIST-informed single-lesion thresholds and the impression-driven label on instances carrying both (quantifying how far the single-lesion approximation diverges from radiologist synthesis), and (b) the count of primary instances whose findings lack explicit change language (a natural reading-inference challenge subset, flagged via `provenance.flags.findings_explicit_change_language`).

The adjudication sample is exported **blinded**: adjudicators receive randomized case order and report text only (`adjudication_blinded.csv`); engine labels are withheld and joined only at analysis time (`agreement_stats.py --key adjudication_analysis_key.csv`). The default design is 60 per non-stable class + 120 stable + all remaining metastasis-positive + up to 30 additional postoperative-flagged progression cases (postoperative/inflammatory language is the main known confounder stratum). Adjudication results are reported as raw agreement, Cohen's kappa, per-class engine error rate, the postoperative-stratum engine error rate, and the engine-error instance list.

## Reference Label Language

Use:

> Longitudinal reference labels were derived from dual-audited finalized radiology reports under a prespecified oncologic-scope protocol: the finalized impression's explicit malignant-disease change conclusion was taken as authoritative (impression priority); when the impression was silent, RECIST 1.1-informed thresholds applied to report-documented paired disease-target measurements and explicit comparative findings language were used; non-oncologic interval changes were excluded from tumor response labels and equivocal statements were downgraded following iRECIST's requirement for unequivocal progression.

Use:

> Labels are protocol-concordant, report-derived reference standards anchored to the dual-audited radiologist impression, not independent image-level adjudications.

Avoid:

> The algorithm generated the gold standard.

Avoid:

> The benchmark labels are clinical ground truth.

## Change Log

- **v0.4.0** (this protocol): v0.3.0 safeguards plus cm/厘米 measurement normalization, conflict quarantine for stable-impression versus explicit findings change, and iRECIST-conservative handling of generic new nodules and slight/follow-up-qualified change language.
- **v0.3.0**: impression-priority engine; RECIST 1.1/iRECIST grounding; oncologic-scope gating; lymph-node short-axis measurement; non-oncologic confounder exclusion; comparative co-text morphology; hard consistency constraints; findings-only model input; deterministic release audit; adjudication sampling.
- **v0.1.0** (superseded): keyword-lexicon extraction without impression precedence; findings+impression model input; no consistency constraints. Known issues: ~8% of primary labels contradicted a stable-only impression; 25% of metastasis-positive labels were stable/regression; 74% of metastasis triggers occurred in negated sentences; model input leaked the impression (a lexicon over the impression alone matched 84.3% of primary labels).

## Future Extensions

- iRECIST-style confirmation task when treatment context is available
- pathology-confirmed TNM staging module when registry linkage is available
- public sample release with controlled-access full text
- external multi-center rebuild of the same protocol (same builder, local reports)
