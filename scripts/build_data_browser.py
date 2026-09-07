"""Build the standalone English-default bilingual benchmark browser."""

from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path


LONG_ZH = "给出同一患者连续两次胸部CT报告的所见部分。请判断当前报告相对于既往报告的肿瘤负荷相关纵向变化：进展、退缩、稳定、混合或不确定，并判断是否记录了新发转移性疾病。"
LONG_EN = "You are given the findings sections of two consecutive chest CT reports from the same patient. Classify the overall tumor-burden-related longitudinal change documented in the current findings relative to the prior findings as progression, regression, stable, mixed, or indeterminate, and state whether new metastatic disease is documented."
IMP_ZH = "请根据胸部CT所见生成影像学诊断印象。"
IMP_EN = "Generate the radiology impression from the chest CT findings."
CJK_RE = re.compile(r"[\u3400-\u4dbf\u4e00-\u9fff\uf900-\ufaff]")


def jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def translate_nested(value, evidence_en: dict[str, str], missing: set[str]):
    if isinstance(value, dict):
        return {key: translate_nested(item, evidence_en, missing) for key, item in value.items()}
    if isinstance(value, list):
        return [translate_nested(item, evidence_en, missing) for item in value]
    if isinstance(value, str) and CJK_RE.search(value):
        translated = evidence_en.get(value)
        if translated is None:
            missing.add(value)
            return value
        return translated
    return value


def payload(data_dir: Path, allow_missing: bool = False) -> dict:
    reports = jsonl(data_dir / "reports_deidentified.jsonl")
    longitudinal = jsonl(data_dir / "longitudinal_change_instances.jsonl")
    impressions = jsonl(data_dir / "impression_generation_instances.jsonl")
    report_en = {row["report_id"]: row for row in jsonl(data_dir / "reports_english.jsonl")}
    evidence_en = {row["source_text"]: row["text_en"] for row in jsonl(data_dir / "evidence_english.jsonl")}
    missing_reports = {row["report_id"] for row in reports if row["report_id"] not in report_en}
    missing_evidence: set[str] = set()

    by_patient = defaultdict(lambda: {"reports": [], "longitudinal": [], "impressions": []})
    for report_row in reports:
        translated = report_en.get(report_row["report_id"], {})
        by_patient[report_row["patient_id"]]["reports"].append({
            "report_id": report_row["report_id"],
            "report_index": report_row.get("report_index"),
            "days_from_first": report_row.get("days_from_first"),
            "exam_type": report_row.get("exam_type", ""),
            "findings_zh": report_row.get("findings", ""),
            "impression_zh": report_row.get("impression", ""),
            "findings_en": translated.get("findings_en", ""),
            "impression_en": translated.get("impression_en", ""),
        })

    for instance in longitudinal:
        provenance_zh = instance.get("provenance", {})
        provenance_en = translate_nested(provenance_zh, evidence_en, missing_evidence)
        by_patient[instance["patient_id"]]["longitudinal"].append({
            "instance_id": instance["instance_id"],
            "task": instance["task"],
            "split": instance.get("split", ""),
            "prior_report_id": instance["prior_report_id"],
            "current_report_id": instance["current_report_id"],
            "interval_days": instance.get("interval_days"),
            "question_zh": LONG_ZH,
            "question_en": instance.get("input", {}).get("question", LONG_EN),
            "label": instance.get("label", {}),
            "provenance_zh": provenance_zh,
            "provenance_en": provenance_en,
        })

    for instance in impressions:
        translated = report_en.get(instance["report_id"], {})
        by_patient[instance["patient_id"]]["impressions"].append({
            "instance_id": instance["instance_id"],
            "task": instance["task"],
            "split": instance.get("split", ""),
            "report_id": instance["report_id"],
            "question_zh": IMP_ZH,
            "question_en": instance.get("input", {}).get("question", IMP_EN),
            "answer_zh": instance.get("label", {}).get("reference_impression", ""),
            "answer_en": translated.get("impression_en", ""),
        })

    if not allow_missing and (missing_reports or missing_evidence):
        raise SystemExit(
            "English translation cache is incomplete: "
            f"{len(missing_reports)} reports and {len(missing_evidence)} evidence strings are missing."
        )

    patients = []
    for patient_id in sorted(by_patient):
        patient = by_patient[patient_id]
        patient["patient_id"] = patient_id
        patient["reports"].sort(key=lambda row: (row.get("report_index") is None, row.get("report_index") or 0))
        patient["longitudinal"].sort(key=lambda row: row["instance_id"])
        patient["impressions"].sort(key=lambda row: row["instance_id"])
        patients.append(patient)

    return {
        "meta": {
            "version": "v0.4.0",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "patient_count": len(patients),
            "report_count": len(reports),
            "longitudinal_count": len(longitudinal),
            "impression_count": len(impressions),
            "translated_report_count": len(report_en),
            "translated_evidence_count": len(evidence_en),
        },
        "patients": patients,
    }


HTML = r'''<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>ThoracicOncoBench v0.4.0 Data Browser</title><style>
:root{font-family:Inter,system-ui,-apple-system,"Segoe UI",sans-serif;color:#1d2a35;background:#f4f7f8;line-height:1.5}*{box-sizing:border-box}body{margin:0}.shell{max-width:1500px;margin:auto;padding:28px 24px 48px}header{background:#123b4a;color:white;padding:26px 28px;border-radius:8px}h1{margin:0 0 5px;font-size:28px;letter-spacing:0}header p{margin:0;color:#d9e8ec}.toolbar{display:flex;flex-wrap:wrap;gap:9px;align-items:center;margin:18px 0;padding:13px;background:#fff;border:1px solid #dbe4e7;border-radius:8px;position:sticky;top:0;z-index:3;box-shadow:0 3px 12px #22313b12}input,select,button{font:inherit}input,select{height:38px;border:1px solid #c8d5d9;border-radius:6px;padding:0 10px;background:#fff;color:#1d2a35}input{min-width:280px;flex:1}button{height:38px;border:1px solid #9fb5bd;border-radius:6px;background:#fff;color:#174a5c;padding:0 12px;cursor:pointer}button.active,button:hover{background:#174a5c;color:#fff}.stats{display:flex;flex-wrap:wrap;gap:8px;margin-bottom:15px}.stat{background:#eaf2f4;border:1px solid #cbdde1;border-radius:6px;padding:6px 10px;font-size:13px}.stat b{font-size:15px;color:#123b4a}.patient,.case{background:#fff;border:1px solid #dbe4e7;border-radius:8px;margin:9px 0;overflow:hidden}.patient>summary,.case>summary{cursor:pointer;list-style:none;padding:12px 15px}.patient>summary::-webkit-details-marker,.case>summary::-webkit-details-marker{display:none}.patient>summary{font-weight:700;display:flex;gap:10px}.patient>summary:before{content:"+";width:22px;height:22px;display:grid;place-items:center;border:1px solid #b6cbd1;border-radius:4px}.patient[open]>summary:before{content:"-"}.patient-count{margin-left:auto;color:#60757d;font-size:12px;font-weight:500}.patient-body,.case-body{border-top:1px solid #e5edef;padding:0 15px 15px}.case{border-radius:7px;background:#fbfcfc}.case>summary{display:flex;gap:8px;align-items:center;flex-wrap:wrap}.case>summary:before{content:">";font-size:16px;color:#61808b}.case[open]>summary:before{transform:rotate(90deg)}.section-title{font-size:15px;color:#174a5c;margin:17px 0 8px;font-weight:700}.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(290px,1fr));gap:11px}.panel{background:#fff;border:1px solid #e2eaec;border-radius:6px;padding:10px}.panel h4{margin:0 0 7px;font-size:13px;color:#174a5c}.text{white-space:pre-wrap;word-break:break-word;font-size:13px;max-height:360px;overflow:auto;background:#f7fafb;border-radius:4px;padding:9px}.question{background:#fffdf3;border:1px solid #eadca9;border-radius:5px;padding:10px;white-space:pre-wrap;font-size:13px}.answer{border-left:4px solid #174a5c;background:#eef6f7;padding:10px;border-radius:5px}.answer strong{font-size:18px}.kv{display:grid;grid-template-columns:minmax(150px,230px) 1fr;gap:6px 12px;font-size:13px}.kv dt{color:#60757d}.kv dd{margin:0;word-break:break-word}.evidence-list{margin:6px 0 12px;padding-left:20px}.evidence-list li{margin:5px 0}.badge{display:inline-block;border-radius:5px;padding:2px 8px;font-size:12px;font-weight:700}.progression{background:#fde9e7;color:#9b2c24}.regression{background:#e6f5ed;color:#26734a}.stable{background:#e8f0f4;color:#295668}.mixed{background:#fff2d9;color:#8a5b11}.indeterminate{background:#eeeaf8;color:#5e4a8c}.muted,.hint{color:#6c7e84;font-size:12px}.empty{padding:30px;text-align:center;color:#6c7e84;background:#fff;border:1px dashed #cbd9dd;border-radius:8px}@media(max-width:700px){.shell{padding:16px 10px 30px}header{padding:20px}.toolbar{position:static}.toolbar input{min-width:100%}.patient-count{width:100%;margin-left:34px}.kv{grid-template-columns:1fr}}
</style></head><body><div class="shell"><header><h1>ThoracicOncoBench v0.4.0</h1><p id="subtitle">De-identified browser for reports, original questions, reference answers, and auditable evidence</p></header><div class="toolbar"><input id="search" type="search" placeholder="Search patients, reports, cases, or clinical text..."><select id="task"><option value="all">All tasks</option><option value="longitudinal">Longitudinal change</option><option value="impression">Impression generation</option></select><select id="label"><option value="all">All reference answers</option><option value="progression">Progression</option><option value="regression">Regression</option><option value="stable">Stable</option><option value="mixed">Mixed</option><option value="indeterminate">Indeterminate</option></select><button id="en" class="active">English</button><button id="zh">Chinese</button><button id="expand">Expand all</button><button id="collapse">Collapse all</button><button id="more">Load more</button><span id="shown" class="hint"></span></div><div id="stats" class="stats"></div><main id="app"></main></div><script>
const DATA=__DATA__;
const T={en:{subtitle:"De-identified browser for reports, original questions, reference answers, and auditable evidence",search:"Search patients, reports, cases, or clinical text...",tasks:["All tasks","Longitudinal change","Impression generation"],labels:["All reference answers","Progression","Regression","Stable","Mixed","Indeterminate"],expand:"Expand all",collapse:"Collapse all",more:"Load more",reports:"Reports",report:"Report",longitudinal:"Longitudinal tasks",impressions:"Impression-generation tasks",original:"Original question",prior:"Prior report findings",current:"Current report findings",input:"Input findings",answer:"Reference answer",metastasis:"New metastatic disease",provenance:"Auditable provenance",viewImpression:"View report impression",none:"No matching records",patient:"patients",reportStat:"reports",longStat:"longitudinal tasks",impStat:"impression tasks",showing:"Showing",of:"of",evidenceTier:"Evidence tier",primaryRule:"Primary rule",primaryEligible:"Primary eligible",ruleInterpretation:"Rule interpretation",protocolRules:"Protocol rule IDs",flags:"Evidence flags",triggers:"Evidence triggers",metTriggers:"Metastasis triggers",measurements:"Measurement evidence",conclusions:"Impression conclusions",impressionBadge:"Impression"},zh:{subtitle:"去标识化数据浏览器：按患者查看报告、原题、参考答案与可审计证据",search:"搜索患者、报告、病例或临床文本...",tasks:["全部任务","纵向变化","印象生成"],labels:["全部参考答案","进展","退缩/缓解","稳定","混合变化","不确定"],expand:"展开全部",collapse:"收起全部",more:"加载更多",reports:"报告",report:"报告",longitudinal:"纵向变化任务",impressions:"印象生成任务",original:"原题",prior:"既往报告所见",current:"当前报告所见",input:"输入所见",answer:"参考答案",metastasis:"新发转移性疾病",provenance:"可审计依据",viewImpression:"查看原始诊断印象",none:"没有匹配结果",patient:"位患者",reportStat:"报告",longStat:"纵向任务",impStat:"印象任务",showing:"显示",of:"/",evidenceTier:"证据层级",primaryRule:"主规则",primaryEligible:"是否主集",ruleInterpretation:"规则解释",protocolRules:"协议规则 ID",flags:"证据标志",triggers:"证据触发项",metTriggers:"转移触发项",measurements:"测量证据",conclusions:"诊断结论",impressionBadge:"印象生成"}};
const NAMES={en:{progression:"Progression",regression:"Regression",stable:"Stable",mixed:"Mixed",indeterminate:"Indeterminate"},zh:{progression:"进展",regression:"退缩/缓解",stable:"稳定",mixed:"混合变化",indeterminate:"不确定"}};
let lang="en",limit=100;const R=new Map;DATA.patients.forEach(p=>p.reports.forEach(r=>R.set(r.report_id,r)));
const esc=s=>String(s??"").replace(/[&<>"']/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;","\"":"&quot;","'":"&#39;"}[c]));
const human=s=>String(s).replaceAll("_"," ").replace(/\b\w/g,c=>c.toUpperCase());
const lname=x=>NAMES[lang][x]||x||"-",qtext=x=>lang==="en"?x.question_en:x.question_zh;
function report(r,title){if(!r)return"";const findings=lang==="en"?r.findings_en:r.findings_zh,impression=lang==="en"?r.impression_en:r.impression_zh;return`<section class="panel"><h4>${esc(title)} <span class="muted">${esc(r.report_id)} | index ${esc(r.report_index)} | day ${esc(r.days_from_first)}</span></h4><div class="text">${esc(findings)}</div>${impression?`<details><summary class="muted">${T[lang].viewImpression}</summary><div class="text">${esc(impression)}</div></details>`:""}</section>`}
function scalar(v){if(v===null||v===undefined)return"-";if(typeof v==="boolean")return v?"true":"false";return esc(v)}
function objectRows(obj){return Object.entries(obj||{}).map(([k,v])=>`<dt>${esc(human(k))}</dt><dd>${typeof v==="object"?esc(JSON.stringify(v,null,2)):scalar(v)}</dd>`).join("")}
function evidenceList(title,items){if(!items?.length)return"";return`<h4>${esc(title)}</h4><ol class="evidence-list">${items.map(item=>`<li><dl class="kv">${typeof item==="object"?objectRows(item):`<dt>${esc(title)}</dt><dd>${scalar(item)}</dd>`}</dl></li>`).join("")}</ol>`}
function prov(x){const l=x.label||{},p=lang==="en"?x.provenance_en:x.provenance_zh;return`<dl class="kv"><dt>${T[lang].evidenceTier}</dt><dd>${scalar(l.evidence_tier)}</dd><dt>${T[lang].primaryRule}</dt><dd>${scalar(l.primary_rule)}</dd><dt>${T[lang].ruleInterpretation}</dt><dd>${scalar(p.primary_rule_description)}</dd><dt>${T[lang].primaryEligible}</dt><dd>${scalar(l.primary_eligible)}</dd><dt>${T[lang].metastasis}</dt><dd>${scalar(l.new_metastatic_disease)}</dd><dt>${T[lang].protocolRules}</dt><dd>${esc((l.protocol_rule_ids||[]).join(", "))}</dd></dl>${evidenceList(T[lang].flags,[p.flags])}${evidenceList(T[lang].triggers,p.triggers)}${evidenceList(T[lang].metTriggers,p.metastasis_triggers)}${evidenceList(T[lang].measurements,p.measurement_evidence)}${evidenceList(T[lang].conclusions,p.impression_conclusion)}`}
function lcard(x){const a=R.get(x.prior_report_id),b=R.get(x.current_report_id),l=x.label||{};return`<details class="case" data-kind="longitudinal" data-label="${esc(l.change)}"><summary><span class="badge ${esc(l.change)}">${esc(lname(l.change))}</span><span>${esc(x.instance_id)}</span><span class="muted">${esc(x.interval_days)} days | ${esc(x.split)}</span></summary><div class="case-body"><h4>${T[lang].original}</h4><div class="question">${esc(qtext(x))}</div><div class="grid">${report(a,T[lang].prior)}${report(b,T[lang].current)}</div><h4>${T[lang].answer}</h4><div class="answer"><strong>${esc(lname(l.change))}</strong><div>${T[lang].metastasis}: <b>${l.new_metastatic_disease?"true":"false"}</b></div></div><h4>${T[lang].provenance}</h4><div class="panel">${prov(x)}</div></div></details>`}
function icard(x){const r=R.get(x.report_id),answer=lang==="en"?x.answer_en:x.answer_zh;return`<details class="case" data-kind="impression"><summary><span class="badge stable">${T[lang].impressionBadge}</span><span>${esc(x.instance_id)}</span><span class="muted">${esc(x.split)}</span></summary><div class="case-body"><h4>${T[lang].original}</h4><div class="question">${esc(qtext(x))}</div><div class="grid">${report(r,T[lang].input)}</div><h4>${T[lang].answer}</h4><div class="answer"><div class="text">${esc(answer)}</div></div></div></details>`}
function render(){const q=document.getElementById("search").value.trim().toLowerCase(),task=document.getElementById("task").value,label=document.getElementById("label").value;let n=0,seen=0,out=[];for(const p of DATA.patients){let ls=task!=="impression"?p.longitudinal.filter(x=>label==="all"||(x.label||{}).change===label):[],is=task!=="longitudinal"&&label==="all"?p.impressions:[];if(q&&!p.patient_id.toLowerCase().includes(q)){ls=ls.filter(x=>JSON.stringify(x).toLowerCase().includes(q)||JSON.stringify(R.get(x.prior_report_id)||{}).toLowerCase().includes(q)||JSON.stringify(R.get(x.current_report_id)||{}).toLowerCase().includes(q));is=is.filter(x=>JSON.stringify(x).toLowerCase().includes(q)||JSON.stringify(R.get(x.report_id)||{}).toLowerCase().includes(q))}if(!ls.length&&!is.length&&task!=="all")continue;if(q&&!p.patient_id.toLowerCase().includes(q)&&!ls.length&&!is.length&&!JSON.stringify(p.reports).toLowerCase().includes(q))continue;n++;if(seen++>=limit)continue;out.push(`<details class="patient"><summary><span>${esc(p.patient_id)}</span><span class="patient-count">${p.reports.length} ${T[lang].reportStat} | ${ls.length} ${T[lang].longStat} | ${is.length} ${T[lang].impStat}</span></summary><div class="patient-body"><div class="section-title">${T[lang].reports}</div><div class="grid">${p.reports.map(r=>report(r,`${T[lang].report} ${r.report_index}`)).join("")}</div>${ls.length?`<div class="section-title">${T[lang].longitudinal}</div>${ls.map(lcard).join("")}`:""}${is.length?`<div class="section-title">${T[lang].impressions}</div>${is.map(icard).join("")}`:""}</div></details>`)}document.getElementById("app").innerHTML=out.join("")||`<div class="empty">${T[lang].none}</div>`;document.getElementById("shown").textContent=lang==="en"?`${T.en.showing} ${Math.min(n,limit)} ${T.en.of} ${n} ${T.en.patient}`:`${T.zh.showing} ${Math.min(n,limit)}${T.zh.of}${n} ${T.zh.patient}`;document.getElementById("more").style.display=n>limit?"inline-block":"none";document.getElementById("stats").innerHTML=`<div class="stat"><b>${DATA.meta.patient_count}</b> ${T[lang].patient}</div><div class="stat"><b>${DATA.meta.report_count}</b> ${T[lang].reportStat}</div><div class="stat"><b>${DATA.meta.longitudinal_count}</b> ${T[lang].longStat}</div><div class="stat"><b>${DATA.meta.impression_count}</b> ${T[lang].impStat}</div>`}
function setlang(x){lang=x;document.documentElement.lang=x==="en"?"en":"zh-CN";document.getElementById("en").classList.toggle("active",x==="en");document.getElementById("zh").classList.toggle("active",x==="zh");document.getElementById("subtitle").textContent=T[x].subtitle;document.getElementById("search").placeholder=T[x].search;[...document.getElementById("task").options].forEach((o,i)=>o.textContent=T[x].tasks[i]);[...document.getElementById("label").options].forEach((o,i)=>o.textContent=T[x].labels[i]);document.getElementById("expand").textContent=T[x].expand;document.getElementById("collapse").textContent=T[x].collapse;document.getElementById("more").textContent=T[x].more;render()}
document.getElementById("search").addEventListener("input",()=>{limit=100;render()});document.getElementById("task").addEventListener("change",()=>{limit=100;render()});document.getElementById("label").addEventListener("change",()=>{limit=100;render()});document.getElementById("zh").addEventListener("click",()=>setlang("zh"));document.getElementById("en").addEventListener("click",()=>setlang("en"));document.getElementById("more").addEventListener("click",()=>{limit+=100;render()});document.getElementById("expand").addEventListener("click",()=>document.querySelectorAll("details").forEach(x=>x.open=true));document.getElementById("collapse").addEventListener("click",()=>document.querySelectorAll("details").forEach(x=>x.open=false));render();
</script></body></html>'''


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", type=Path, default=Path("data"))
    parser.add_argument("--output", type=Path, default=Path("benchmark_data_browser.html"))
    parser.add_argument("--allow-missing-translations", action="store_true")
    args = parser.parse_args()
    obj = payload(args.data_dir, allow_missing=args.allow_missing_translations)
    data = json.dumps(obj, ensure_ascii=False, separators=(",", ":")).replace("</script", "<\\/script")
    args.output.write_text(HTML.replace("__DATA__", data), encoding="utf-8")
    print(json.dumps({"output": str(args.output), "patients": obj["meta"]["patient_count"], "bytes": args.output.stat().st_size}, ensure_ascii=False))


if __name__ == "__main__":
    main()
