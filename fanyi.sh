#!/bin/bash

# Required parameters:
# @raycast.schemaVersion 1
# @raycast.title fany
# @raycast.mode fullOutput
# @raycast.argument1 {"type":"text","placeholder":"输入要翻译的文本"}

# Optional parameters:
# @raycast.icon 📋
# @raycast.packageName es.utils

# Documentation:
# @raycast.author gitbyeos
# @raycast.authorURL https://raycast.com/gitbyeos

set -e

SERVER_URL="${SERVER_URL:-http://127.0.0.1:11878}"
INPUT_TEXT="${1:-}"

if [[ -z "$INPUT_TEXT" ]]
then
    INPUT_TEXT="$(pbpaste)"
fi


python3 - "$SERVER_URL" "$INPUT_TEXT" <<'PY'
import json
import sys
import urllib.error
import urllib.request

server_url = sys.argv[1].rstrip("/")
input_text = sys.argv[2]
system_prompt = "将以下文本翻译为中文，注意只需要输出翻译后的结果，不要额外解释"


def request(method, path, data=None):
    body = None if data is None else json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        f"{server_url}{path}",
        data=body,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))


def stream_request(path, data):
    body = json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        f"{server_url}{path}",
        data=body,
        method="POST",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as response:
        for raw_line in response:
            line = raw_line.decode("utf-8").strip()
            if not line.startswith("data: "):
                continue

            chunk = line.removeprefix("data: ").strip()
            if chunk == "[DONE]":
                break

            data = json.loads(chunk)
            delta = data["choices"][0].get("delta", {})
            content = delta.get("content")
            if content:
                print(content, end="", flush=True)
        print()


try:
    models = request("GET", "/v1/models")
    model_id = models["data"][0]["id"]
    stream_request(
        "/v1/chat/completions",
        {
            "model": model_id,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": input_text},
            ],
            "top_k": 20,
            "top_p": 0.6,
            "repetition_penalty": 1.05,
            "temperature": 0.7,
            "stream": True,
        },
    )
except (KeyError, IndexError, json.JSONDecodeError, urllib.error.URLError, TimeoutError) as exc:
    print(f"翻译失败: {exc}")
    sys.exit(1)
PY
