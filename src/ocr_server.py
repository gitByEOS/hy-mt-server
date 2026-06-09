#!/usr/bin/env python3
"""GLM-OCR 服务 - 提供图片文字识别 API"""
import base64
import json
import sys
import tempfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

OCR_HOST = "0.0.0.0"
OCR_PORT = 11879
MAX_IMAGE_BYTES = 5 * 1024 * 1024
MODEL_PATH = Path(__file__).parent.parent / "models" / "GLM-OCR"

_model = None
_processor = None


def load_model():
    """懒加载 GLM-OCR 模型"""
    global _model, _processor
    if _model is not None:
        return _model, _processor

    import torch
    from transformers import AutoModelForImageTextToText, AutoProcessor

    print(f"加载 GLM-OCR 模型: {MODEL_PATH}")
    _processor = AutoProcessor.from_pretrained(str(MODEL_PATH))
    _model = AutoModelForImageTextToText.from_pretrained(
        str(MODEL_PATH),
        torch_dtype="auto",
        device_map="mps",
    )
    print("GLM-OCR 模型已加载")
    return _model, _processor


def recognize_text(image_bytes: bytes) -> str:
    """使用 GLM-OCR 识别图片中的文字"""
    model, processor = load_model()

    # 将图片写入临时文件（GLM-OCR 需要文件路径）
    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
        f.write(image_bytes)
        temp_path = f.name

    try:
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "image", "url": temp_path},
                    {"type": "text", "text": "Text Recognition:"},
                ],
            }
        ]

        inputs = processor.apply_chat_template(
            messages,
            tokenize=True,
            add_generation_prompt=True,
            return_dict=True,
            return_tensors="pt",
        ).to(model.device)
        inputs.pop("token_type_ids", None)

        generated_ids = model.generate(**inputs, max_new_tokens=4096)
        output_text = processor.decode(
            generated_ids[0][inputs["input_ids"].shape[1]:],
            skip_special_tokens=True,
        )
        return output_text.strip()
    finally:
        Path(temp_path).unlink(missing_ok=True)


class OCRHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path == "/":
            self.send_json({"status": "ok", "model": "GLM-OCR"})
        elif self.path == "/health":
            self.send_json({"status": "healthy"})
        else:
            self.send_error(404)

    def do_POST(self):
        if self.path != "/api/ocr":
            self.send_json_error(404, "接口不存在")
            return

        try:
            data = self.read_json_body()
            image_data = data.get("image", "")
            if not isinstance(image_data, str) or "," not in image_data:
                raise ValueError("图片格式无效")

            header, encoded = image_data.split(",", 1)
            if not header.startswith("data:image/") or ";base64" not in header:
                raise ValueError("图片格式无效")

            image_bytes = base64.b64decode(encoded, validate=True)
            if len(image_bytes) > MAX_IMAGE_BYTES:
                raise ValueError("图片过大")

            text = recognize_text(image_bytes)
            self.send_json({"text": text})

        except ValueError as e:
            self.send_json_error(400, str(e))
        except Exception as e:
            self.send_json_error(500, f"OCR 失败: {e}")

    def read_json_body(self):
        length = int(self.headers.get("Content-Length", "0"))
        if length <= 0 or length > MAX_IMAGE_BYTES + 1024:
            raise ValueError("请求体无效")
        return json.loads(self.rfile.read(length).decode("utf-8"))

    def send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def send_json_error(self, status, message):
        self.send_json({"error": message}, status)

    def log_message(self, format, *args):
        return


def main():
    # 启动时预加载模型
    print("预加载 GLM-OCR 模型...")
    load_model()

    server = ThreadingHTTPServer((OCR_HOST, OCR_PORT), OCRHandler)
    print(f"GLM-OCR 服务已启动: http://127.0.0.1:{OCR_PORT}")
    print("按 Ctrl+C 可停止服务。")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止。")
        sys.exit(0)


if __name__ == "__main__":
    main()