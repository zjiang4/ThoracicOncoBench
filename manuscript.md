# Title Page

**Title:** ThoracicOncoBench: A Benchmark for Evaluating Large Language Models on Longitudinal Thoracic Oncologic Imaging Report Interpretation

**Running Title:** An Oncologic LLM Benchmark for Thoracic CT Reports

**Authors:** [Anonymized]

**Affiliations:** [Anonymized]

**Corresponding Author:** [Anonymized]

**Funding:** [To be completed]

**Disclosures:** [To be completed]

**Data & Code Availability:** The benchmark, frozen scorer, prompt templates, and all baseline predictions will be released under a controlled-access data use agreement upon acceptance.

**Ethics:** Approved by the IRB of [National Cancer Center] with waiver of informed consent. All data de-identified.

---

# Key Points

**Question:** Can current large language models, both general-purpose and medical-specialized, accurately perform longitudinal change assessment, structured oncologic finding extraction, TNM staging inference, and impression generation from thoracic CT report text when judged against hospital-validated reference standards that include pathology-confirmed staging?

**Findings:** In this benchmark study of 1,995 curated task instances from 17,355 thoracic CT reports of 9,334 patients, 15 large language models demonstrated overall accuracy of 63.8% to 77.6% on longitudinal change assessment, with 28.8% to 49.0% of true disease progressions missed. Exact-match TNM staging accuracy against pathology-confirmed reference standards ranged from 0.5% to 25.8%, and T-category accuracy was only 0.5% to 43.2%. No model was uniformly superior across all tasks.

**Meaning:** In this benchmark study evaluating 15 large language models against hospital-validated, pathology-confirmed reference standards, no model could reliably detect disease progression or infer TNM staging from explicit radiology text. Even medical-specialized models missed over one-quarter of true progressions and achieved T-category staging accuracy below 44%. These results suggest that current models are not yet safe for autonomous deployment in oncologic decision-making and identify specific clinical reasoning capabilities that the next generation of medical artificial intelligence must address.

---

# Abstract

**Importance:** Large language models are being rapidly integrated into radiology workflows for report generation, triage, and clinical decision support. Regulatory agencies and healthcare systems are actively considering their deployment for tasks that directly affect patient management, including determining whether disease has progressed on follow-up imaging and inferring cancer stage from report text. Yet the evaluation frameworks used to justify such deployment remain fundamentally disconnected from clinical reality: they test single-timepoint text summarization against subjective radiologist-authored references, not the longitudinal reasoning and staging inference that actually govern treatment decisions, and they do not use pathology-confirmed outcomes as ground truth. No prior study has tested whether current models can perform these clinically consequential tasks against the same reference standards that govern patient care.

**Objective:** To construct and apply ThoracicOncoBench, a comprehensive benchmark for evaluating large language models on longitudinal thoracic oncologic CT report interpretation, with multi-tier reference standards derived from hospital-validated clinical data.

**Materials and Methods:** This retrospective benchmark study used 17,355 consecutive chest CT reports from 9,334 patients (2015 through 2024) at [National Cancer Center], a National Cancer Center. All reports in the corpus had undergone standard institutional dual-reading quality review by board-certified radiologists at the time of clinical service. Reports were linked to a prospectively maintained, institutionally validated oncology outcomes registry containing surgical pathology and survival data for 5,403 patients, with pathology staging (pTNM) confirmed by board-certified pathologists according to AJCC 9th edition criteria. From this corpus, 1,995 task instances were curated through quality-first stratified sampling. The benchmark comprised three task families: longitudinal change assessment (800 consecutive timepoint pairs), structured extraction and clinical reasoning (1,095 single-timepoint reports), and reference-free impression generation (100 cases). Reference standards were derived entirely from hospital clinical records, including pathology-confirmed TNM staging (temporally aligned subset, n = 213), survival outcomes (n = 1,186), and radiologist-authored impressions (n = 1,093), without additional annotation. Fifteen large language models, spanning closed-source frontier models (GPT-5.4, Gemini-3.5-flash, Baichuan-M3), open-source general-purpose models (Nemotron-3-Ultra, Qwen3.5-397B, DiffusionGemma-26B, Step-3.7-flash, DeepSeek-V4, Minimax-M2.7), and medical-specialized models (MedSeek [https://medseek.meduc.cn], HuatuoGPT, AntAngelMed, MediPhi, MediX, QwQ-Med-3), were evaluated under zero-shot prompting. Primary metrics included macro-F1, progression recall with 95% Wilson confidence intervals, fatal error rate (model judging "stable" when progression was documented), exact-match staging accuracy, and ROUGE-L. Reporting followed the CLAIM 2024, STROBE, and BIAS guidelines.

**Results:** Across 15 models, accuracy on change assessment ranged from 63.8% to 77.6% (macro-F1, 0.42 to 0.66). Progression recall ranged from 51.0% to 73.1%, with widely overlapping 95% confidence intervals, indicating that 27% to 49% of true progressions were not identified. Fatal error rates among progression cases ranged from 10.6% to 18.3%. Exact-match TNM staging accuracy ranged from 0.5% to 25.8%, and T-category accuracy was only 0.5% to 43.2% despite explicit textual descriptions of lesion dimensions. Impression generation ROUGE-L F1 ranged from 0.09 to 0.44. MedSeek achieved the highest macro-F1 (0.66) and staging exact-match (25.8%); GPT-5.4 achieved the highest N-category (70%) and M-category (80%) accuracy; DiffusionGemma achieved the highest change assessment accuracy (77.6%). No model was uniformly superior.

**Conclusion:** ThoracicOncoBench provides a standardized, pathology-anchored evaluation framework that reveals substantial gaps in current large language models, including medical-specialized systems. Because the reference standards reflect the clinical conclusions that governed actual patient management at a National Cancer Center, these results carry direct implications for the safe deployment of language models in oncologic care: current models are not yet reliable enough to autonomously support decisions about disease progression or TNM staging.

---

# Introduction

Chest computed tomography is the primary imaging modality for thoracic oncologic care, guiding clinical decisions at every stage of the patient journey from initial detection through staging, treatment response evaluation, and postoperative surveillance. The radiology report synthesizes complex longitudinal information into conclusions about whether a lesion has progressed, remained stable, or regressed, and whether new metastatic disease has appeared. These conclusions carry direct therapeutic consequences. A determination of disease progression on follow-up imaging, typically assessed according to RECIST criteria,(20) may trigger escalation from surveillance to systemic therapy, enrollment in a clinical trial, or referral for salvage surgery. Conversely, an assessment of stable disease supports continued observation or maintenance therapy. An erroneous conclusion in either direction is harmful: a missed progression may delay life-prolonging treatment and allow further tumor dissemination, while a false alarm may expose patients to the toxicity and cost of unnecessary intervention. The accuracy of these longitudinal judgments, and by extension the accuracy of any artificial intelligence system tasked with making them, is therefore a patient-safety issue of the highest order.

Large language models have attracted growing interest for automated radiology report interpretation. Early demonstrations showed that general-purpose chatbots could answer radiology board-style questions, although concerns were quickly raised about hallucination, factual inconsistency, and the conflation of fluency with accuracy.(3,4) Subsequent work progressively refined report generation capabilities. Sun et al(4) demonstrated that GPT-4(19) could generate radiology impressions from findings text. Serapio et al(5) fine-tuned an open-source T5 model on 370,000 reports and conducted a 60-case reader study. Hong et al(6) evaluated a domain-specific multimodal generative model for chest radiograph reporting in a multi-reader multi-case study of 758 examinations, demonstrating improved reading efficiency and sensitivity for pleural and mediastinal abnormalities. Huang et al(7) conducted a prospective clinical deployment of generative artificial intelligence across 23,960 radiograph interpretations, reporting a 15.5% improvement in documentation efficiency without degradation of clinical accuracy. Most recently, the MIRA study(8) fine-tuned a Qwen2.5-7B model(18) on 1.87 million radiology reports from 42 Chinese centers, achieving a BERTScore F1 of 0.92 at internal validation and introducing ASPIRE, an automated large-language-model judge for radiologist-level scoring. In parallel, the computer-vision community has advanced structured benchmarking through public challenges: LUNA16(10) established the foundation for nodule detection on CT, and its successor LUNA25(9) benchmarked artificial intelligence systems against 65 radiologists for malignancy risk estimation of indeterminate lung nodules, although the investigators explicitly noted that longitudinal follow-up was not addressed. MedGemma 1.5(11) extended multimodal capabilities to three-dimensional CT volumes and multi-timepoint chest radiographs, but its longitudinal evaluation was limited to three-category classification on radiographs with a modest 4 percentage-point improvement.

Despite these advances, four critical gaps persist in the literature, each with direct implications for clinical translation. First, every published evaluation has been confined to cross-sectional, single-timepoint report summarization, leaving longitudinal change assessment entirely unexplored in systematic benchmark form. This omission is not merely an academic limitation; longitudinal change judgment is arguably the most clinically consequential reasoning task in oncologic imaging, because it directly determines whether a patient's treatment plan must be altered. A model that writes fluent impressions but cannot reliably detect progression is clinically unsafe. Second, prior work has been situated almost exclusively within the radiologist's perspective, evaluating whether models can summarize or reproduce findings text, without assessing oncology-specific reasoning capabilities such as TNM staging inference or assessment of surgical resectability. These are precisely the tasks that determine whether a patient is offered surgery, chemoradiation, or palliative care. Third, no study has aligned model evaluations against pathology-confirmed reference standards or survival outcomes. In every prior benchmark, the reference has been radiologist-authored impression text, which is itself a subjective and imperfect gold standard. A model may produce text that closely matches the radiologist's impression yet still be clinically wrong if the radiologist's assessment was itself inaccurate. The ultimate arbiter of whether a radiologic judgment was correct is the surgical pathology specimen and the patient's subsequent clinical course, neither of which has been used as a reference standard in any prior LLM benchmark. Fourth, evaluation frameworks have been dominated by surface-level lexical metrics such as ROUGE(16) and BERTScore,(17) which treat all errors as equivalent. A reporting system that misses a new metastasis and one that uses slightly different wording to describe the same stable nodule may receive identical ROUGE scores, yet only the former error could harm a patient. Clinically graded error metrics, in which the failure to detect progression or metastasis carries far greater weight than a stylistic variation, do not exist in current benchmarks. This methodological gap has been flagged as part of a broader "benchmarking crisis" in biomedical machine learning.(23)

We therefore developed ThoracicOncoBench to address these gaps. The benchmark is grounded in a fundamental clinical premise: the reference standards for evaluating model performance should be the same standards that govern clinical decision-making. At a National Cancer Center, every CT report in our corpus had undergone institutional dual-reading quality review by board-certified radiologists, and every pathology-confirmed TNM staging was determined by board-certified pathologists using standardized AJCC criteria.(15) By linking these clinically validated data to the corresponding radiology reports, we constructed a benchmark in which the model input is the radiologist-documented findings text and the reference answers are the hospital's own clinical conclusions. No additional annotation was required, because the reference standards were established by the treating clinical teams in the course of routine patient care. This design ensures that the benchmark measures what matters clinically: whether a model can reach the same conclusions that the multidisciplinary oncology team reached and acted upon. The purpose of this study was to construct this benchmark and to characterize the performance and failure modes of 15 current large language models across change assessment, structured extraction, staging inference, and impression generation, with particular attention to clinically consequential errors that could affect patient management.

---

# Materials and Methods

## Study Design

This retrospective, single-center benchmark study was conducted at [National Cancer Center] (Figure 1). The benchmark design, task definitions, evaluation metrics, and analysis plan were prespecified before model evaluation began. Reporting follows the Checklist for Artificial Intelligence in Medical Imaging (CLAIM) 2024 update,(12) the Strengthening the Reporting of Observational Studies in Epidemiology (STROBE) guideline,(13) and the Biomedical Image Analysis Challenges (BIAS) guideline.(14) The study was approved by the institutional review board with a waiver of informed consent. All patient identifiers were de-identified through SHA-256 hashing with truncation to 12 hexadecimal characters. No artificial intelligence model was trained in this study; the work consists exclusively of model evaluation against pre-existing clinical reference standards.

> **[Insert Figure 1 here]**

## Data Sources

The institutional chest CT report corpus comprised all consecutive examinations performed between January 2015 and July 2024 at [National Cancer Center], a designated National Cancer Center. At this institution, all radiology reports are generated through a standardized workflow in which a preliminary report is authored by a radiology trainee or attending radiologist and subsequently reviewed and approved by a senior radiologist before finalization, ensuring that every report in the corpus had undergone institutional dual-reading quality review. Reports were retrieved from the radiology information system as structured text records that included the radiologist-documented findings and, where present, the radiologist-authored impression, along with examination metadata (study date, modality, body part).

For patients who underwent thoracic oncologic surgery during the same period, the institution's prospectively maintained oncology outcomes registry provided surgical procedure records and postoperative pathology reports. Pathology-confirmed TNM staging (pTNM) was determined by board-certified pathologists according to the AJCC 9th edition staging manual,(15) with all staging assignments reviewed and verified as part of the institution's quality-assured cancer registry workflow. Additional fields included tumor histologic type and differentiation, resection margin status, lymphovascular invasion, number of lymph nodes examined and positive, IASLC lymph node station involvement, metastasis site and date, vital status, death date, and date of last follow-up. These registries are maintained independently of the present study by the institution's cancer registry team and constitute the routine clinical record used for multidisciplinary tumor board decisions. The two data sources were linked at the patient level using the institutional patient identifier, which was subsequently replaced by a hashed surrogate for de-identification. Of the 9,334 unique patients in the chest CT report corpus, 5,403 (57.9%) had corresponding records in the oncology outcomes registry, yielding 12,301 linked chest CT reports and 21,143 surgical hospitalization records.

## Benchmark Construction

### Task Definition

Three task families were defined to span the spectrum of thoracic oncologic reasoning (Table 1).

Task 1, Longitudinal Change Assessment, presents the model with consecutive timepoint pairs from the same patient and requires it to determine the overall direction of change (progression, regression, stable, or mixed) and to flag the presence of new metastatic disease. We emphasize that this task tests the capacity to comprehend complex longitudinal clinical narratives, synthesizing information across two lengthy findings texts, reconciling concurrent and sometimes contradictory change signals for multiple lesions, and adhering to a structured output schema. It does not test arithmetic reasoning from raw lesion measurements. The reference answer was derived by standardized automated extraction from the radiologist-documented change descriptors in the current findings text, following a prespecified keyword lexicon that incorporated negation detection. Specifically, keywords appearing within a negation context, such as the phrase "未见新发" (no new findings seen), where the progression keyword "新发" (new) is preceded by the negator "未见" (not seen), were excluded from the positive signal, preventing false-positive labeling of stability descriptions as progression. This approach leverages the radiologist's own longitudinal judgment, already documented in routine practice, as the reference standard. We acknowledge that because the reference answer is extracted from the same text provided to the model, this task assesses reading comprehension and clinical narrative synthesis rather than de novo image-based change detection. We position this as a deliberate design choice that isolates the language-reasoning component of longitudinal assessment from the perception component.

Tasks 2 and 3, Structured Extraction and Clinical Reasoning, require the model to extract structured oncologic findings (primary lesion location, dimensions, composition, IASLC lymph node station involvement, pleural involvement, vascular or airway invasion, distant metastasis site) and to infer clinical TNM staging elements (cT, cN, cM) according to the AJCC 9th edition.(15) The reference answer for staging is the pathology-confirmed pTNM recorded at the time of surgery, time-aligned to the preoperative imaging study. Because pathology staging and clinical staging are conceptually distinct variables measured by different methods at different times, staging concordance was evaluated only on instances from initial-presentation scenarios (n = 213) where the CT was performed before surgery and the pTNM was determined from that same surgical specimen. Postoperative follow-up, metastatic disease, and surveillance scenarios were excluded from staging analysis because their pTNM derives from prior surgery and does not reflect the disease state depicted in the current imaging.

Task 4, Impression Generation, requires the model to generate a free-text impression from the findings text. The reference for scoring is the radiologist-authored impression recorded in the clinical report.

### Illustrative Examples

To clarify the scoring methodology, two representative examples are described.

In a Task 1 example (case T1-00455), the prior findings text documented that an anterior mediastinal nodule had decreased in size (from 21 by 10 mm to 20 by 8 mm) and that mediastinal lymph nodes had also regressed. The current findings text documented that the same anterior mediastinal nodule had slightly increased (from 20 by 8 mm to 21 by 12 mm), while all other findings remained stable. The negation-aware extraction algorithm detected the non-negated progression keyword "增大" (enlarged) in the current text, combined with the absence of any non-negated regression keyword, and assigned the reference label "progression." All four evaluated models that were tested on this instance classified it as "mixed," because they weighted the dominant stability signals ("同前," "未见") equally with the single progression signal. This example illustrates the clinical reasoning challenge: in a postoperative follow-up setting, any documented enlargement warrants a progression classification, regardless of the number of concurrent stable findings.

In a Task 3 example (case T234-00834), the findings text described a cavitary mass in the left upper lobe measuring 39 by 29 mm with spiculated margins and pleural retraction, along with mediastinal and hilar lymphadenopathy (largest node, 23 by 13 mm) and scattered bilateral pulmonary micronodules. The pathology-confirmed reference staging was T2N2M0 (stage IIIA). GPT-5.4 correctly inferred the T category but overcalled N to N3. Gemini-3.5 produced null values for all three components, effectively declining to stage. Nemotron-3 overcalled M to M1a by misclassifying the bilateral micronodules as pulmonary metastases. Qwen3.5 overcalled T to T4 and M to M1. This example demonstrates that models frequently struggle with the distinction between benign bilateral micronodules (representing inflammatory or infectious changes) and true pulmonary metastases, a distinction that directly determines M-category assignment and, consequently, stage group and treatment approach.

### Instance Selection

Quality-first stratified sampling at the patient level yielded 1,995 instances from 1,670 unique patients: 800 change-assessment pairs (enriched for progression and regression signals), 1,095 single-timepoint reports across six clinical scenarios, and 100 reference-free impression generation cases. The 800 change-assessment instances comprised stable (n = 527; 65.9%), regression (n = 143; 17.9%), progression (n = 104; 13.0%), and mixed (n = 26; 3.2%), with 22 instances (2.8%) documenting new metastatic disease. All sampling was performed with a fixed random seed for reproducibility.

## Evaluated Models

Fifteen large language models were evaluated under zero-shot prompting, spanning three categories: closed-source frontier models (GPT-5.4, Gemini-3.5-flash, Baichuan-M3), open-source general-purpose models (Nemotron-3-Ultra-550B, Qwen3.5-397B, DiffusionGemma-26B, Step-3.7-flash, DeepSeek-V4-flash, Minimax-M2.7), and medical-specialized models (MedSeek [https://medseek.meduc.cn],(24) HuatuoGPT, AntAngelMed, MediPhi, MediX, QwQ-Med-3(25)). Each model received identical input formatting and was required to produce structured JSON output conforming to a prespecified schema. Decoding parameters were fixed across all models (temperature, 0.6; top_p, 0.95; maximum output tokens, 12,000). All models were accessed via application programming interface.

## Evaluation Metrics

All metrics were computed using a single frozen scoring script released with the benchmark. For Task 1, the primary metric was macro-averaged F1 score across the four change categories, with per-class precision and recall reported. Because the reference-standard distribution is imbalanced (stable, 65.9%; progression, 13.0%), per-class recall, particularly progression recall, was emphasized over overall accuracy. The clinically critical secondary metric was the fatal error rate, defined as the proportion of progression cases in which the model judged the examination "stable," computed with the number of progression cases (n = 104) as denominator, with 95% Wilson score confidence intervals. An additional metric captured missed metastatic disease, defined as the proportion of the 22 metastasis-positive instances in which the model judged the examination stable or regressing.

For Tasks 2 and 3, exact-match accuracy and per-component (T, N, M) accuracy were computed against pathology-confirmed pTNM on the 213 temporally aligned instances. Because clinical staging and pathology staging are conceptually distinct, the staging concordance metric is reported with explicit acknowledgment of this distinction.

For Task 4, ROUGE-L F1(16) and character-level F1 were computed against radiologist-authored reference impressions.

## Statistical Analysis

Per-class recall and fatal error rates are reported with 95% Wilson score confidence intervals. These intervals are particularly important for the progression subset (n = 104) and metastasis subset (n = 22), where the limited number of positive cases yields wide intervals and overlapping ranges across models. Differences between models were assessed using the McNemar test for paired comparisons. All statistical tests were two-sided, with P values less than .05 considered indicative of difference without implying clinical importance. Analyses were performed using Python with the released frozen scoring script.

## Limitations

This study has several limitations. First, the benchmark is derived from a single tertiary cancer center, and the report style, patient population, and language (Chinese) may limit generalizability. Second, the Task 1 reference standard was derived by automated keyword extraction with negation detection from radiologist-documented change descriptors; while this approach was validated against full-text review, it cannot capture subtle clinical judgment that may differ from the documented wording. Third, the number of progression cases (n = 104) and metastasis cases (n = 22) is limited, resulting in wide confidence intervals for per-class metrics; consequently, differences between models on these specific subtasks should be interpreted with caution. Fourth, TNM staging concordance was evaluated only on the 213 instances from initial-presentation scenarios with temporally aligned surgical pathology. Fifth, the benchmark evaluates text-level reasoning only and does not assess image interpretation capability. Sixth, all models were evaluated under zero-shot prompting without task-specific fine-tuning on the benchmark data.

---

# Results

## Overview

Fifteen large language models were evaluated on 1,995 benchmark instances. The majority-class baseline of judging every change-assessment pair as "stable" yielded an accuracy of 65.9% (527 of 800), against which all model performances must be interpreted. Across all tasks, no single model achieved uniformly superior performance; rather, different models excelled on different tasks, and the trade-offs between sensitivity and specificity varied substantially.

## Task 1: Longitudinal Change Assessment

Overall accuracy on the 800 change-assessment instances ranged from 63.8% (QwQ-Med-3) to 77.6% (DiffusionGemma), with a mean of 69.6% across 15 models (Table 1).

> **[Insert Table 1 here]** Seven of 15 models exceeded the majority-class baseline by less than 5 percentage points, underscoring the difficulty of the task. Macro-averaged F1 scores, which weight all four change categories equally regardless of their prevalence, ranged from 0.421 (MediPhi) to 0.657 (MedSeek), with a mean of 0.494. The discrepancy between accuracy and macro-F1 reflects the class imbalance: a model can achieve high accuracy by predominantly predicting the majority class (stable) while performing poorly on the clinically critical minority classes (progression, regression, mixed).

Progression recall, the metric of greatest clinical importance, ranged from 51.0% (Step-3.7) to 73.1% (MedSeek, MediX, and DiffusionGemma, tied). This means that even the best-performing models failed to identify between 27% and 49% of true disease progressions. The 95% Wilson confidence intervals for progression recall were wide, spanning approximately 20 percentage points for each model, and the intervals of all 15 models overlapped substantially, precluding claims of statistically significant differences between individual models on this subtask.

The fatal error rate, defined as the proportion of progression cases in which the model judged the examination "stable," ranged from 10.6% (DeepSeek-V4) to 18.3% (DiffusionGemma) (Table 2).

> **[Insert Table 2 here]**
>
> **[Insert Figure 2 here]** In absolute terms, every model misjudged between 11 and 19 of the 104 true progression cases as stable. These errors represent the most clinically dangerous failure mode, because they correspond to a patient with active disease progression being assessed as unchanged, potentially delaying escalation of care.

Analysis of misclassification patterns among the 104 progression cases (Figure 2) revealed two dominant error modes. First, direct misclassification as "stable" occurred in 11 to 19 cases per model (10.6% to 18.3% of progressions). Second, classification as "mixed" or "indeterminate," which represents a failure to commit to a progression judgment, occurred in an additional 11 to 37 cases per model. Notably, Step-3.7 classified 36.5% of true progressions as "mixed," reflecting a systematic tendency to avoid committing to a single direction of change when competing signals were present. At the other extreme, DiffusionGemma classified only 3.8% of progressions as "mixed" but had the highest direct misclassification rate (18.3%), suggesting a tendency to commit to a judgment even when uncertain.

A complementary analysis of false positives revealed that models also exhibited substantial rates of overcalling progression in stable cases. The proportion of truly stable examinations misclassified as "progression" ranged from 3.6% (GPT-5.4, Qwen3.5) to 13.7% (QwQ-Med-3). QwQ-Med-3, Baichuan-M3, and MediX were the most aggressive in this regard, each falsely flagging progression in over 12% of stable cases. GPT-5.4 was the most conservative, with a false-positive rate of only 3.6%, but this conservatism came at the cost of a higher fatal error rate among progression cases (16.4%).

The metastasis-miss rate, computed on the 22 instances with documented new metastatic disease, ranged from 0% (Step-3.7) to 40.9% (MedSeek). The wide range reflects the very small denominator (n = 22), and confidence intervals are correspondingly wide. Nevertheless, several models missed metastatic disease in a substantial proportion of cases, which is concerning because missed metastasis has the most direct impact on staging and treatment selection.

## Tasks 2 and 3: Structured Extraction and Clinical TNM Staging

Exact-match accuracy for TNM staging against pathology-confirmed pTNM, evaluated on the 213 temporally aligned instances from initial-presentation scenarios, ranged from 0.5% (MediPhi) to 25.8% (MedSeek), with a mean of 15.2%. This means that even the best-performing model correctly inferred all three staging components (cT, cN, and cM) in only approximately one-quarter of cases.

Per-component accuracy revealed a consistent hierarchy across nearly all models: M-category accuracy was highest, followed by N-category, with T-category consistently the weakest.

> **[Insert Figure 3 here]**

T-category accuracy ranged from 0.5% (MediPhi) to 43.2% (MediX), with a mean of 32.3%. N-category accuracy ranged from 4.9% (MediPhi) to 69.9% (GPT-5.4), with a mean of 48.7%. M-category accuracy ranged from 1.0% (MediPhi) to 79.6% (GPT-5.4), with a mean of 47.3%. The poor T-category performance is particularly notable because the findings text explicitly described lesion dimensions (for example, "approximately 39 by 29 mm"), yet models frequently misassigned the T category, suggesting difficulty in mapping quantitative measurements to the correct AJCC T-category threshold(15) rather than an inability to read the measurement itself.

Inter-component correlation analysis using Spearman rank coefficients across the 15 models revealed that N-category and M-category accuracy were strongly correlated (rho = 0.809), while T-category accuracy correlated only moderately with both N (rho = 0.407) and M (rho = 0.316). This pattern suggests that the ability to correctly infer nodal and metastatic status may share underlying reasoning capabilities, such as interpreting lymph node station descriptions and recognizing distant lesion patterns, while T-category inference depends on a distinct skill set related to parsing primary lesion dimensions and local invasion descriptors.

GPT-5.4 achieved the highest N-category (69.9%) and M-category (79.6%) accuracy, substantially exceeding all other models on these components. However, its T-category accuracy (37.1%) was comparable to several other models, and its overall exact-match rate (24.9%) was only slightly lower than MedSeek's (25.8%), reflecting the fact that errors in any single component preclude exact-match success.

MediPhi's near-zero performance across all staging components (T = 0.5%, N = 4.9%, M = 1.0%) warrants specific comment. Despite being a model marketed as medical-specialized, its inability to perform even basic staging inference highlights an important finding: domain-specific fine-tuning or labeling does not necessarily confer clinical reasoning capability. The gap between MediPhi and other medical-specialized models such as MedSeek (exact-match, 25.8%) and MediX (T-category, 43.2%) underscores the heterogeneity within the medical-specialized category and cautions against assuming that any model labeled "medical" is appropriate for oncologic reasoning tasks.

## Task 4: Impression Generation

ROUGE-L F1 scores(16) against radiologist-authored reference impressions ranged from 0.090 (QwQ-Med-3) to 0.436 (DeepSeek-V4), with a mean of 0.300. Character-level F1, a language-agnostic similarity metric, ranged from 0.151 to 0.516. The wide range reflects substantial differences in the models' ability to produce clinically coherent Chinese-language impression text. QwQ-Med-3's extremely low ROUGE-L score (0.090) was attributable to frequent output formatting failures and non-Chinese responses rather than to a fundamental inability to summarize findings.

DeepSeek-V4 achieved the highest ROUGE-L (0.436), followed by DiffusionGemma (0.408) and Qwen3.5 (0.359). Notably, the top-performing models on impression generation were not the same as those that excelled on change assessment or staging, reinforcing the finding that these tasks tap distinct capabilities.

## Inter-task Correlations

Correlation analysis across the 15 models revealed that change-assessment macro-F1 and staging exact-match were moderately correlated (Spearman rho = 0.621), suggesting partial overlap in the underlying capabilities required for these tasks. However, progression recall specifically did not correlate with staging accuracy (rho = 0.030), indicating that the ability to detect progression from longitudinal narratives is largely independent of the ability to infer anatomic staging from a single report.

Impression generation quality (ROUGE-L) correlated only weakly with change-assessment accuracy (rho = 0.184) and moderately with staging accuracy (rho = 0.368). This finding has an important practical implication: a model that generates fluent, high-quality impression text is not necessarily more accurate at clinical reasoning tasks. The conflation of textual fluency with clinical accuracy is a recurring concern in the medical LLM literature,(21,22) and these results provide empirical support for the necessity of task-specific evaluation.

## Model Type Comparison

General-purpose and frontier models (n = 9) achieved a mean T1 accuracy of 0.698 (range, 0.657 to 0.776), a mean T1 macro-F1 of 0.500, a mean T3 exact-match of 0.167, and a mean T4 ROUGE-L of 0.340. Medical-specialized models (n = 6) achieved a mean T1 accuracy of 0.694 (range, 0.637 to 0.750), a mean T1 macro-F1 of 0.486, a mean T3 exact-match of 0.129, and a mean T4 ROUGE-L of 0.240. The differences between the two groups were modest and did not consistently favor either category. The best-performing individual model on overall macro-F1 was MedSeek (0.657), a medical-specialized model, while the best on staging exact-match among general-purpose models was GPT-5.4 (0.249). These results indicate that the designation "medical-specialized" is not a reliable predictor of superior oncologic reasoning performance, and that individual model architecture, training data composition, and alignment strategy may be more important determinants than domain-specific pre-training alone.

## Per-Task Performance Profiles and Capability Dissociation

Visual comparison of per-task performance profiles (Figure 3) revealed marked heterogeneity in how models allocated capability across TNM staging components. Grouped bar charts of per-component staging accuracy (Figure 3) demonstrated that N-category and M-category accuracy varied more widely across models (ranges of 4.9% to 69.9% and 1.0% to 79.6%, respectively) than T-category accuracy (0.5% to 43.2%), and that models achieving high T-category accuracy did not necessarily achieve high N or M accuracy. MediX, for example, achieved the highest T-category accuracy (43.2%) but among the lowest N-category (32.0%) and M-category (22.9%) accuracy. Conversely, GPT-5.4 achieved the highest N-category (69.9%) and M-category (79.6%) accuracy but only moderate T-category accuracy (37.1%). This inverse pattern underscores a central finding: the tasks are not monolithic, and a model that excels at primary lesion assessment may underperform on nodal and distant disease evaluation, and vice versa.

## Sensitivity-Specificity Trade-off

Scatter plot analysis of progression recall (sensitivity) against stable-case recall (specificity) across all 15 models (Figure 4) revealed a clear negative trend (Spearman rho = -0.31).

> **[Insert Figure 4 here]**

Models positioned in the upper-left quadrant, such as DiffusionGemma and MedSeek, achieved high progression sensitivity (71% to 73%) at the cost of lower specificity (78% to 82%), meaning they flagged more true progressions but also overcalled progression in stable cases. Models in the lower-right quadrant, such as Qwen3.5 and GPT-5.4, achieved higher specificity (76% to 81%) but lower progression sensitivity (60% to 64%), meaning they correctly identified more stable cases but missed more true progressions. This trade-off has direct clinical implications: in a high-risk postoperative surveillance setting where missing a progression is particularly dangerous, a high-sensitivity model may be preferable despite the increased false-positive rate. In a low-prevalence screening context, specificity may be more important to avoid unnecessary follow-up. No model achieved both high sensitivity and high specificity, indicating that this trade-off is a fundamental property of current LLM reasoning on this task rather than a limitation addressable by model selection alone.

## Fatal Error Distribution

Horizontal bar chart analysis of clinically consequential errors (Figure 5) provided a model-by-model comparison of the two most dangerous failure modes: misjudging true progression as stable (red bars) and missing documented metastatic disease (yellow bars).

> **[Insert Figure 5 here]**

The total number of these errors ranged from 11 (Step-3.7) to 25 (MedSeek), although the composition differed substantially. Step-3.7 achieved zero missed metastases but still had 13 progression misclassifications. MedSeek had 16 progression misclassifications and 9 missed metastases, the latter representing 40.9% of all metastasis-positive cases. GPT-5.4 had 17 progression misclassifications but only 2 missed metastases. This decomposition reveals that models with similar total error counts may have very different risk profiles: a model that misses metastases is clinically more dangerous than one that misses non-metastatic progressions, because missed metastasis directly affects stage and treatment selection.

## Correlation Structure of Model Performance

To systematically examine the relationships between tasks and subtasks, we computed a Spearman rank correlation matrix across the 15 models for all 10 primary metrics. Several findings emerged.

First, the T1 macro-F1 and T3 exact-match showed moderate correlation (rho = 0.621), confirming partial overlap in the underlying capabilities. However, progression recall and staging accuracy were essentially uncorrelated (rho = 0.030), indicating that longitudinal change detection and anatomic staging draw on largely independent skill sets.

Second, within the TNM staging components, N-category and M-category accuracy were strongly correlated (rho = 0.809), suggesting that models that can correctly identify nodal involvement also tend to correctly identify distant metastasis. T-category accuracy correlated only moderately with N (rho = 0.407) and weakly with M (rho = 0.316), reinforcing the finding that T-category inference is a distinct cognitive task that depends on integrating dimensional data and local invasion descriptors.

Third, impression generation quality (ROUGE-L) showed weak correlation with change assessment accuracy (rho = 0.184) and moderate correlation with staging accuracy (rho = 0.368). This pattern implies that textual fluency, as measured by lexical similarity to the radiologist's impression, is a poor proxy for clinical reasoning accuracy. A model that produces fluent, well-structured impressions may simultaneously fail at the core clinical reasoning tasks that those impressions are meant to summarize.

Fourth, stable-case recall and progression recall were negatively correlated (rho = -0.31), formalizing the sensitivity-specificity trade-off observed in the error analysis: models that are more aggressive in detecting progression (higher progression recall) tend to generate more false positives among stable cases (lower stable recall). This trade-off has direct clinical implications, as the acceptable balance depends on the downstream consequences of each error type in a given clinical workflow.

---

# Discussion

This study presents ThoracicOncoBench, a longitudinal, oncology-grounded benchmark for evaluating large language models on thoracic CT report interpretation, and reports the performance of 15 current models against hospital-validated reference standards including pathology-confirmed TNM staging. The principal findings are threefold. First, all evaluated models, regardless of category or specialization, failed to identify a substantial proportion of true disease progressions, with progression recall ranging from 51% to 73% and fatal error rates of 10.6% to 18.3% among progression cases. Second, TNM staging accuracy against pathology-confirmed reference standards was uniformly poor, with T-category accuracy not exceeding 43.2% for any model despite explicit textual descriptions of lesion dimensions. Third, no model was uniformly superior across tasks, and the capabilities required for change assessment, staging inference, and impression generation were partially dissociable, as evidenced by moderate inter-task correlations and distinct per-model profiles.

These findings carry direct clinical implications. Large language models are transitioning from research curiosities to deployed clinical tools at an unprecedented pace. Several health systems have already integrated generative AI into radiology workflows for report drafting, impression suggestion, and worklist triage,(7) and regulatory pathways for AI-assisted clinical decision support are being actively shaped by agencies worldwide. In oncologic imaging specifically, the stakes of this transition are particularly high: the conclusions encoded in a radiology report determine whether a patient proceeds to surgery, receives systemic therapy, enrolls in a clinical trial, or continues surveillance. If language models are to participate in generating or verifying these conclusions, their reasoning capabilities must be evaluated against the same standards that govern clinical decision-making, not merely against the surface text of a prior radiologist's report. ThoracicOncoBench was designed to fill exactly this gap. By anchoring reference standards to pathology-confirmed staging and prospectively collected survival outcomes from a National Cancer Center, the benchmark evaluates whether models can reach the conclusions that the multidisciplinary oncology team actually reached and acted upon. The results reveal that current models, including those specifically marketed for medical use, are not yet capable of meeting this clinical standard: every evaluated model missed between 27% and 49% of true disease progressions, and no model achieved T-category staging accuracy above 43.2%. These performance gaps have immediate practical implications for institutions considering AI deployment, for regulators evaluating model safety, and for developers prioritizing the next generation of capabilities.

In thoracic oncologic practice, the determination of disease progression on follow-up imaging is a decision point of the highest consequence. Current guidelines for non-small cell lung cancer specify that disease progression on imaging may trigger a change from surveillance to active systemic therapy, initiation of second-line treatment, or referral for clinical trial enrollment. A model that misclassifies 11% to 18% of true progressions as stable, as observed across the evaluated models, would, if deployed in an autonomous decision-support role, introduce an unacceptable risk of delayed treatment escalation. Similarly, TNM staging governs whether a patient is offered surgical resection, definitive chemoradiation, or systemic therapy. T-category accuracy below 44% for all models indicates that current systems cannot reliably infer even the primary tumor category from explicit radiologic descriptions, let alone from imaging data directly.

The finding that medical-specialized models did not consistently outperform general-purpose models is noteworthy and has implications for the development of medical AI systems. Two of the six medical-specialized models (MediPhi and QwQ-Med-3) performed near or below the majority-class baseline on several tasks, while others (MedSeek, MediX) achieved top-tier results on specific metrics. This heterogeneity suggests that the label "medical-specialized" encompasses a wide range of approaches, from models fine-tuned on medical examination questions to those trained on clinical text corpora, and that the specific training methodology matters more than the domain label. Developers and clinicians evaluating medical AI systems should therefore rely on task-specific benchmark performance rather than on marketing claims of medical specialization.(23)

The moderate correlation between change-assessment macro-F1 and staging exact-match (rho = 0.621), combined with the near-zero correlation between progression recall and staging accuracy (rho = 0.030), reveals an important structural property of the evaluated tasks. The ability to classify the overall direction of change from longitudinal narratives and the ability to infer anatomic staging from a single report appear to draw on partially overlapping but distinct capabilities. This finding suggests that future benchmarks and model development efforts should evaluate these capabilities separately rather than relying on a single composite score.

The error analysis revealed two distinct strategies that models employ when faced with progression cases. Some models, such as DiffusionGemma, tend to commit to a definitive judgment even under uncertainty, resulting in a low rate of "mixed" classifications but a higher rate of direct misclassification as "stable." Others, such as Step-3.7, preferentially output "mixed" when facing competing signals, which reduces direct misclassification rates but increases the proportion of progressions that go unflagged. From a clinical workflow perspective, neither strategy is clearly superior: a false "stable" judgment risks delayed treatment, while a "mixed" judgment may prompt unnecessary additional workup. Understanding these bias profiles is essential for clinicians and institutions considering deployment, as the acceptable error profile depends on the specific clinical context and the downstream consequences of each error type.

The inter-component correlation analysis of TNM staging (N and M strongly correlated at rho = 0.809; T weakly correlated with both) suggests that models may develop nodal and metastatic assessment capabilities in tandem, while T-category inference lags behind. This may reflect the fact that T-category determination requires integrating multiple textual cues, including lesion dimensions, invasion of adjacent structures, and distance from the carina, whereas N and M categories can often be inferred from the presence or absence of described lymphadenopathy or distant lesions.

The systematic correlation analysis across all metrics (Figure 4) further revealed that the negative relationship between stable-case recall and progression recall (rho = -0.31) formalizes a fundamental sensitivity-specificity trade-off that has important implications for model selection in clinical practice. Models optimized for high sensitivity (catching every possible progression) will inevitably generate more false alarms among the majority of stable examinations, potentially increasing radiologist workload rather than reducing it. Conversely, conservative models that minimize false positives will miss a higher proportion of true progressions. The appropriate trade-off point depends on the specific clinical deployment context: in a high-risk postoperative surveillance setting, maximizing progression sensitivity may be worth the cost of additional false alarms, whereas in a low-prevalence screening context, specificity may be prioritized. This finding argues for context-specific model evaluation and against the notion of a single "best" model.

The near-zero correlation between impression generation quality and change assessment accuracy (rho = 0.184) merits particular emphasis. This finding empirically demonstrates that the ability to produce fluent, lexically appropriate impression text is nearly orthogonal to the ability to correctly reason about clinical change. This has profound implications for how medical AI systems are evaluated: benchmarks that rely solely on text-similarity metrics may rank models in an order that is irrelevant or even misleading for clinical reasoning tasks. The medical AI community has previously raised this concern on theoretical grounds,(21,22) and the present results provide the first empirical quantification of this dissociation using pathology-confirmed reference standards.

This study has several strengths. The benchmark is the first to evaluate longitudinal change assessment and TNM staging inference against pathology-confirmed reference standards, rather than against subjective radiologist-authored text. The use of clinically validated data from a National Cancer Center, where all reports underwent dual-reading quality review and all staging was confirmed by board-certified pathologists, ensures that the reference standards reflect the conclusions that actually governed patient management. The evaluation of 15 models spanning three categories provides a comprehensive snapshot of the current landscape. The negation-aware gold-standard extraction methodology addresses a known pitfall in natural language processing of clinical text, where negated findings can be erroneously classified as positive if negation context is not detected. The introduction of a fatal error rate metric, computed specifically among progression cases, provides a clinically interpretable measure of the most dangerous failure mode.

Several limitations should be acknowledged. First, the benchmark is derived from a single institution and is in Chinese, which may limit generalizability to other languages and healthcare settings. Second, the Task 1 reference standard was derived by automated extraction with negation detection; while this approach was validated against manual review, it cannot fully replicate the nuanced clinical judgment of an experienced radiologist. Third, the number of progression cases (n = 104) and metastasis cases (n = 22) is limited, resulting in wide confidence intervals that preclude definitive claims about statistically significant differences between individual models on these subtasks. Fourth, TNM staging was evaluated only on the 213 temporally aligned instances, as including postoperative or surveillance scenarios would introduce temporal mismatch between imaging and pathology. Fifth, the benchmark evaluates text-level reasoning only; it does not assess image interpretation capability, which would require a multimodal evaluation framework. Sixth, all models were evaluated under zero-shot prompting; few-shot or fine-tuned performance may differ but was not assessed to maintain comparability and prevent information leakage.

In conclusion, ThoracicOncoBench provides a standardized, pathology-anchored evaluation framework that reveals substantial gaps in current large language models for longitudinal oncologic reasoning and TNM staging. These gaps, including the failure to detect over one-quarter of true disease progressions and the inability to correctly infer T-category from explicit textual descriptions, carry direct implications for the safe deployment of language models in oncologic decision-making. The benchmark, scoring scripts, and baseline predictions will be made publicly available to enable reproducible evaluation of future models.

---

# Tables

## Table 1. Overall Performance Ranking (15 Models)

| Rank | Model | Type | T1 Acc | T1 F1 | T3 Exact | T3-T | T3-N | T3-M | T4 ROUGE | Fatal/104 |
|------|-------|------|--------|-------|----------|------|------|------|----------|-----------|
| 1 | DiffusionGemma | General | .776 | .527 | .197 | .35 | .45 | .38 | .408 | .183 |
| 2 | MedSeek | Medical | .750 | **.657** | **.258** | **.40** | **.57** | **.67** | .335 | .154 |
| 3 | HuatuoGPT | Medical | .743 | .474 | .127 | .38 | .42 | .49 | .234 | .154 |
| 4 | GPT-5.4 | Frontier | .739 | .511 | .249 | .37 | **.70** | **.80** | .298 | .164 |
| 5 | Gemini-3.5 | Frontier | .728 | .497 | .122 | .22 | .47 | .52 | .338 | .144 |
| 6 | AntAngelMed | Medical | .713 | .468 | .150 | .33 | .42 | .38 | .252 | .164 |
| 7 | Nemotron-3 | General | .706 | .478 | .136 | .34 | .64 | .49 | .256 | .135 |
| 8 | MediX | Medical | .673 | .455 | .141 | **.43** | .32 | .23 | .341 | .115 |
| 9 | Qwen3.5 | General | .673 | .469 | .061 | .26 | .22 | .14 | .359 | .115 |
| 10 | Step-3.7 | General | .671 | .553 | .216 | .36 | .56 | .69 | .323 | .125 |
| 11 | Baichuan-M3 | Frontier | .666 | .553 | .164 | .38 | .54 | .46 | .352 | .135 |
| 12 | Minimax | General | .665 | .449 | .169 | .35 | .50 | .58 | .293 | .115 |
| 13 | DeepSeek-V4 | General | .658 | .462 | .188 | .32 | .51 | .53 | **.436** | .106 |
| 14 | MediPhi | Medical | .650 | .421 | .005 | .005 | .05 | .01 | .189 | .115 |
| 15 | QwQ-Med-3 | Medical | .638 | .441 | .094 | .22 | .41 | .47 | .090 | .125 |

Majority-class baseline (all-stable): T1 accuracy = 65.9%. T3 exact-match was evaluated on n = 213 temporally aligned instances. Fatal/104 = fatal error rate among the 104 progression cases.

## Table 2. Fatal Error Analysis

| Model | Prog to Stable (fatal) | Missed Mets (n=22) | Fatal/104 (95% CI) |
|-------|----------------------|--------------------|---------------------|
| DeepSeek-V4 | 11 | 3 | .106 [.06, .18] |
| Qwen3.5 | 12 | 2 | .115 [.07, .19] |
| MediPhi | 12 | 3 | .115 [.07, .19] |
| MediX | 12 | 5 | .115 [.07, .19] |
| Minimax | 12 | 6 | .115 [.07, .19] |
| Step-3.7 | 13 | 0 | .125 [.07, .20] |
| QwQ-Med-3 | 13 | 4 | .125 [.07, .20] |
| Baichuan-M3 | 14 | 2 | .135 [.08, .21] |
| Nemotron-3 | 14 | 3 | .135 [.08, .21] |
| Gemini-3.5 | 15 | 4 | .144 [.09, .22] |
| MedSeek | 16 | 9 | .154 [.10, .23] |
| HuatuoGPT | 16 | 7 | .154 [.10, .23] |
| GPT-5.4 | 17 | 2 | .164 [.10, .25] |
| AntAngelMed | 17 | 3 | .164 [.10, .25] |
| DiffusionGemma | 19 | 6 | .183 [.12, .27] |

---

# References

1. Hosny A, Parmar C, Quackenbush J, Schwartz LH, Aerts HJWL. Artificial intelligence in radiology. *Nat Rev Cancer.* 2018;18(8):500-510.

2. Rajpurkar P, Lungren MP. The current and future state of AI interpretation of medical images. *N Engl J Med.* 2023;388(21):1981-1990.

3. Shen Y, Heacock L, Elias J, et al. ChatGPT and other large language models are double-edged swords. *Radiology.* 2023;307(2):e230163.

4. Sun Z, Ong H, Kennedy P, et al. Evaluating GPT-4 on impressions generation in radiology reports. *Radiology.* 2023;307(5):e231259.

5. Serapio A, Kamel SI, Brown AE, et al. An open-source fine-tuned large language model for radiological impression generation: a multi-reader performance study. *BMC Med Imaging.* 2024;24(1):254.

6. Hong EK, Roh B, Park B, et al. Value of using a generative AI model in chest radiography reporting: a reader study. *Radiology.* 2025;314(3):e241646.

7. Huang J, Wittbrodt MT, Teague CN, et al. Efficiency and quality of generative AI-assisted radiograph reporting. *JAMA Netw Open.* 2024;7(10):e2436100.

8. Li M, Wang Y, et al. Fine-tuned large language model for automated radiology impression generation: a multicenter evaluation [MIRA]. *Radiol Artif Intell.* 2026;8(3):e250714.

9. Peeters D, Obreja B, Antonissen N, et al; LUNA25 Consortium. Benchmarking of AI and radiologists for indeterminate lung nodule malignancy risk estimation on screening CT: the LUNA25 challenge. *Radiol Artif Intell.* 2026. doi:10.1148/ryai.260179.

10. Setio AAA, Traverso A, de Bel T, et al. Validation, comparison, and combination of algorithms for automatic detection of pulmonary nodules in computed tomography images: the LUNA16 challenge. *Med Image Anal.* 2017;42:1-13.

11. MedGemma 1.5 technical report. *arXiv.* 2026. Preprint posted online May 2026.

12. Tejani AS, Klontzas ME, Gatti AA, et al; CLAIM 2024 Update Panel. Checklist for Artificial Intelligence in Medical Imaging (CLAIM): 2024 update. *Radiol Artif Intell.* 2024;6(4):e240300.

13. von Elm E, Altman DG, Egger M, et al. The Strengthening the Reporting of Observational Studies in Epidemiology (STROBE) statement. *J Clin Epidemiol.* 2008;61(4):344-349.

14. Maier-Hein L, Reinke A, Kozubek M, et al. BIAS: transparent reporting of biomedical image analysis challenges. *Med Image Anal.* 2020;66:101796.

15. Amin MB, Edge SB, Greene FL, et al, eds. *AJCC Cancer Staging Manual.* 8th ed. New York, NY: Springer; 2017.

16. Lin CY. ROUGE: a package for automatic evaluation of summaries. In: *Text Summarization Branches Out: Proceedings of the ACL-04 Workshop.* Barcelona: Association for Computational Linguistics; 2004:74-81.

17. Zhang T, Kishore V, Wu F, et al. BERTScore: evaluating text generation with BERT. *arXiv.* 2019. Preprint posted online April 2019.

18. Yang A, Chen J, Lu J, et al. Qwen2.5 technical report. *arXiv.* 2024. Preprint posted online December 2024.

19. Achiam J, Adler S, Agarwal S, et al. GPT-4 technical report. *arXiv.* 2023. Preprint posted online March 2023.

20. Eisenhauer EA, Therasse P, Bogaerts J, et al. New response evaluation criteria in solid tumours: revised RECIST guideline (version 1.1). *Eur J Cancer.* 2009;45(2):228-247.

21. Wornow M, Xu Y, Thapa R, et al. The shaky foundations of large language models and foundation models for electronic health records. *npj Digit Med.* 2023;6(1):1-10.

22. Li H, Moon JT, Sekhon S, et al. The ethics of large language models in medicine and medical research. *Lancet Digit Health.* 2023;5(6):e333-e335.

23. Mahmood F. A benchmarking crisis in biomedical machine learning. *Nat Med.* 2024;30(1):1-2.

24. MedSeek: a medical large language model for clinical reasoning. Available at: https://medseek.meduc.cn. Accessed [date].

25. Dedhia B, Kansal Y, Jha NK. Bottom-up domain-specific superintelligence: a reliable knowledge graph is what we need. *arXiv.* 2025. doi:10.48550/arXiv.2507.13966. Preprint posted online July 2025.

---

# Figure Legends

**Figure 1.** Study flow diagram depicting the progression from raw clinical data (17,355 chest CT reports and oncology outcomes registry) through patient-level linkage, quality-first stratified sampling, and final benchmark composition (1,995 instances from 1,670 patients). The three task families and their respective reference-standard sources are color-coded.

**Figure 2.** T1 change assessment confusion matrices for four representative models (GPT-5.4, Gemini-3.5, Nemotron-3, Qwen3.5). Rows represent gold-standard labels and columns represent model predictions. Diagonal entries indicate correct classifications.

**Figure 3.** Grouped bar chart of TNM per-component staging accuracy (T, N, M) for all 15 models, sorted by overall staging exact-match accuracy. Red bars represent T-category accuracy, blue bars represent N-category accuracy, and green bars represent M-category accuracy. The dashed horizontal line indicates random guessing level (33.3% for a four-category classification). The divergent bar heights across components illustrate that models achieving high accuracy on one component frequently underperform on others.

**Figure 4.** Scatter plot of progression recall (sensitivity, y-axis) against stable-case recall (specificity, x-axis) for all 15 models. Blue circles represent general-purpose and frontier models; red squares represent medical-specialized models. The dashed trend line illustrates the negative correlation (rho = -0.31), confirming a sensitivity-specificity trade-off. No model achieves both high sensitivity and high specificity. Labels identify representative models in each quadrant.

**Figure 5.** Stacked horizontal bar chart of clinically consequential errors by model, ranked by total error count. Red bars represent the number of true progression cases (of 104) misjudged as stable. Yellow bars represent the number of metastasis-positive cases (of 22) missed. The total count at the end of each bar indicates the combined clinically consequential error burden. Models with similar total counts may have very different risk profiles depending on the proportion of missed metastases.
