#!/bin/bash
set -e

SERVER_URL="${SERVER_URL:-http://127.0.0.1:11878}"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-60}"

echo "🔍 验证模型服务: ${SERVER_URL}"

python3 - "$SERVER_URL" "$TIMEOUT_SECONDS" <<'PY'
import json
import sys
import time
import urllib.error
import urllib.request

server_url = sys.argv[1].rstrip("/")
timeout_seconds = int(sys.argv[2])


def request(method, path, data=None):
    body = None if data is None else json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        f"{server_url}{path}",
        data=body,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def infer(model_id, prompt):
    payload = {
        "model": model_id,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": 128,
        "temperature": 0.3,
        "top_p": 0.6,
    }
    result = request("POST", "/v1/chat/completions", payload)
    return result["choices"][0]["message"]["content"].strip()


def validate_output(source, output, forbidden_terms):
    if not output:
        return "输出为空"
    if output.strip().lower() == source.strip().lower():
        return "输出等于原文"
    if any(term.lower() in output.lower() for term in forbidden_terms):
        return "输出疑似包含解释废话"
    return ""


deadline = time.time() + timeout_seconds
last_error = None
while time.time() < deadline:
    try:
        models = request("GET", "/v1/models")
        model_id = models["data"][0]["id"]
        break
    except (KeyError, IndexError, urllib.error.URLError, TimeoutError) as exc:
        last_error = exc
        time.sleep(2)
else:
    print(f"❌ 服务未就绪: {last_error}")
    sys.exit(1)

print(f"   模型: {model_id}")

cases = [
    {
        "name": "英文到中文",
        "source": "It is free, from Tencent's Hy-MT model.",
        "prompt": "Translate the following segment into Chinese, without additional explanation.\n\nIt is free, from Tencent's Hy-MT model.",
        "forbidden_terms": ["translation", "explanation", "without additional explanation"],
    },
    {
        "name": "中文到英文",
        "source": "这个接口今天已经可以稳定使用。",
        "prompt": "将以下文本翻译为英语，注意只需要输出翻译后的结果，不要额外解释：\n\n这个接口今天已经可以稳定使用。",
        "forbidden_terms": ["翻译", "解释", "以下"],
    },
    {
        "name": "日文到中文",
        "source": "明日は雨が降るかもしれません。",
        "prompt": "将以下文本翻译为中文，注意只需要输出翻译后的结果，不要额外解释：\n\n明日は雨が降るかもしれません。",
        "forbidden_terms": ["翻译", "解释", "以下"],
    },
    {
        "name": "韩文到中文",
        "source": "오늘 회의는 오후 세 시에 시작합니다.",
        "prompt": "将以下文本翻译为中文，注意只需要输出翻译后的结果，不要额外解释：\n\n오늘 회의는 오후 세 시에 시작합니다.",
        "forbidden_terms": ["翻译", "解释", "以下"],
    },
    {
        "name": "法文到中文",
        "source": "Le service est disponible toute la journée.",
        "prompt": "将以下文本翻译为中文，注意只需要输出翻译后的结果，不要额外解释：\n\nLe service est disponible toute la journée.",
        "forbidden_terms": ["翻译", "解释", "以下"],
    },
    {
        "name": "德文到中文",
        "source": "Die neue Version wurde heute veröffentlicht.",
        "prompt": "将以下文本翻译为中文，注意只需要输出翻译后的结果，不要额外解释：\n\nDie neue Version wurde heute veröffentlicht.",
        "forbidden_terms": ["翻译", "解释", "以下"],
    },
    {
        "name": "西班牙文到中文",
        "source": "El sistema responde más rápido que antes.",
        "prompt": "将以下文本翻译为中文，注意只需要输出翻译后的结果，不要额外解释：\n\nEl sistema responde más rápido que antes.",
        "forbidden_terms": ["翻译", "解释", "以下"],
    },
    {
        "name": "俄文到中文",
        "source": "Модель успешно обработала запрос.",
        "prompt": "将以下文本翻译为中文，注意只需要输出翻译后的结果，不要额外解释：\n\nМодель успешно обработала запрос.",
        "forbidden_terms": ["翻译", "解释", "以下"],
    },
    {
        "name": "阿拉伯文到中文",
        "source": "الخدمة تعمل بشكل مستقر الآن.",
        "prompt": "将以下文本翻译为中文，注意只需要输出翻译后的结果，不要额外解释：\n\nالخدمة تعمل بشكل مستقر الآن.",
        "forbidden_terms": ["翻译", "解释", "以下"],
    },
    {
        "name": "葡萄牙文到中文",
        "source": "A resposta chegou em poucos segundos.",
        "prompt": "将以下文本翻译为中文，注意只需要输出翻译后的结果，不要额外解释：\n\nA resposta chegou em poucos segundos.",
        "forbidden_terms": ["翻译", "解释", "以下"],
    },
]

failed = []
for index, case in enumerate(cases, start=1):
    print(f"\n[{index}/{len(cases)}] {case['name']}")
    started_at = time.time()
    try:
        output = infer(model_id, case["prompt"])
        elapsed = time.time() - started_at
        error = validate_output(case["source"], output, case["forbidden_terms"])
    except (KeyError, IndexError, urllib.error.URLError, TimeoutError) as exc:
        output = ""
        elapsed = time.time() - started_at
        error = f"请求失败: {exc}"

    print(f"   原文: {case['source']}")
    print(f"   输出: {output or '<空>'}")
    print(f"   耗时: {elapsed:.2f}s")

    if error:
        print(f"   结果: ❌ {error}")
        failed.append(case["name"])
    else:
        print("   结果: ✅ 通过")

if failed:
    print(f"\n❌ 验证失败: {len(failed)}/{len(cases)}")
    print(f"   失败项: {', '.join(failed)}")
    sys.exit(1)

print(f"\n✅ 验证通过: {len(cases)}/{len(cases)}")
PY
