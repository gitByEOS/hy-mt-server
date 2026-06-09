#!/bin/bash
set -e
OCR_PORT=11879
PIP_INDEX_URL="${PIP_INDEX_URL:-https://pypi.tuna.tsinghua.edu.cn/simple}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
MODEL_DIR="${SCRIPT_DIR}/models/GLM-OCR"

has_python_module() {
    python - "$1" <<'PY' &> /dev/null
import importlib.util
import sys
sys.exit(0 if importlib.util.find_spec(sys.argv[1]) else 1)
PY
}

install_ocr_dependencies() {
    if has_python_module "torch" && has_python_module "transformers" && has_python_module "accelerate" && has_python_module "torchvision"
    then
        return
    fi

    echo "📦 安装 GLM-OCR 依赖..."
    echo "   PyPI 镜像: ${PIP_INDEX_URL}"
    pip install --upgrade --index-url "$PIP_INDEX_URL" torch transformers accelerate torchvision Pillow
}

check_model() {
    if [[ ! -d "$MODEL_DIR" ]]
    then
        echo "❌ 模型未下载: ${MODEL_DIR}"
        echo "   请执行: modelscope download --model ZhipuAI/GLM-OCR --local_dir ${MODEL_DIR}"
        exit 1
    fi
    echo "✅ 模型已就绪: ${MODEL_DIR}"
}

start_service() {
    echo "🚀 启动 GLM-OCR 服务..."
    echo "   服务地址: http://0.0.0.0:${OCR_PORT}"
    echo "   按 Ctrl+C 可停止服务。"

    export HF_HUB_OFFLINE=1
    export TRANSFORMERS_OFFLINE=1
    export HF_HUB_DISABLE_TELEMETRY=1
    export HF_HUB_DISABLE_IMPLICIT_TOKEN=1

    python "${SCRIPT_DIR}/src/ocr_server.py"
}

# --- 1. 环境检查 ---
echo "🔍 正在检查运行环境..."
if ! command -v python3 &> /dev/null
then
    echo "❌ 错误：未找到 Python 3，请先安装。"
    exit 1
fi

ARCH="$(uname -m)"
if [[ "$ARCH" != "arm64" ]]
then
    echo "⚠️  GLM-OCR 目前主要支持 Apple Silicon (arm64)"
    echo "   当前架构: ${ARCH}"
fi
echo "✅ 环境检查通过。"

# --- 2. 设置 Python 虚拟环境 ---
if [[ ! -d "hy-mt-env" ]]
then
    echo "🐍 创建 Python 虚拟环境..."
    python3 -m venv hy-mt-env
fi
source hy-mt-env/bin/activate

# --- 3. 安装依赖 ---
install_ocr_dependencies

# --- 4. 检查模型 ---
check_model

# --- 5. 启动服务 ---
start_service