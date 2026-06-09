#!/bin/bash
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
OCR_URL="${OCR_URL:-http://127.0.0.1:11879}"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-60}"

echo "🔍 验证 GLM-OCR 服务: ${OCR_URL}"

source "${SCRIPT_DIR}/../hy-mt-env/bin/activate"
python3 - "$OCR_URL" "$TIMEOUT_SECONDS" <<'PY'
import base64
import io
import json
import sys
import time
import urllib.error
import urllib.request

ocr_url = sys.argv[1].rstrip("/")
timeout_seconds = int(sys.argv[2])


def request(path, data=None, timeout=30):
    body = None if data is None else json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        f"{ocr_url}{path}",
        data=body,
        method="POST" if data else "GET",
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=timeout) as response:
        return json.loads(response.read().decode("utf-8"))


def create_test_image(text, width=600, height=100):
    """创建带文字的测试图片"""
    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGB", (width, height), color="white")
    draw = ImageDraw.Draw(img)
    # 尝试多个支持中文的字体路径
    font_paths = [
        "/System/Library/Fonts/Supplemental/Arial Unicode.ttf",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/System/Library/Fonts/PingFang.ttc",
    ]
    font = None
    for fp in font_paths:
        try:
            font = ImageFont.truetype(fp, 32)
            break
        except Exception:
            continue
    if font is None:
        font = ImageFont.load_default()
    draw.text((30, 30), text, fill="black", font=font)
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    img_bytes = buffer.getvalue()
    return f"data:image/png;base64,{base64.b64encode(img_bytes).decode()}"


def ocr_api(image_data, timeout=120):
    """调用 OCR API"""
    result = request("/api/ocr", {"image": image_data}, timeout=timeout)
    return result.get("text", "").strip()


def validate_output(expected, output):
    """验证 OCR 输出"""
    if not output:
        return "输出为空"
    expected_words = expected.split()
    matched = sum(1 for word in expected_words if word.lower() in output.lower())
    if matched < len(expected_words) * 0.5:
        return f"识别不完整: 期望 '{expected}', 实际 '{output}'"
    return ""


# 等待服务就绪
deadline = time.time() + timeout_seconds
last_error = None

while time.time() < deadline:
    try:
        status = request("/", timeout=5)
        print(f"✅ 服务就绪: {status.get('model', 'GLM-OCR')}")
        break
    except (urllib.error.URLError, TimeoutError) as exc:
        last_error = exc
        time.sleep(2)
else:
    print(f"❌ 服务未启动: {last_error}")
    print("   请先运行: ./ocr_server.sh")
    sys.exit(1)

# 测试用例
cases = [
    {"name": "英文", "text": "Hello World Test"},
    {"name": "中文", "text": "你好世界 测试"},
    {"name": "混合", "text": "Hello 世界 Test 测试"},
    {"name": "数字", "text": "12345 67890"},
]

failed = []
for index, case in enumerate(cases, start=1):
    print(f"\n[{index}/{len(cases)}] {case['name']}")

    image_data = create_test_image(case["text"])
    started_at = time.time()

    try:
        output = ocr_api(image_data)
        elapsed = time.time() - started_at
    except urllib.error.HTTPError as exc:
        output = ""
        elapsed = time.time() - started_at
        print(f"   ❌ HTTP Error {exc.code}: {exc.read().decode()}")
        failed.append(case["name"])
        continue

    print(f"   原文: {case['text']}")
    print(f"   输出: {output or '<空>'}")
    print(f"   耗时: {elapsed:.2f}s")

    error = validate_output(case["text"], output)
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