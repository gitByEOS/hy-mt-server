#!/usr/bin/env python3
import json
import socket
import sys
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

WEB_HOST = "0.0.0.0"
WEB_PORT = 11888
MODEL_URL = "http://127.0.0.1:11878"

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
      padding: 8px 8px 38px;
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
      height: 32px;
    }

    .hint {
      position: absolute;
      left: 18px;
      bottom: 0;
      color: var(--muted);
      font-size: 12px;
      line-height: 28px;
    }

    button {
      border: 0;
      border-radius: 999px;
      min-width: 92px;
      padding: 2px 22px;
      position: absolute;
      right: 20px;
      bottom: 2px;
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
      <div class="subtitle">输入任意语言，翻译为中文</div>
    </header>

    <main id="messages">
      <div class="empty" id="empty">局域网均可访问，输入文本，点击翻译。</div>
    </main>

    <div class="composer-wrap">
      <form class="composer" id="form">
        <textarea id="input" placeholder="输入要翻译的文本..." autofocus></textarea>
        <div class="actions">
          <div class="hint">提示：Shift+Enter 换行</div>
          <button id="submit" type="submit">翻译</button>
        </div>
      </form>
    </div>
  </div>

  <script>
    const form = document.getElementById("form");
    const input = document.getElementById("input");
    const submit = document.getElementById("submit");
    const messages = document.getElementById("messages");
    const empty = document.getElementById("empty");

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

    async function translate(text) {
      const answer = addMessage("assistant", "");
      const response = await fetch("/api/translate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text }),
      });

      if (!response.ok || !response.body) {
        answer.textContent = `翻译失败：${response.status}`;
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

      input.value = "";
      submit.disabled = true;
      addMessage("user", text);
      try {
        await translate(text);
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
        if self.path != "/api/translate":
            self.send_error(404)
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
            data = json.loads(self.rfile.read(length).decode("utf-8"))
            text = data["text"].strip()
            if not text:
                raise ValueError("empty text")
            self.proxy_translate(text)
        except (BrokenPipeError, ConnectionResetError):
            return
        except Exception as exc:
            self.send_json_error(500, f"翻译失败: {exc}")

    def send_json_error(self, status, message):
        body = json.dumps({"error": message}, ensure_ascii=False).encode("utf-8")
        try:
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            return

    def proxy_translate(self, text):
        models = request_json("GET", "/v1/models")
        model_id = pick_model_id(models)
        payload = {
            "model": model_id,
            "messages": [
                {
                    "role": "system",
                    "content": "将以下文本翻译为中文，注意只需要输出翻译后的结果，不要额外解释",
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
