# 0820 Reproducibility Record

## Cohorts

- T1 longitudinal change assessment: 800 pairs from 605 patients; 104 progression cases; 22 pairs with dual-verified documented new metastasis.
- T3 clinical-to-pathologic staging: 213 temporally aligned cases.
- AJCC era: 98 cases in the AJCC 7 era (2017 or earlier) and 115 in the AJCC 8 era (2018 or later).

## Reference-standard provenance

The source CT reports and benchmark reference answers were produced within the clinical workflow of Peking University Cancer Hospital, a national-level tertiary oncology institution. Reports underwent 2-radiologist verification or a documented second audit before inclusion. T1 labels were derived from verified radiologist-documented longitudinal change descriptors. T3 reference values were pathology-confirmed pTNM recorded during clinical care.

## Scoring

The frozen scorer uses an intention-to-evaluate denominator. Parse failures, missing fields, and schema-invalid outputs are counted as incorrect. T1 reports macro-F1, progression recall, progression-to-stable misclassification, and the metastasis-positive-pair endpoint described below. T3 reports exact-match and component-level T, N, and M concordance.

The metastasis-positive endpoint is calculated among the 22 dual-verified metastasis-positive pairs as the proportion whose model longitudinal-change label is not `progression`. It is not a separate metastasis-classification task because the released model output schema contains the T1 change label but no independent binary metastasis field.

## Model-run metadata

Fifteen models were each run once. Temperature was 0.6, top_p was 0.95, prompt version was `v1 (infer_v2.py)`, API seeds were not controlled, and maximum-output-token limits were heterogeneous across providers.

## Data access

Patient-level source records and institutional identifiers are not included in this public repository. The repository provides the schema example, frozen scorer, aggregate results, and corrected figures.
