#!/bin/bash

# Required parameters:
# @raycast.schemaVersion 1
# @raycast.title web_launch
# @raycast.mode compact

# Optional parameters:
# @raycast.icon 🌋

# Documentation:
# @raycast.author gitbyeos
# @raycast.authorURL https://raycast.com/gitbyeos

set -euo pipefail

WEB_PORT=11888
PIP_INDEX_URL="${PIP_INDEX_URL:-https://pypi.tuna.tsinghua.edu.cn/simple}"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON="${SCRIPT_DIR}/hy-mt-env/bin/python"
LOG_PATH="${SCRIPT_DIR}/web_launch.log"

cd "$SCRIPT_DIR"

ensure_python() {
    if ! command -v python3 &> /dev/null
    then
        echo "错误：未找到 Python 3，请先安装。"
        exit 1
    fi
}

ensure_venv() {
    if [[ ! -d "hy-mt-env" ]]
    then
        echo "🐍 创建 Python 虚拟环境..."
        python3 -m venv hy-mt-env
    fi
    source hy-mt-env/bin/activate
}

has_python_module() {
    "$PYTHON" - "$1" <<'PY' &> /dev/null
import importlib.util
import sys

sys.exit(0 if importlib.util.find_spec(sys.argv[1]) else 1)
PY
}

install_web_dependencies() {
    if has_python_module "Vision" && has_python_module "Quartz"
    then
        return
    fi

    echo "安装网页 OCR 依赖..."
    "$PYTHON" -m pip install --upgrade --index-url "$PIP_INDEX_URL" \
        pyobjc-framework-Vision \
        pyobjc-framework-Quartz
}

is_web_running() {
    "$PYTHON" - "$WEB_PORT" <<'PY'
import socket
import sys

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.settimeout(0.3)
    sys.exit(0 if sock.connect_ex(("127.0.0.1", int(sys.argv[1]))) == 0 else 1)
PY
}

local_ip() {
    "$PYTHON" <<'PY'
import socket

try:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        sock.connect(("8.8.8.8", 80))
        print(sock.getsockname()[0])
except OSError:
    print("127.0.0.1")
PY
}

wait_until_ready() {
    for _ in {1..20}
    do
        if is_web_running
        then
            return 0
        fi
        sleep 0.2
    done
    return 1
}

start_web() {
    nohup "$PYTHON" "${SCRIPT_DIR}/web.py" >> "$LOG_PATH" 2>&1 &
}

ensure_python
ensure_venv

if is_web_running
then
    echo "网页已运行：http://$(local_ip):${WEB_PORT}"
    exit 0
fi

install_web_dependencies
start_web

if wait_until_ready
then
    echo "网页已启动：http://$(local_ip):${WEB_PORT}"
    exit 0
fi

echo "网页启动失败，查看日志：${LOG_PATH}"
exit 1
