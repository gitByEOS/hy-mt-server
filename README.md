# HY-MT 本地服务脚本

用于在 Mac 本地启动腾讯 HY-MT 翻译模型服务。

支持：
- Apple Silicon：ModelScope 下载原始模型，本地转换为 MLX 8bit 后使用 `mlx-lm`
- Intel Mac：使用 `llama-cpp-python` + ModelScope GGUF 模型

## 环境要求

- macOS
- Python 3

## 启动服务

```bash
bash server.sh
```

默认服务地址：

```text
http://127.0.0.1:11878
```

首次启动大概需要5-10分钟，会自动创建虚拟环境、安装依赖、下载模型。


## 验证服务

服务启动后，另开一个终端执行：

```bash
bash verify.sh
```

## 文件说明

- `server.sh`：启动模型服务
- `verify.sh`：验证模型服务是否正常
- `hy-mt-env/`：脚本自动创建的 Python 虚拟环境