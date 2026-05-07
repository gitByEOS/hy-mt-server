#!/bin/bash
set -e
SERVER_PORT=11878
PIP_INDEX_URL="${PIP_INDEX_URL:-https://pypi.tuna.tsinghua.edu.cn/simple}"

has_python_module() {
    python - "$1" <<'PY' &> /dev/null
import importlib.util
import sys

sys.exit(0 if importlib.util.find_spec(sys.argv[1]) else 1)
PY
}

install_model_launcher() {
    if [[ "$RUNTIME" == "mlx" ]]
    then
        if has_python_module "mlx_lm" && has_python_module "modelscope"
        then
            return
        fi

        if ! has_python_module "mlx_lm" || ! has_python_module "modelscope"
        then
            echo "📦 下载模型启动器: mlx-lm"
            echo "   PyPI 镜像: ${PIP_INDEX_URL}"
            pip install --upgrade --index-url "$PIP_INDEX_URL" mlx-lm modelscope
        fi
        return
    fi

    if has_python_module "llama_cpp" && has_python_module "modelscope"
    then
        return
    fi

    echo "📦 下载模型启动器: llama-cpp-python"
    echo "   PyPI 镜像: ${PIP_INDEX_URL}"
    echo "   llama-cpp-python 预编译源: ${LLAMA_CPP_WHEEL_INDEX}"
    pip install --upgrade \
        --index-url "$PIP_INDEX_URL" \
        --extra-index-url "$LLAMA_CPP_WHEEL_INDEX" \
        "llama-cpp-python[server]" \
        modelscope
}

download_model() {
    if [[ "$RUNTIME" == "mlx" ]]
    then
        if [[ ! -d "$MODEL_DIR" ]]
        then
            echo "⬇️  下载模型..."
            echo "   模型仓库: ${MODEL_REPO}"
            if ! modelscope download --model "$MODEL_REPO" --local_dir "$MODEL_DIR"
            then
                echo "❌ 模型下载失败。"
                echo "   请检查网络，或手动执行: modelscope download --model ${MODEL_REPO} --local_dir ${MODEL_DIR}"
                exit 1
            fi
        fi

        if [[ ! -d "$MLX_MODEL_DIR" ]]
        then
            echo "🔁 转换 MLX 模型..."
            mlx_lm.convert \
                --hf-path "$MODEL_DIR" \
                --mlx-path "$MLX_MODEL_DIR" \
                --quantize \
                --q-bits 8 \
                --trust-remote-code
        fi
        return
    fi

    if [[ -f "$MODEL_PATH" ]]
    then
        return
    fi

    echo "⬇️  下载模型..."
    echo "   模型文件: ${MODEL_FILE}"
    mkdir -p "$MODEL_DIR"
    if ! modelscope download --model "$MODEL_REPO" "$MODEL_FILE" --local_dir "$MODEL_DIR"
    then
        echo "❌ 模型下载失败。"
        echo "   请检查网络，或手动执行: modelscope download --model ${MODEL_REPO} ${MODEL_FILE} --local_dir ${MODEL_DIR}"
        exit 1
    fi
}

start_service() {
    echo "🚀 启动服务..."
    echo "   服务地址: http://127.0.0.1:${SERVER_PORT}"
    echo "   按 Ctrl+C 可停止服务。"

    # 完全离线模式，阻止任何网络请求
    export HF_HUB_OFFLINE=1
    export TRANSFORMERS_OFFLINE=1
    export HF_HUB_DISABLE_TELEMETRY=1
    export HF_HUB_DISABLE_IMPLICIT_TOKEN=1

    if [[ "$RUNTIME" == "mlx" ]]
    then
        echo "   模型: ${MLX_MODEL_DIR}"
        # 使用绝对路径
        local abs_model_path
        abs_model_path="$(cd "$MLX_MODEL_DIR" && pwd)"
        mlx_lm.server --model "$abs_model_path" --host "127.0.0.1" --port "$SERVER_PORT"
        return
    fi

    echo "   模型: ${MODEL_REPO}/${MODEL_FILE}"
    python -m llama_cpp.server \
        --model "$MODEL_PATH" \
        --model_alias "hunyuan" \
        --host "127.0.0.1" \
        --port "$SERVER_PORT"
}

# --- 1. 环境检查 ---
echo "🔍 正在检查运行环境..."
if ! command -v python3 &> /dev/null
then
    echo "❌ 错误：未找到 Python 3，请先安装。"
    exit 1
fi
ARCH="$(uname -m)"
CPU_BRAND="$(sysctl -n machdep.cpu.brand_string 2>/dev/null || true)"
if [[ "$ARCH" == "arm64" && "$CPU_BRAND" == *"Apple M"* ]]
then
    RUNTIME="mlx"
    MODEL_REPO="Tencent-Hunyuan/HY-MT1.5-1.8B"
    MODEL_DIR="models/HY-MT1.5-1.8B"
    MLX_MODEL_DIR="models/HY-MT1.5-1.8B-mlx-8bit"
elif [[ "$ARCH" == "x86_64" && "$CPU_BRAND" == *"Intel"* ]]
then
    RUNTIME="llama_cpp"
    MODEL_REPO="Tencent-Hunyuan/HY-MT1.5-1.8B-GGUF"
    MODEL_FILE="HY-MT1.5-1.8B-Q4_K_M.gguf"
    MODEL_DIR="models/HY-MT1.5-1.8B-GGUF"
    MODEL_PATH="${MODEL_DIR}/${MODEL_FILE}"
    LLAMA_CPP_WHEEL_INDEX="${LLAMA_CPP_WHEEL_INDEX:-https://abetlen.github.io/llama-cpp-python/whl/cpu}"
else
    echo "❌ 错误：仅支持 Apple Silicon 或 Intel 芯片的 Mac。"
    echo "   当前架构: ${ARCH}"
    echo "   当前 CPU: ${CPU_BRAND:-未知}"
    exit 1
fi
echo "✅ 环境检查通过。"

# --- 2. 设置 Python 虚拟环境 ---
if [[ ! -d "hy-mt-env" ]]
then
    echo "🐍 创建 Python 虚拟环境..."
    python3 -m venv hy-mt-env
fi
source hy-mt-env/bin/activate

# --- 3. 下载模型启动器 ---
install_model_launcher

# --- 4. 下载模型 ---
download_model

# --- 5. 启动服务 ---
start_service
