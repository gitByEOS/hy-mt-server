#!/usr/bin/env python3
import base64
import binascii
import json
import socket
import sys
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

WEB_HOST = "0.0.0.0"
WEB_PORT = 11888
MODEL_URL = "http://127.0.0.1:11878"
MAX_REQUEST_BYTES = 7 * 1024 * 1024
MAX_OCR_IMAGE_BYTES = 5 * 1024 * 1024

HTML = r"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
  <title>离线翻译</title>
  <style>
    :root {
      color-scheme: dark;
      --bg: #151515;
      --panel: #2b2b2b;
      --panel-soft: #242424;
      --text: #f4f4f5;
      --muted: #9a9a9f;
      --border: #3a3a3c;
      --primary: #496dff;
      --primary-text: #ffffff;
      --assistant: transparent;
      --user: #2f2f2f;
      --shadow: rgba(0, 0, 0, 0.35);
    }

    * { box-sizing: border-box; }
    body {
      margin: 0;
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      background:
        radial-gradient(circle at 50% 0%, rgba(73, 109, 255, 0.08), transparent 34%),
        var(--bg);
      color: var(--text);
    }

    .app {
      min-height: 100dvh;
      display: flex;
      flex-direction: column;
      max-width: 880px;
      margin: 0 auto;
    }

    header {
      position: sticky;
      top: 0;
      z-index: 2;
      padding: 14px 18px;
      border-bottom: 1px solid rgba(255, 255, 255, 0.04);
      background: rgba(21, 21, 21, 0.82);
      backdrop-filter: blur(14px);
    }

    h1 {
      margin: 0;
      font-size: 18px;
      line-height: 1.2;
      font-weight: 650;
    }

    .subtitle {
      margin-top: 4px;
      color: var(--muted);
      font-size: 13px;
    }

    main {
      flex: 1;
      padding: 18px;
      padding-bottom: 126px;
    }

    .empty {
      margin-top: 20dvh;
      text-align: center;
      color: var(--muted);
    }

    .message {
      margin: 14px 0;
      display: flex;
    }

    .message.user { justify-content: flex-end; }
    .bubble {
      max-width: 86%;
      padding: 12px 15px;
      border: 0;
      border-radius: 14px;
      white-space: pre-wrap;
      line-height: 1.65;
      word-break: break-word;
      background: var(--assistant);
    }

    .user .bubble {
      background: var(--user);
      color: #f5f5f5;
    }

    .preview-image {
      display: block;
      max-width: 240px;
      max-height: 320px;
      border-radius: 12px;
      object-fit: contain;
    }

    .message-status {
      margin-top: 8px;
      color: var(--muted);
      font-size: 13px;
    }

    .composer-wrap {
      position: fixed;
      left: 0;
      right: 0;
      bottom: 0;
      padding: 8px 12px max(8px, env(safe-area-inset-bottom));
      background: linear-gradient(to top, var(--bg) 78%, rgba(21, 21, 21, 0));
    }

    .composer {
      position: relative;
      max-width: 880px;
      margin: 0 auto;
      background: var(--panel);
      border: 1px solid var(--border);
      border-radius: 16px;
      padding: 8px 8px 44px;
      box-shadow: 0 18px 44px var(--shadow);
    }

    textarea {
      width: 100%;
      min-height: 56px;
      max-height: 180px;
      resize: none;
      border: 0;
      outline: 0;
      color: var(--text);
      background: transparent;
      font: inherit;
      line-height: 1.5;
      padding: 8px;
    }

    textarea::placeholder {
      color: #77777c;
    }

    .actions {
      position: absolute;
      left: 0;
      right: 0;
      bottom: 0;
      height: 38px;
    }

    .language-controls {
      position: absolute;
      left: 12px;
      bottom: 5px;
      display: flex;
      align-items: center;
      gap: 6px;
      color: var(--muted);
      font-size: 12px;
    }

    .language-label {
      color: var(--muted);
      white-space: nowrap;
    }

    .hint {
      color: var(--muted);
      margin-left: 8px;
      white-space: nowrap;
    }

    .language-controls select {
      border: 1px solid var(--border);
      border-radius: 999px;
      padding: 4px 10px;
      color: var(--text);
      background: var(--panel-soft);
      font: inherit;
      outline: 0;
    }

    button {
      border: 0;
      border-radius: 999px;
      min-width: 92px;
      padding: 2px 22px;
      position: absolute;
      right: 20px;
      bottom: 5px;
      background: var(--primary);
      color: var(--primary-text);
      font-size: 18px;
     
      cursor: pointer;
      box-shadow: 0 8px 22px rgba(73, 109, 255, 0.26);
    }

    button:disabled {
      opacity: 0.55;
      cursor: not-allowed;
    }
  </style>
</head>
<body>
  <div class="app">
    <header>
      <h1>离线翻译</h1>
      <div class="subtitle">优先翻译成第一语言，如果输入为第一语言则翻译成第二语言</div>
    </header>

    <main id="messages">
      <div class="empty" id="empty">局域网均可访问，输入文本，点击翻译。</div>
    </main>

    <div class="composer-wrap">
      <form class="composer" id="form">
        <textarea id="input" placeholder="输入要翻译的文本..." autofocus></textarea>
        <div class="actions">
          <div class="language-controls" aria-label="翻译语言">
            <span class="language-label">第一语言</span>
            <select id="first-language" aria-label="第一语言">
              <option value="中文">中文</option>
              <option value="英文">英文</option>
              <option value="日文">日文</option>
              <option value="韩文">韩文</option>
              <option value="法文">法文</option>
              <option value="德文">德文</option>
              <option value="西班牙文">西班牙文</option>
            </select>
            <span>→</span>
            <span class="language-label">第二语言</span>
            <select id="second-language" aria-label="第二语言">
              <option value="英文">英文</option>
              <option value="中文">中文</option>
              <option value="日文">日文</option>
              <option value="韩文">韩文</option>
              <option value="法文">法文</option>
              <option value="德文">德文</option>
              <option value="西班牙文">西班牙文</option>
            </select>
            <span class="hint">提示：Shift+Enter 换行</span>
          </div>
          <button id="submit" type="submit">翻译</button>
        </div>
      </form>
    </div>
  </div>

  <script>
    const form = document.getElementById("form");
    const input = document.getElementById("input");
    const submit = document.getElementById("submit");
    const firstLanguage = document.getElementById("first-language");
    const secondLanguage = document.getElementById("second-language");
    const messages = document.getElementById("messages");
    const empty = document.getElementById("empty");
    const apiBasePath = window.location.pathname.replace(/\/$/, "");
    const translateApiPath = apiBasePath === "" ? "/api/translate" : `${apiBasePath}/api/translate`;
    const ocrApiPath = apiBasePath === "" ? "/api/ocr" : `${apiBasePath}/api/ocr`;
    const ocrImageMaxSide = 1280;
    const ocrImageQuality = 0.8;

    function addMessage(role, text = "") {
      empty?.remove();
      const row = document.createElement("div");
      row.className = `message ${role}`;
      const bubble = document.createElement("div");
      bubble.className = "bubble";
      bubble.textContent = text;
      row.appendChild(bubble);
      messages.appendChild(row);
      window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" });
      return bubble;
    }

    function addImageMessage(imageUrl) {
      empty?.remove();
      const row = document.createElement("div");
      row.className = "message user";
      const bubble = document.createElement("div");
      bubble.className = "bubble";
      const image = document.createElement("img");
      image.className = "preview-image";
      image.src = imageUrl;
      image.alt = "待识别图片";
      const status = document.createElement("div");
      status.className = "message-status";
      status.textContent = "正在识别...";
      bubble.appendChild(image);
      bubble.appendChild(status);
      row.appendChild(bubble);
      messages.appendChild(row);
      window.scrollTo({ top: document.body.scrollHeight, behavior: "smooth" });
      return status;
    }

    async function readError(response, fallback) {
      const data = await response.json().catch(() => ({ error: fallback }));
      return data.error || fallback;
    }

    function pickPastedImage(event) {
      const items = Array.from(event.clipboardData?.items || []);
      const imageItem = items.find((item) => item.type.startsWith("image/"));
      return imageItem?.getAsFile() || null;
    }

    function blobToDataUrl(blob) {
      return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.onload = () => resolve(reader.result);
        reader.onerror = () => reject(reader.error);
        reader.readAsDataURL(blob);
      });
    }

    function canvasToBlob(canvas) {
      return new Promise((resolve, reject) => {
        canvas.toBlob(
          (blob) => blob ? resolve(blob) : reject(new Error("图片压缩失败")),
          "image/jpeg",
          ocrImageQuality,
        );
      });
    }

    async function compressImage(file) {
      const image = await createImageBitmap(file);
      const scale = Math.min(1, ocrImageMaxSide / Math.max(image.width, image.height));
      const canvas = document.createElement("canvas");
      canvas.width = Math.round(image.width * scale);
      canvas.height = Math.round(image.height * scale);
      const context = canvas.getContext("2d");
      context.drawImage(image, 0, 0, canvas.width, canvas.height);
      image.close();
      const blob = await canvasToBlob(canvas);
      return blobToDataUrl(blob);
    }

    async function recognizeImage(imageData) {
      const response = await fetch(ocrApiPath, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ image: imageData }),
      });
      const data = await response.json().catch(() => ({}));
      if (!response.ok) {
        throw new Error(data.error || "OCR 失败");
      }
      return data.text || "";
    }

    async function handleImagePaste(event) {
      const file = pickPastedImage(event);
      if (!file) return;

      event.preventDefault();
      submit.disabled = true;
      let status = null;
      try {
        const imageData = await compressImage(file);
        status = addImageMessage(imageData);
        const text = await recognizeImage(imageData);
        status.textContent = `检测到文本：\n${text}`;
        await translate(text, firstLanguage.value, secondLanguage.value);
      } catch (error) {
        if (status) {
          status.textContent = error.message;
        } else {
          addMessage("assistant", `OCR 失败：${error.message}`);
        }
      } finally {
        submit.disabled = false;
        input.focus();
      }
    }

    async function translate(text, firstLanguageValue, secondLanguageValue) {
      const answer = addMessage("assistant", "");
      const response = await fetch(translateApiPath, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text,
          first_language: firstLanguageValue,
          second_language: secondLanguageValue,
        }),
      });

      if (!response.ok || !response.body) {
        answer.textContent = `翻译失败：${await readError(response, `HTTP ${response.status}`)}`;
        return;
      }

      const reader = response.body.getReader();
      const decoder = new TextDecoder();
      while (true) {
        const { value, done } = await reader.read();
        if (done) break;
        answer.textContent += decoder.decode(value, { stream: true });
        window.scrollTo({ top: document.body.scrollHeight });
      }
    }

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const text = input.value.trim();
      if (!text) return;

      const firstLanguageValue = firstLanguage.value;
      const secondLanguageValue = secondLanguage.value;
      input.value = "";
      submit.disabled = true;
      addMessage("user", text);
      try {
        await translate(text, firstLanguageValue, secondLanguageValue);
      } catch (error) {
        addMessage("assistant", `翻译失败：${error.message}`);
      } finally {
        submit.disabled = false;
        input.focus();
      }
    });

    input.addEventListener("keydown", (event) => {
      if (event.key !== "Enter" || event.shiftKey || event.isComposing) {
        return;
      }

      event.preventDefault();
      form.requestSubmit();
    });

    input.addEventListener("paste", (event) => {
      handleImagePaste(event).catch((error) => {
        addMessage("assistant", `OCR 失败：${error.message}`);
      });
    });
  </script>
</body>
</html>
"""


def request_json(method, path, data=None):
    body = None if data is None else json.dumps(data).encode("utf-8")
    req = urllib.request.Request(
        f"{MODEL_URL}{path}",
        data=body,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=120) as response:
        return json.loads(response.read().decode("utf-8"))


def pick_model_id(models):
    for model in models["data"]:
        model_id = model["id"]
        if model_id.startswith("/") or "/" not in model_id:
            return model_id
    return models["data"][0]["id"]


def local_ips():
    ips = ["127.0.0.1"]
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            ip = sock.getsockname()[0]
            if not ip.startswith("127.") and ip not in ips:
                ips.append(ip)
    except OSError:
        pass
    return ips


class RequestError(Exception):
    status = 400


class ServerError(Exception):
    status = 500


def decode_image_data_url(image_data):
    if not isinstance(image_data, str):
        raise RequestError("图片不能为空")
    if "," not in image_data:
        raise RequestError("图片格式无效")

    header, encoded = image_data.split(",", 1)
    if not header.startswith("data:image/") or ";base64" not in header:
        raise RequestError("图片格式无效")

    try:
        image_bytes = base64.b64decode(encoded, validate=True)
    except (binascii.Error, ValueError) as exc:
        raise RequestError("图片格式无效") from exc

    if not image_bytes:
        raise RequestError("图片不能为空")
    if len(image_bytes) > MAX_OCR_IMAGE_BYTES:
        raise RequestError("图片过大")
    return image_bytes


def recognize_text_with_vision(image_bytes):
    try:
        import Quartz
        import Vision
        from Foundation import NSData
    except ImportError as exc:
        raise ServerError("缺少 OCR 依赖，请安装 pyobjc-framework-Vision 和 pyobjc-framework-Quartz") from exc

    data = NSData.dataWithBytes_length_(image_bytes, len(image_bytes))
    source = Quartz.CGImageSourceCreateWithData(data, None)
    if source is None:
        raise RequestError("图片格式无效")

    cg_image = Quartz.CGImageSourceCreateImageAtIndex(source, 0, None)
    if cg_image is None:
        raise RequestError("图片格式无效")

    request = Vision.VNRecognizeTextRequest.alloc().init()
    request.setRecognitionLevel_(Vision.VNRequestTextRecognitionLevelAccurate)
    request.setUsesLanguageCorrection_(True)
    try:
        request.setRecognitionLanguages_(
            ["zh-Hans", "en-US", "ja-JP", "ko-KR", "fr-FR", "de-DE", "es-ES"]
        )
    except Exception:
        pass

    handler = Vision.VNImageRequestHandler.alloc().initWithCGImage_options_(cg_image, {})
    success, error = handler.performRequests_error_([request], None)
    if not success:
        reason = error.localizedDescription() if error else "未知错误"
        raise ServerError(f"OCR 失败: {reason}")

    lines = []
    for observation in request.results() or []:
        candidates = observation.topCandidates_(1)
        if not candidates:
            continue
        text = candidates[0].string().strip()
        if text:
            lines.append(text)

    if not lines:
        raise RequestError("未识别到文字")
    return "\n".join(lines)


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path != "/":
            self.send_error(404)
            return

        content = HTML.encode("utf-8")
        try:
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        except (BrokenPipeError, ConnectionResetError):
            return

    def do_POST(self):
        try:
            if self.path == "/api/translate":
                self.handle_translate()
                return
            if self.path == "/api/ocr":
                self.handle_ocr()
                return
            self.send_json_error(404, "接口不存在")
        except (BrokenPipeError, ConnectionResetError):
            return
        except RequestError as exc:
            self.send_json_error(exc.status, str(exc))
        except ServerError as exc:
            self.send_json_error(exc.status, str(exc))
        except Exception as exc:
            self.send_json_error(500, f"服务失败: {exc}")

    def read_json_body(self):
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError as exc:
            raise RequestError("请求长度无效") from exc

        if length <= 0:
            raise RequestError("请求体不能为空")
        if length > MAX_REQUEST_BYTES:
            raise RequestError("请求体过大")

        try:
            return json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise RequestError("JSON 格式无效") from exc

    def handle_translate(self):
        data = self.read_json_body()
        text = str(data.get("text", "")).strip()
        first_language = str(data.get("first_language", "")).strip()
        second_language = str(data.get("second_language", "")).strip()
        if not text:
            raise RequestError("文本不能为空")
        if not first_language or not second_language:
            raise RequestError("语言不能为空")
        self.proxy_translate(text, first_language, second_language)

    def handle_ocr(self):
        data = self.read_json_body()
        image_bytes = decode_image_data_url(data.get("image"))
        text = recognize_text_with_vision(image_bytes)
        self.send_json({"text": text})

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            return

    def send_json_error(self, status, message):
        body = json.dumps({"error": message}, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            return

    def proxy_translate(self, text, first_language, second_language):
        models = request_json("GET", "/v1/models")
        model_id = pick_model_id(models)
        system_prompt = (
            f"判断以下文本是否为{first_language}。"
            f"如果是{first_language}，翻译为{second_language}；"
            f"否则翻译为{first_language}。"
            "只输出翻译后的结果，不要额外解释。"
        )
        payload = {
            "model": model_id,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {"role": "user", "content": text},
            ],
            "top_k": 20,
            "top_p": 0.6,
            "repetition_penalty": 1.05,
            "temperature": 0.7,
            "stream": True,
        }

        body = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{MODEL_URL}/v1/chat/completions",
            data=body,
            method="POST",
            headers={"Content-Type": "application/json"},
        )

        try:
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Cache-Control", "no-cache")
            self.end_headers()
        except (BrokenPipeError, ConnectionResetError):
            return

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
                    try:
                        self.wfile.write(content.encode("utf-8"))
                        self.wfile.flush()
                    except (BrokenPipeError, ConnectionResetError):
                        return

    def log_message(self, format, *args):
        return


def main():
    server = ThreadingHTTPServer((WEB_HOST, WEB_PORT), Handler)
    print("网页服务已启动：")
    for ip in local_ips():
        print(f"  http://{ip}:{WEB_PORT}")
    print("需连接同一个 WiFi。")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止。")
        sys.exit(0)


if __name__ == "__main__":
    main()
