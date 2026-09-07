"""ThoracicOncoBench longitudinal-change label engine v0.4.0.

Clinical grounding:
- The finalized impression is the dual-audited final synthesis of the reporting
  radiologist (trainee/attending draft + senior-radiologist approval) and is
  treated as the authoritative longitudinal conclusion (impression priority).
- RECIST 1.1 (Eisenhauer et al., Eur J Cancer 2009): a new lesion defines
  progressive disease; >=20% diameter increase with >=5 mm absolute increase
  supports progression; >=30% diameter decrease supports regression; absence
  of meaningful change supports stable disease. Single-lesion paired
  measurements extracted from routine reports are RECIST-informed, not
  RECIST-compliant (no formal target-lesion sums or nadir).
- iRECIST (Seymour et al., Lancet Oncol 2017): only unequivocal new/progressive
  disease counts as progression; equivocal or hedged statements are downgraded
  out of the primary set.
"""

import re
from dataclasses import dataclass, field

PARSER_VERSION = "v0.4.0"

LABELS = ("progression", "regression", "stable", "mixed", "indeterminate")
TIERS = ("definitive", "quantitative", "directional", "suspicious", "weak", "indeterminate")

RULE_DESCRIPTIONS = {
    "RECIST-PD-IMPRESSION": "Dual-audited final impression explicitly concludes progression, recurrence, or worsening.",
    "RECIST-PD-NEW-LESION": "New oncologic lesion or new metastatic disease documented (RECIST 1.1: new lesion defines progressive disease).",
    "RECIST-PD-QUANTITATIVE": "Paired lesion measurements meet RECIST-informed progression threshold (>=20% and >=5 mm increase).",
    "RECIST-PD-QUANTITATIVE-SUPPORT": "Report-level supportive measurement signal; not a full RECIST sum-of-diameters assessment.",
    "RECIST-PD-DIRECTIONAL": "Findings document explicit comparative worsening language (e.g., 较前增大/增多).",
    "RECIST-PR-IMPRESSION": "Dual-audited final impression explicitly concludes improvement, response, or regression.",
    "RECIST-PR-QUANTITATIVE": "Paired lesion measurements meet RECIST-informed regression threshold (>=30% decrease).",
    "RECIST-PR-DIRECTIONAL": "Findings document explicit comparative improvement language (e.g., 较前缩小/吸收).",
    "RECIST-SD-IMPRESSION": "Dual-audited final impression explicitly concludes no meaningful change.",
    "RECIST-SD-DIRECTIONAL": "Findings explicitly document no meaningful change or explicitly negated progression.",
    "RECIST-MIXED-IMPRESSION": "Dual-audited final impression documents concurrent worsening and improvement.",
    "RECIST-MIXED-DIRECTIONAL": "Findings document concurrent worsening and improvement across disease sites.",
    "MEASUREMENT-BELOW-RECIST-INFORMED-THRESHOLD": "Paired measurements extracted but change does not meet RECIST-informed thresholds.",
    "QUALITY-EXPLICIT-COMPARISON": "Primary labels require explicit comparison language in findings or impression.",
    "QUALITY-IMPRESSION-PRIORITY": "The dual-audited impression is the primary synthesis; explicit disease-relevant conflict with a stable impression is quarantined as indeterminate.",
    "QUALITY-IMPRESSION-SUPPORTED": "Primary labels are supported by the dual-audited final impression.",
    "QUALITY-UNCERTAINTY-DOWNGRADE": "Hedged or equivocal statements (iRECIST: not unequivocal) are downgraded out of the primary set.",
    "QUALITY-POSTOP-INFLAMMATORY-FLAG": "Postoperative or inflammatory co-text downgrades findings-level progression evidence.",
    "QUALITY-ONCOLOGIC-SCOPE": "Progression/regression evidence must refer to malignant disease burden, not a non-oncologic complication.",
    "QUALITY-NONONCOLOGIC-DOWNGRADE": "Effusion, pneumothorax, atelectasis, infection, fibrosis, and postoperative change are not tumor progression endpoints.",
    "QUALITY-CONSISTENCY-MET-PROGRESSION": "New metastatic disease must be labeled progression or mixed, never stable or regression.",
    "QUALITY-INDETERMINATE": "Insufficient, conflicting, or negated-only evidence.",
    "QUALITY-INDETERMINATE-CONFLICT": "Definitive new-metastasis evidence conflicts with a stable impression conclusion.",
}

_SENT_SPLIT = re.compile(r"[。；;！？\n]+")
_ITEM_NO = re.compile(r"^\s*\d+\s*[\.、）)]?\s*")

NEG_TERMS = ("未", "除外", "排除", "无")
UNCERTAINTY_HARD = ("可能", "可疑", "待排", "待鉴别", "待查", "待定", "不除外", "倾向", "性质待定", "鉴别")
UNCERTAINTY_SOFT = ("请结合", "建议复查", "建议追查", "密切追查", "密切观察", "随访", "追查", "复查")
UNCERTAINTY_TERMS = UNCERTAINTY_HARD + UNCERTAINTY_SOFT
SOFT_CHANGE_TERMS = ("略增大", "稍增大", "轻度增大", "轻微增大", "小幅增大", "略增多", "稍增多",
                     "轻度增多", "轻微增多", "略缩小", "稍缩小", "轻度缩小", "轻微缩小")
POSTOP_INFLAMM_TERMS = ("术后", "陈旧", "纤维", "瘢痕", "炎性", "炎症", "感染", "结核", "放疗", "栓塞后")
BENIGN_TERMS = ("反应性", "良性", "倾向良性", "炎性", "炎症", "感染", "结核", "瘢痕", "陈旧", "术后")
NON_ONCOLOGIC_TERMS = ("胸水", "胸腔积液", "心包积液", "积气", "气胸", "液气胸", "肺不张", "膨胀不全",
                       "实变", "斑片影", "片絮影", "条索影", "纤维化", "肺气肿", "肺大泡", "支气管扩张",
                       "炎症", "炎性", "感染", "脓肿", "瘘", "漏", "术后改变", "手术后")
ONCOLOGIC_TERMS = ("肿瘤", "肿块", "肿物", "癌", "恶性", "病灶", "结节", "淋巴结", "转移", "复发",
                   "胸膜结节", "胸膜转移", "骨质破坏", "破坏灶", "软组织占位", "占位", "播散", "种植", "癌栓")
COMPARE_MARKERS = ("较前", "与前次", "较前片", "较以前", "与前片", "对比前片", "较前次")
PROG_INHERENT = ("进展", "复发", "加重", "恶化")
PROG_COMPARE_VERBS = ("增大", "增多", "增粗")
REG_INHERENT = ("好转", "缓解")
REG_COMPARE_VERBS = ("缩小", "减小", "减少", "吸收", "消退")
STABLE_TERMS = ("同前", "相仿", "稳定", "无明显变化", "未见明显变化", "未见明确变化", "未见变化", "未见新变化")
NEGOBS_PROG = re.compile(r"未[^，。；]{0,6}?(进展|增大|增多|复发|转移|新发|新增|新见|新出现)")
NEW_LESION = re.compile(r"(新发|新增|新见|新出现)[^，。；]{0,10}?(病灶|结节|肿块|占位|软组织|淋巴结|转移|破坏|骨质破坏)")
NEW_LESION_NEG = re.compile(r"(未见|无|未及)[^，。；]{0,6}?(新发|新增|新见|新出现|新)")
MET_TERMS = ("转移", "转移瘤", "转移灶", "骨质破坏", "破坏灶")
MET_NEW_CTX = re.compile(r"(新发|新增|新见|新出现)[^，。；]{0,12}?(转移|转移瘤|转移灶|骨质破坏|破坏灶)|(转移|转移瘤|转移灶)[^，。；]{0,8}?(较前|进展|增多|增大)|复发转移")
NUM = r"\d+(?:\.\d+)?"
UNIT = r"(?:mm|MM|毫米|cm|CM|厘米)"
_MEAS = re.compile(
    rf"约?(?P<a>{NUM})\s*(?:x|X|×|\*)\s*(?P<b>{NUM})\s*(?P<unit2>{UNIT})"
    rf"|约?(?P<c>{NUM})\s*(?P<unit1>{UNIT})"
)
_PRIOR_MARK = re.compile(r"(?:原|原来|原为|前次|术前|既往|上次|由|自)[^，。；]{0,8}$")
_CURR_MARK = re.compile(r"(?:现|本次|目前|增大至|增至|缩小至|减至|发展为|变化为)[^，。；]{0,8}$")


def _sentence_measurements(sentence):
    out = []
    for m in _MEAS.finditer(sentence):
        if m.group("a") is not None:
            nums = [float(m.group("a")), float(m.group("b"))]
            unit = m.group("unit2")
        else:
            nums = [float(m.group("c"))]
            unit = m.group("unit1")
        scale = 10.0 if unit.lower() in ("cm", "厘米") else 1.0
        nums = [n * scale for n in nums]
        # RECIST 1.1 uses the long axis for non-nodal lesions and the short
        # axis for lymph nodes.  Routine Chinese reports often provide both
        # axes in the same phrase, so preserve the pair and select the
        # disease-appropriate axis here.
        is_node = "淋巴结" in sentence or "结节" in sentence and "淋巴" in sentence
        val = min(nums) if is_node and len(nums) > 1 else max(nums)
        before = sentence[:m.start()]
        if _CURR_MARK.search(before[-14:]):
            role = "current"
        elif _PRIOR_MARK.search(before[-14:]):
            role = "prior"
        else:
            role = None
        out.append((role, val, m.group(0), is_node))
    return out


def _extract_measurements(sentences, section):
    out = []
    for s in sentences:
        meas = _sentence_measurements(s)
        priors = [x for x in meas if x[0] == "prior"]
        currs = [x for x in meas if x[0] == "current"]
        if len(priors) != 1 or len(currs) != 1:
            continue
        prior, current = priors[0][1], currs[0][1]
        if prior <= 0:
            continue
        rel = (current - prior) / prior
        if rel >= 0.20 and (current - prior) >= 5:
            direction, rule = "progression", "RECIST-PD-QUANTITATIVE"
        elif rel <= -0.30:
            direction, rule = "regression", "RECIST-PR-QUANTITATIVE"
        else:
            direction, rule = "below_threshold_change", "MEASUREMENT-BELOW-RECIST-INFORMED-THRESHOLD"
        out.append({
            "section": section, "sentence": s,
            "prior_mm": prior, "current_mm": current,
            "absolute_change_mm": round(current - prior, 2),
            "relative_change": round(rel, 4),
            "direction": direction, "rule_id": rule,
            "disease_relevant": _measurement_relevant(s),
            "uncertain": _uncertain(s),
            "measurement_axis": "short_axis" if (priors[0][3] or currs[0][3]) else "long_axis",
            "measurable_by_recist": max(prior, current) >= (15.0 if (priors[0][3] or currs[0][3]) else 10.0),
        })
    return out


RULE_ANCHORS = {
    "RECIST-PD-NEW-LESION": "RECIST 1.1 new-lesion criterion (Eisenhauer et al. 2009): appearance of one or more new malignant lesions defines progressive disease.",
    "RECIST-PD-QUANTITATIVE": "RECIST 1.1 target-lesion PD threshold (>=20% increase in diameter sum, >=5 mm absolute), adapted to report-documented measurable single-lesion pairs (long axis for non-nodal lesions; short axis for nodes).",
    "RECIST-PD-QUANTITATIVE-SUPPORT": "RECIST 1.1 is adapted only as report-level supportive evidence because formal target-lesion sums, nadir, and image review are unavailable.",
    "RECIST-PD-IMPRESSION": "Institutional dual-audit reporting workflow: the finalized impression is the senior-radiologist-approved synthesis (impression priority).",
    "RECIST-PD-DIRECTIONAL": "RECIST 1.1 PD definition (increase in extent of disease), instantiated by explicit radiologist-documented comparative worsening language.",
    "RECIST-PR-QUANTITATIVE": "RECIST 1.1 partial-response threshold (>=30% decrease in diameter sum), adapted to report-documented measurable single-lesion pairs (long axis for non-nodal lesions; short axis for nodes).",
    "RECIST-PR-IMPRESSION": "Institutional dual-audit reporting workflow: the finalized impression is the senior-radiologist-approved synthesis (impression priority).",
    "RECIST-PR-DIRECTIONAL": "RECIST 1.1 response definitions, instantiated by explicit radiologist-documented comparative improvement language.",
    "RECIST-SD-IMPRESSION": "Institutional dual-audit reporting workflow: the finalized impression is the senior-radiologist-approved synthesis (impression priority).",
    "RECIST-SD-DIRECTIONAL": "RECIST 1.1 stable disease: neither sufficient shrinkage to qualify for PR nor sufficient increase to qualify for PD.",
    "RECIST-MIXED-IMPRESSION": "Report-level extension beyond RECIST 1.1 categories: concurrent documented worsening and improvement in different disease sites.",
    "RECIST-MIXED-DIRECTIONAL": "Report-level extension beyond RECIST 1.1 categories: concurrent documented worsening and improvement in different disease sites.",
    "MEASUREMENT-BELOW-RECIST-INFORMED-THRESHOLD": "RECIST 1.1 stable disease: measured change does not meet PD or PR thresholds.",
    "QUALITY-EXPLICIT-COMPARISON": "Longitudinal assessment requires an explicit comparator; RECIST 1.1 response assessment is defined relative to baseline/nadir.",
    "QUALITY-IMPRESSION-PRIORITY": "Institutional dual-audit reporting workflow: the finalized impression is primary, while explicit disease-relevant conflict with a stable impression is quarantined as indeterminate.",
    "QUALITY-IMPRESSION-SUPPORTED": "Institutional dual-audit reporting workflow: primary labels rest on the senior-radiologist-approved impression.",
    "QUALITY-UNCERTAINTY-DOWNGRADE": "iRECIST (Seymour et al. 2017): only unequivocal new or progressive disease qualifies as progression; equivocal findings do not.",
    "QUALITY-POSTOP-INFLAMMATORY-FLAG": "RECIST 1.1 new-lesion criteria exclude lesions attributable to non-oncologic causes (postoperative/inflammatory); flagged as confounders.",
    "QUALITY-ONCOLOGIC-SCOPE": "RECIST 1.1 response categories apply to measurable/assessable malignant disease burden, not generic interval change in physiology or postoperative findings.",
    "QUALITY-NONONCOLOGIC-DOWNGRADE": "Non-oncologic changes are retained as provenance but cannot independently define tumor progression or response.",
    "QUALITY-CONSISTENCY-MET-PROGRESSION": "RECIST 1.1: new malignant lesions, including new metastatic disease, define progressive disease.",
    "QUALITY-INDETERMINATE": "RECIST 1.1 non-measurable/unevaluable disease analog: no reliable protocol mapping is possible.",
    "QUALITY-INDETERMINATE-CONFLICT": "iRECIST: unequivocal documentation conflicting across report sections cannot support a primary label.",
}


def split_sentences(text):
    if not text:
        return []
    out = []
    for raw in _SENT_SPLIT.split(text):
        s = _ITEM_NO.sub("", raw).strip()
        if s:
            out.append(s)
    return out


def _negated(sentence, idx):
    window = sentence[max(0, idx - 12):idx]
    return any(n in window for n in NEG_TERMS)


def _uncertain(sentence):
    # Soft recommendations are uncertainty when attached to a change claim:
    # "增大，追查/复查" is not an unequivocal RECIST progression statement.
    if any(u in sentence for u in UNCERTAINTY_HARD):
        return True
    if _soft_recommendation(sentence):
        has_change_claim = (
            any(t in sentence for t in PROG_INHERENT + PROG_COMPARE_VERBS + REG_INHERENT + REG_COMPARE_VERBS)
            or bool(NEW_LESION.search(sentence))
        )
        return has_change_claim
    return False


def _soft_recommendation(sentence):
    if any(t in sentence for t in ("请结合", "随访", "追查", "密切观察", "密切追查")):
        return True
    # "复查" can be part of the exam indication (e.g. "癌复查") and is
    # only uncertainty when phrased as an actual recommendation.
    return "复查" in sentence and any(t in sentence for t in ("建议", "密切", "后复查", "后再查"))


def _soft_change(sentence, idx=None):
    ctx = _local_context(sentence, idx, window=18)
    return any(t in ctx for t in SOFT_CHANGE_TERMS)


def _new_lesion_is_unequivocal(sentence, idx=None):
    """RECIST/iRECIST gate for generic new nodules or lesions.

    A generic new small nodule is not automatically a new malignant lesion.
    Definitive progression requires explicit malignant/metastatic context;
    otherwise the trigger remains suspicious/secondary for adjudication.
    """
    ctx = _local_context(sentence, idx, window=28)
    malignant = ("转移" in ctx or "复发" in ctx or "恶性" in ctx or "肿瘤" in ctx
                 or "癌" in ctx or "占位" in ctx or "肿块" in ctx or "肿物" in ctx
                 or "骨质破坏" in ctx or "破坏灶" in ctx)
    generic_small = any(t in ctx for t in ("微小结节", "小结节", "结节")) and not malignant
    return malignant and not generic_small


def _local_context(sentence, idx=None, window=24):
    if idx is None:
        return sentence
    return sentence[max(0, idx - window):min(len(sentence), idx + window)]


def _oncologic_context(sentence, idx=None):
    """Return whether a change is plausibly about malignant disease burden.

    Radiology reports routinely contain longitudinal changes unrelated to
    tumor burden (effusion, atelectasis, infection, postoperative change).
    RECIST progression should not be inferred from those findings alone.
    Explicit malignant terms take precedence over generic inflammatory or
    postoperative co-text.
    """
    ctx = _local_context(sentence, idx)
    explicit = any(t in ctx for t in ("转移", "复发", "恶性", "肿瘤", "癌", "肿块", "肿物", "占位", "播散", "种植"))
    has_onc = any(t in ctx for t in ONCOLOGIC_TERMS)
    if not has_onc:
        return False
    if explicit:
        return True
    # Generic nodules/nodes/lesions are not malignant by themselves when the
    # same sentence offers a benign, inflammatory, or postoperative account.
    if any(t in ctx for t in BENIGN_TERMS):
        return False
    if any(t in ctx for t in NON_ONCOLOGIC_TERMS) and not any(t in ctx for t in ("胸膜结节", "骨质破坏")):
        return False
    return True


def _stable_context(sentence, idx=None):
    ctx = _local_context(sentence, idx)
    if any(t in ctx for t in ("未见新发结节", "未见新增结节", "未见新生结节", "未见转移", "未见复发")):
        return True
    return _oncologic_context(sentence, idx)


def _measurement_relevant(sentence):
    return _oncologic_context(sentence) and not (
        any(t in sentence for t in NON_ONCOLOGIC_TERMS)
        and not any(t in sentence for t in ("肿瘤", "肿块", "肿物", "癌", "恶性", "转移", "复发", "骨质破坏"))
    )


def _has_compare(sentence, idx):
    return any(c in sentence[max(0, idx - 10):idx + 4] for c in COMPARE_MARKERS)


def _postop_inflam(sentence):
    return any(p in sentence for p in POSTOP_INFLAMM_TERMS)


@dataclass
class Evidence:
    category: str
    strength: str
    term: str
    section: str
    sentence: str
    rule: str


@dataclass
class LabelResult:
    change: str
    new_metastatic_disease: bool
    evidence_tier: str
    confidence: str
    primary_eligible: bool
    primary_rule: str
    protocol_rule_ids: list = field(default_factory=list)
    triggers: list = field(default_factory=list)
    metastasis_triggers: list = field(default_factory=list)
    measurement_evidence: list = field(default_factory=list)
    flags: dict = field(default_factory=dict)
    impression_conclusion: list = field(default_factory=list)


def _scan_directional(sentences, section):
    evs = []
    for s in sentences:
        for m in NEW_LESION.finditer(s):
            if NEW_LESION_NEG.search(s[max(0, m.start() - 8):m.start()]):
                continue
            if not _oncologic_context(s, m.start()):
                continue
            neg = _negated(s, m.start())
            unc = _uncertain(s)
            postop = _postop_inflam(s)
            if neg:
                continue
            unequivocal_new = _new_lesion_is_unequivocal(s, m.start())
            strength = "definitive" if (not unc and not postop and unequivocal_new) else "suspicious"
            evs.append(Evidence("progression", strength, m.group(0), section, s, "RECIST-PD-NEW-LESION"))
        for term in PROG_INHERENT:
            for m in re.finditer(term, s):
                if not _oncologic_context(s, m.start()):
                    continue
                if _negated(s, m.start()):
                    continue
                unc = _uncertain(s)
                postop = _postop_inflam(s)
                strength = "definitive" if (not unc and not postop and not _soft_change(s, m.start())) else "suspicious"
                evs.append(Evidence("progression", strength, term, section, s, "RECIST-PD-DIRECTIONAL"))
        for term in PROG_COMPARE_VERBS:
            for m in re.finditer(term, s):
                if not _oncologic_context(s, m.start()):
                    continue
                if not _has_compare(s, m.start()):
                    continue
                if _negated(s, m.start()):
                    continue
                unc = _uncertain(s)
                postop = _postop_inflam(s)
                strength = "definitive" if (not unc and not postop and not _soft_change(s, m.start())) else "suspicious"
                evs.append(Evidence("progression", strength, term, section, s, "RECIST-PD-DIRECTIONAL"))
        for term in REG_INHERENT:
            for m in re.finditer(term, s):
                if not _oncologic_context(s, m.start()):
                    continue
                if _negated(s, m.start()):
                    continue
                strength = "definitive" if not _uncertain(s) and not _soft_change(s, m.start()) else "suspicious"
                evs.append(Evidence("regression", strength, term, section, s, "RECIST-PR-DIRECTIONAL"))
        for term in REG_COMPARE_VERBS:
            for m in re.finditer(term, s):
                if not _oncologic_context(s, m.start()):
                    continue
                if not _has_compare(s, m.start()):
                    continue
                if _negated(s, m.start()):
                    continue
                strength = "definitive" if not _uncertain(s) and not _soft_change(s, m.start()) else "suspicious"
                evs.append(Evidence("regression", strength, term, section, s, "RECIST-PR-DIRECTIONAL"))
        for m in NEGOBS_PROG.finditer(s):
            evs.append(Evidence("stable", "definitive", m.group(0), section, s, "RECIST-SD-DIRECTIONAL"))
        for term in STABLE_TERMS:
            for m in re.finditer(term, s):
                if not _stable_context(s, m.start()):
                    continue
                evs.append(Evidence("stable", "definitive", term, section, s, "RECIST-SD-DIRECTIONAL"))
    return evs


def _scan_metastasis(sentences, section):
    trigs = []
    for s in sentences:
        for term in MET_TERMS:
            for m in re.finditer(term, s):
                if not _oncologic_context(s, m.start()) and term not in ("转移", "转移瘤", "转移灶"):
                    continue
                neg = _negated(s, m.start())
                unc = _uncertain(s)
                newctx = bool(MET_NEW_CTX.search(s))
                definitive = (not neg) and (newctx or (section == "impression" and not unc))
                trigs.append({
                    "term": term, "section": section, "sentence": s,
                    "negated": neg, "uncertain": unc, "new_or_progressing": newctx,
                    "definitive": definitive,
                })
    return trigs


def _impression_conclusions(imp_sentences):
    concl = []
    for s in imp_sentences:
        prog = reg = stab = False
        for m in NEW_LESION.finditer(s):
            if (_oncologic_context(s, m.start()) and
                    _new_lesion_is_unequivocal(s, m.start()) and
                    not (_negated(s, m.start()) or NEW_LESION_NEG.search(s[max(0, m.start() - 8):m.start()]))):
                prog = True
        for term in PROG_INHERENT:
            i = s.find(term)
            while i != -1:
                if _oncologic_context(s, i) and not _negated(s, i) and not _soft_change(s, i):
                    prog = True
                i = s.find(term, i + 1)
        for term in PROG_COMPARE_VERBS:
            i = s.find(term)
            while i != -1:
                if _oncologic_context(s, i) and _has_compare(s, i) and not _negated(s, i) and not _soft_change(s, i):
                    prog = True
                i = s.find(term, i + 1)
        for term in REG_INHERENT + REG_COMPARE_VERBS:
            i = s.find(term)
            while i != -1:
                if (_oncologic_context(s, i) and (term in REG_INHERENT or _has_compare(s, i))
                        and not _negated(s, i) and not _soft_change(s, i)):
                    reg = True
                i = s.find(term, i + 1)
        for term in STABLE_TERMS:
            i = s.find(term)
            while i != -1:
                if _stable_context(s, i) or any(t in s for t in ONCOLOGIC_TERMS):
                    stab = True
                i = s.find(term, i + 1)
        for m in NEGOBS_PROG.finditer(s):
            stab = True
        if _uncertain(s) and not (prog or reg or stab):
            continue
        if prog or reg or stab:
            concl.append({"sentence": s, "progression": prog, "regression": reg, "stable": stab,
                          "uncertain": _uncertain(s)})
    return concl


def label_pair(prior_findings, current_findings, current_impression, report_flags=None):
    report_flags = report_flags or {}
    f_sents = split_sentences(current_findings)
    i_sents = split_sentences(current_impression)

    f_evs = _scan_directional(f_sents, "findings")
    i_evs = _scan_directional(i_sents, "impression")
    meas_f = _extract_measurements(f_sents, "findings")
    meas_i = _extract_measurements(i_sents, "impression")
    meas = meas_f + meas_i
    met_trigs = _scan_metastasis(f_sents, "findings") + _scan_metastasis(i_sents, "impression")
    imp_concl = _impression_conclusions(i_sents)

    rules = []
    flags = {
        "explicit_comparison": bool(report_flags.get("explicit_comparison")) or any(
            c in (current_findings or "") + (current_impression or "") for c in COMPARE_MARKERS + ("同前", "相仿")),
        "impression_present": bool((current_impression or "").strip()),
        "impression_conclusion": bool(imp_concl),
        "uncertainty_language": any(e.strength == "suspicious" for e in f_evs + i_evs) or any(t["uncertain"] for t in met_trigs),
        "postoperative_language": _postop_inflam(current_findings or "") or _postop_inflam(current_impression or ""),
        "inflammatory_language": any(p in (current_findings or "") for p in ("炎性", "炎症", "感染")),
        "measurement_present": bool(meas),
        "oncologic_evidence_present": any(_oncologic_context(s) for s in f_sents + i_sents),
        "non_oncologic_change_present": any(
            any(t in s for t in NON_ONCOLOGIC_TERMS) and any(v in s for v in PROG_INHERENT + PROG_COMPARE_VERBS + REG_INHERENT + REG_COMPARE_VERBS)
            for s in f_sents + i_sents
        ),
        "met_suspicious": any(t["uncertain"] and not t["negated"] for t in met_trigs),
        "findings_explicit_change_language": any(e.section == "findings" for e in f_evs),
    }

    # iRECIST-style handling: unequivocal impression sentences govern the
    # primary label; equivocal sentences are retained in provenance but must
    # not become definitive merely because another sentence is stable.
    imp_def = [c for c in imp_concl if not c["uncertain"]]
    imp_unc = [c for c in imp_concl if c["uncertain"]]
    imp_prog = any(c["progression"] for c in imp_def)
    imp_reg = any(c["regression"] for c in imp_def)
    imp_stab = any(c["stable"] for c in imp_def) and not (imp_prog or imp_reg)
    imp_uncertain = bool(imp_concl) and not imp_def

    f_prog_def = [e for e in f_evs if e.category == "progression" and e.strength == "definitive"]
    f_reg_def = [e for e in f_evs if e.category == "regression" and e.strength == "definitive"]
    any_stable = [e for e in f_evs + i_evs if e.category == "stable"]
    f_prog_susp = [e for e in f_evs if e.category == "progression" and e.strength == "suspicious"]
    f_reg_susp = [e for e in f_evs if e.category == "regression" and e.strength == "suspicious"]
    uncertain_meas = [m for m in meas if m["direction"] in ("progression", "regression")
                      and m.get("disease_relevant") and m.get("measurable_by_recist")
                      and m.get("uncertain")]

    met_def = [t for t in met_trigs if t["definitive"]]
    met_flag = bool(met_def)

    eligible_measurement_change = [m for m in meas if m["direction"] in ("progression", "regression")
                                   and m.get("disease_relevant") and m.get("measurable_by_recist")
                                   and not m.get("uncertain")]
    findings_change_conflict = bool(f_prog_def or f_reg_def or f_prog_susp or f_reg_susp
                                     or eligible_measurement_change)

    change = tier = primary_rule = None
    conflict = False

    if imp_def:
        if imp_prog and imp_reg:
            change, tier, primary_rule = "mixed", "definitive", "RECIST-MIXED-IMPRESSION"
        elif imp_prog:
            change, tier, primary_rule = "progression", "definitive", "RECIST-PD-IMPRESSION"
        elif imp_reg:
            change, tier, primary_rule = "regression", "definitive", "RECIST-PR-IMPRESSION"
        else:
            change, tier, primary_rule = "stable", "definitive", "RECIST-SD-IMPRESSION"
        rules.append("QUALITY-IMPRESSION-PRIORITY")
        rules.append("QUALITY-IMPRESSION-SUPPORTED")
        if change == "stable" and (met_flag or findings_change_conflict):
            change, tier, primary_rule = "indeterminate", "indeterminate", "QUALITY-INDETERMINATE-CONFLICT"
            conflict = True
            if met_flag:
                met_flag = True
    elif any(m["direction"] in ("progression", "regression") and m.get("disease_relevant")
             and m.get("measurable_by_recist") and not m.get("uncertain") for m in meas):
        # Paired measurements are a report-level RECIST-informed support
        # signal. They are only eligible when the measured entity is
        # plausibly oncologic and the sentence is unequivocal.
        eligible_meas = eligible_measurement_change
        pd = any(m["direction"] == "progression" for m in eligible_meas)
        pr = any(m["direction"] == "regression" for m in eligible_meas)
        if pd and pr:
            change, tier, primary_rule = "mixed", "quantitative", "RECIST-MIXED-DIRECTIONAL"
        elif pd:
            change, tier, primary_rule = "progression", "quantitative", "RECIST-PD-QUANTITATIVE"
        else:
            change, tier, primary_rule = "regression", "quantitative", "RECIST-PR-QUANTITATIVE"
        rules.append("RECIST-PD-QUANTITATIVE" if pd else "RECIST-PR-QUANTITATIVE")
    elif f_prog_def and f_reg_def:
        change, tier, primary_rule = "mixed", "directional", "RECIST-MIXED-DIRECTIONAL"
    elif f_prog_def:
        change, tier, primary_rule = "progression", "directional", "RECIST-PD-NEW-LESION" \
            if f_prog_def[0].rule == "RECIST-PD-NEW-LESION" else "RECIST-PD-DIRECTIONAL"
    elif f_reg_def:
        change, tier, primary_rule = "regression", "directional", "RECIST-PR-DIRECTIONAL"
    elif imp_concl and imp_uncertain:
        if imp_prog or imp_reg:
            change, tier, primary_rule = ("progression" if imp_prog and not imp_reg else
                                          "regression" if imp_reg and not imp_prog else "mixed"), "suspicious", \
                "QUALITY-UNCERTAINTY-DOWNGRADE"
        elif any(NEW_LESION.search(c["sentence"]) for c in imp_unc):
            # A generic new nodule/lesion with follow-up language is not
            # equivalent to a stable oncologic conclusion; quarantine it.
            change, tier, primary_rule = "indeterminate", "indeterminate", "QUALITY-INDETERMINATE"
        else:
            change, tier, primary_rule = "stable", "suspicious", "QUALITY-UNCERTAINTY-DOWNGRADE"
    elif uncertain_meas or f_prog_susp:
        dirs = {m["direction"] for m in uncertain_meas}
        if f_prog_susp:
            dirs.add("progression")
        if len(dirs) > 1:
            change = "mixed"
        else:
            change = "progression" if "progression" in dirs else "regression"
        change, tier, primary_rule = change, "suspicious", "QUALITY-UNCERTAINTY-DOWNGRADE"
    elif any_stable:
        change, tier, primary_rule = "stable", "directional", "RECIST-SD-DIRECTIONAL"
    else:
        change, tier, primary_rule = "indeterminate", "indeterminate", "QUALITY-INDETERMINATE"

    if met_flag and change == "regression":
        change, primary_rule = "mixed", "RECIST-MIXED-DIRECTIONAL"
        rules.append("QUALITY-CONSISTENCY-MET-PROGRESSION")
        if tier == "definitive":
            tier = "definitive"
    if met_flag and change == "stable" and not conflict:
        change, tier, primary_rule = "indeterminate", "indeterminate", "QUALITY-INDETERMINATE-CONFLICT"
        conflict = True
        rules.append("QUALITY-CONSISTENCY-MET-PROGRESSION")

    rules.append(primary_rule)
    if flags["explicit_comparison"]:
        rules.append("QUALITY-EXPLICIT-COMPARISON")
    if flags["postoperative_language"]:
        rules.append("QUALITY-POSTOP-INFLAMMATORY-FLAG")
    if flags["oncologic_evidence_present"]:
        rules.append("QUALITY-ONCOLOGIC-SCOPE")
    if flags["non_oncologic_change_present"]:
        rules.append("QUALITY-NONONCOLOGIC-DOWNGRADE")
    if tier == "suspicious":
        rules.append("QUALITY-UNCERTAINTY-DOWNGRADE")
    if any(m["direction"] == "below_threshold_change" for m in meas):
        rules.append("MEASUREMENT-BELOW-RECIST-INFORMED-THRESHOLD")
    if any(m["direction"] in ("progression", "regression") for m in meas):
        rules.append("RECIST-PD-QUANTITATIVE-SUPPORT")

    primary_eligible = (
        tier in ("definitive", "quantitative")
        and change in ("progression", "regression", "stable", "mixed")
        and flags["explicit_comparison"]
        and not conflict
    )
    confidence = "high" if tier == "definitive" else "standard" if tier in ("quantitative", "directional") else "low"

    triggers = [{"category": e.category, "section": e.section, "sentence": e.sentence, "term": e.term,
                 "strength": e.strength} for e in f_evs + i_evs]
    met_prov = [{k: t[k] for k in ("term", "section", "sentence", "negated", "uncertain",
                                   "new_or_progressing", "definitive")} for t in met_trigs]

    return LabelResult(
        change=change,
        new_metastatic_disease=met_flag,
        evidence_tier=tier,
        confidence=confidence,
        primary_eligible=primary_eligible,
        primary_rule=primary_rule,
        protocol_rule_ids=list(dict.fromkeys(rules)),
        triggers=triggers,
        metastasis_triggers=met_prov,
        measurement_evidence=meas,
        flags=flags,
        impression_conclusion=imp_concl,
    )
