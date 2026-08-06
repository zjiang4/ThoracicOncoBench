Cover Letter

[Date]

Editor-in-Chief
Radiology: Artificial Intelligence
Radiological Society of North America
820 Jorie Boulevard
Oak Brook, IL 60523

Dear Editor:

We are pleased to submit our manuscript entitled "ThoracicOncoBench: A Benchmark for Evaluating Large Language Models on Longitudinal Thoracic Oncologic Imaging Report Interpretation" for consideration by Radiology: Artificial Intelligence.

The integration of large language models into radiology workflows is accelerating at an unprecedented pace, such as (1) the MIRA (Multimodal Interventional RAdiology evaluation) study, which demonstrated that a fine-tuned model can generate radiology impressions from 1.87 million reports across 42 Chinese centers, and (2) the LUNA25 challenge, which benchmarked AI against 65 radiologists for nodule malignancy estimation. These landmark contributions have defined the frontier. Yet both studies, like every prior evaluation in this field, share a common structural limitation: they assess single-timepoint, cross-sectional performance against radiologist-authored reference text. They do not test whether models can perform the longitudinal reasoning and staging inference that actually govern treatment decisions in oncologic care, and they do not use pathology-confirmed outcomes as the reference standard.

ThoracicOncoBench was designed to fill this gap.

Our benchmark is constructed from 17,355 consecutive chest CT reports from 9,334 patients at Peking University Cancer Hospital, a National Cancer Center where every report undergoes institutional dual-reading quality review by board-certified radiologists and every TNM staging is confirmed by board-certified pathologists. By linking these two clinically validated data sources, we created 1,995 benchmark instances that test four task families: longitudinal change assessment (determining whether disease has progressed, regressed, or remained stable), structured oncologic finding extraction, clinical TNM staging inference, and impression generation. The reference standards are not subjective text comparisons; they are the pathology-confirmed staging and survival outcomes that governed actual patient management.

We evaluated 15 large language models spanning closed-source frontier models (GPT-5.4, Gemini-3.5-flash, Baichuan-M3), open-source general-purpose models (Nemotron-3-Ultra, Qwen3.5-397B, DiffusionGemma-26B, Step-3.7-flash, DeepSeek-V4, Minimax-M2.7), and medical-specialized models (MedSeek, HuatuoGPT, AntAngelMed, MediPhi, MediX, QwQ-Med-3). To our knowledge, this is the most comprehensive multi-model evaluation of clinical reasoning capability in thoracic oncologic imaging to date.

The results, we believe, will be of considerable interest to your readership for three reasons.

First, the findings are clinically actionable and carry patient-safety implications. Every evaluated model, regardless of its category or medical specialization, failed to identify between 27% and 49% of true disease progressions. Fatal error rates, defined as judging a progressing examination as stable, ranged from 10.6% to 18.3% among the 104 progression cases. T-category staging accuracy did not exceed 43.2% for any model, despite explicit textual descriptions of lesion dimensions. These are not marginal performance gaps; they are deficits of a magnitude that, if such systems were deployed autonomously, could result in delayed treatment escalation for patients with active disease.

Second, the results challenge prevailing assumptions about medical-specialized models. The six medical-specialized models in our evaluation did not consistently outperform general-purpose models. MediPhi achieved near-zero staging accuracy (0.5%), while MedSeek achieved the highest macro-F1 (0.657) and staging exact-match (25.8%) among all models. This heterogeneity demonstrates that the label "medical-specialized" is not a reliable predictor of clinical reasoning performance, a finding with direct implications for model selection, regulatory review, and procurement decisions.

Third, the benchmark introduces methodological innovations that we believe will be adopted by future studies. The negation-aware gold-standard extraction methodology addresses a known pitfall in clinical NLP. The fatal error rate metric, computed among progression cases rather than across all instances, provides a clinically interpretable measure of the most dangerous failure mode. The sensitivity-specificity trade-off analysis (Figure 4) formalizes a fundamental property of model behavior that has been discussed theoretically but never empirically quantified against pathology-confirmed reference standards.

We have made the complete benchmark, frozen scoring script, prompt templates, and all 15 sets of baseline predictions available for public evaluation. Our intention is for ThoracicOncoBench to serve as a living benchmark that the community can use to track progress as new models are developed, analogous to how LUNA16 and LUNA25 have served the computer-vision community.

This manuscript has not been published previously and is not under consideration elsewhere. All authors have read and approved the submission. The authors have no relevant conflicts of interest to disclose. The study was approved by the institutional review board with a waiver of informed consent.

We believe this work aligns closely with the mission of Radiology: Artificial Intelligence to publish rigorous, clinically grounded evaluations of AI systems in medical imaging, and we are confident that it will be of substantial interest to your readership.

Thank you for your consideration. We look forward to your response.

Sincerely,

[Corresponding Author Name]
[Title]
[Department]
[National Cancer Center]
[Address]
[Email]
[Telephone]
