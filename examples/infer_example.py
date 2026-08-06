"""
ThoracicOncoBench — 推理脚本 v2 (多端点 + key轮换)
"""

import json, time, argparse, os, sys, re
import urllib.request, urllib.error
import concurrent.futures

BENCH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "..", "data", "benchmark.jsonl"
)

SYS = "你是胸部肿瘤放射科专家。严格按要求输出，只输出JSON，不要解释，不要用<think>标签。"


def build_prompt(inst):
    task = inst["task"]
    if task == "change_assessment":
        p = inst["input"]["prior"]
        c = inst["input"]["current"]
        return f"""判断同一患者两次胸部CT影像所见中病灶的变化。
[前片 {p.get("study_date", "")} 影像所见]
{p.get("findings_text", "")}

[本次 {c.get("study_date", "")} 影像所见]
{c.get("findings_text", "")}

请输出JSON：
{{"overall_change": "progression|regression|stable|mixed|indeterminate", "new_metastasis_signal": true|false}}
progression=较前进展/增大/新发；regression=较前缩小/减少；stable=同前/稳定；mixed=既有进展又有退缩；indeterminate=无法判断。"""
    else:
        f = inst["input"].get("findings_text", "")
        ctx = inst["input"].get("clinical_context", "")
        return f"""胸部CT影像所见如下（临床情境：{ctx}）。
{f}

请输出JSON：
{{"impression": "诊断意见文本", "cTNM": {{"cT": "数字", "cN": "数字", "cM": "数字"}}}}
若信息不足填null。"""


NVIDIA_KEYS = [
    "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",
    "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",
    "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",
    "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",
    "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",
    "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",
    "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",
    "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",
    "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",
    "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",
    "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",
    "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",
    "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",
    "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",
    "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",
    "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",
    "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",
    "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",
    "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",
    "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",
    "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",
    "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",
    "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",
]

CUSTOM_API_ENDPOINTS = {"antangelmed", "medseek", "huatuogpt", "medix-r1", "mediphi", "qwq-med-3-med"}

ENDPOINTS = {
    "gptnb": {"url": "https://api.gptnb.ai/v1/chat/completions", "keys": None},
    "nvidia": {
        "url": "https://integrate.api.nvidia.com/v1/chat/completions",
        "keys": NVIDIA_KEYS,
    },
    "baichuan": {
        "url": "https://api.baichuan-ai.com/v1/chat/completions",
        "keys": ["sk-faa09c93a4decf8de250bb5baf545e94"],
    },
    "local": {"url": "http://localhost:1234/v1/chat/completions", "keys": [None]},
    "antangelmed": {
        "url": "http://localhost:1234/api/v1/chat",
        "keys": [None],
    },
    "medseek": {
        "url": "http://localhost:1234/api/v1/chat",
        "keys": [None],
    },
    "huatuogpt": {
        "url": "http://localhost:1234/api/v1/chat",
        "keys": [None],
    },
    "medix-r1": {
        "url": "http://localhost:1234/api/v1/chat",
        "keys": [None],
    },
    "mediphi": {
        "url": "http://localhost:1234/api/v1/chat",
        "keys": [None],
    },
    "qwq-med-3-med": {
        "url": "http://localhost:1234/api/v1/chat",
        "keys": [None],
    },

}

_key_idx = [0]


def get_next_key(ep):
    cfg = ENDPOINTS[ep]
    if cfg["keys"] is None:
        return os.environ.get("GPTNB_API_KEY")
    k = cfg["keys"][_key_idx[0] % len(cfg["keys"])]
    _key_idx[0] += 1
    return k


def call_api(ep, model, prompt, max_tokens=8000):
    cfg = ENDPOINTS[ep]
    is_custom = ep in CUSTOM_API_ENDPOINTS
    max_retry = 8 if ep == "medix-r1" else 4
    for attempt in range(max_retry):
        key = get_next_key(ep)
        headers = {
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
        }
        if key:
            headers["Authorization"] = f"Bearer {key}"
        if is_custom:
            body = {
                "model": model,
                "system_prompt": SYS,
                "input": prompt,
            }
        else:
            body = {
                "model": model,
                "messages": [
                    {"role": "system", "content": SYS},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.6,
                "max_tokens": max_tokens,
                "top_p": 0.95,
            }
        try:
            data = json.dumps(body).encode("utf-8")
            req = urllib.request.Request(
                cfg["url"], data=data, headers=headers, method="POST"
            )
            with urllib.request.urlopen(req, timeout=300) as resp:
                out = json.loads(resp.read().decode("utf-8"))
            if is_custom:
                raw = ""
                for item in out.get("output", []):
                    if isinstance(item, dict) and item.get("type") == "message":
                        raw = item.get("content", "")
                        break
                if not raw:
                    raw = str(out)
            else:
                msg = out["choices"][0]["message"]
                raw = msg.get("content", "") or msg.get("reasoning_content", "")
            return raw
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 503):
                max_retry = 8 if ep == "medix-r1" else 4
                wait = 15 * (attempt + 1)
                print(f"  HTTP {e.code}, 等待{wait}s后重试({attempt+1}/{max_retry})", file=sys.stderr)
                time.sleep(wait)
            else:
                print(f"  HTTP {e.code}, 不重试", file=sys.stderr)
                return None
        except Exception as e:
            print(f"  异常: {e}, 重试({attempt+1}/4)", file=sys.stderr)
            if attempt < max_retry - 1:
                time.sleep(10 * (attempt + 1))
            else:
                return None
    return None


def extract_json(text):
    if not text:
        return None
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.S).strip()
    try:
        return json.loads(text)
    except:
        pass
    m = re.search(r"\{.*\}", text, re.S)
    if m:
        try:
            return json.loads(m.group(0))
        except:
            pass
    return None


def normalize_output(task, parsed):
    out = {}
    if not parsed:
        return out
    if task == "change_assessment":
        out["overall_change"] = str(
            parsed.get("overall_change", "indeterminate")
        ).lower()
        out["new_metastasis_signal"] = bool(parsed.get("new_metastasis_signal", False))
    else:
        out["impression"] = parsed.get("impression")
        ctnm = parsed.get("cTNM") or parsed.get("tnm") or {}
        out["cTNM"] = {
            "cT": ctnm.get("cT") or ctnm.get("T"),
            "cN": ctnm.get("cN") or ctnm.get("N"),
            "cM": ctnm.get("cM") or ctnm.get("M"),
        }
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--endpoint", required=True, choices=["gptnb", "nvidia", "baichuan", "local", "antangelmed", "medseek", "huatuogpt", "medix-r1", "mediphi", "qwq-med-3-med"]
    )
    ap.add_argument("--model", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--max-tokens", type=int, default=14000)
    ap.add_argument("--workers", type=int, default=4, help="并行调用数")
    args = ap.parse_args()

    if args.endpoint == "gptnb" and not os.environ.get("GPTNB_API_KEY"):
        print("ERROR: gptnb 需设置 GPTNB_API_KEY", file=sys.stderr)
        sys.exit(1)

    bench = [json.loads(l) for l in open(BENCH, encoding="utf-8")]
    if args.start:
        bench = bench[args.start :]
    if args.limit:
        bench = bench[: args.limit]
    print(f"推理: {args.endpoint}/{args.model} on {len(bench)} 例, 并行{args.workers}路 -> {args.out}")
    t0 = time.time()

    def process_one(inst):
        prompt = build_prompt(inst)
        content = call_api(args.endpoint, args.model, prompt, args.max_tokens)
        parsed = extract_json(content)
        out = normalize_output(inst["task"], parsed)
        return {
            "id": inst["id"],
            "output": out,
            "_raw": (content or "")[:200],
        }

    n_ok, n_fail = 0, 0
    with open(args.out, "w", encoding="utf-8") as f:
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {executor.submit(process_one, inst): inst for inst in bench}
            for i, future in enumerate(concurrent.futures.as_completed(futures)):
                result = future.result()
                if result["output"]:
                    n_ok += 1
                else:
                    n_fail += 1
                f.write(json.dumps(result, ensure_ascii=False) + "\n")
                f.flush()
                if i % 20 == 0 or i < 3:
                    ok = "ok" if result["output"] else "FAIL"
                    print(
                        f"  [{i + 1}/{len(bench)}] {result['id']} {ok} ok={n_ok} fail={n_fail} ({time.time() - t0:.0f}s)"
                    )
    print(
        f"完成: {len(bench)} 例, ok={n_ok} fail={n_fail}, 用时 {time.time() - t0:.0f}s"
    )


if __name__ == "__main__":
    main()
