# 离线翻译

用于在 Mac 本地启动腾讯 HY-MT 翻译模型服务，配合对话式网页，实现离线翻译

支持：

- Apple Silicon：ModelScope 下载原始模型，本地转换为 MLX 8bit 后使用 `mlx-lm`
- Intel Mac：使用 `llama-cpp-python` + ModelScope GGUF 模型
- OCR: GLM-OCR 模型（Apple Silicon）或 Mac Vision（备选）

## 环境要求

- macOS
- Python 3

## 启动服务

### 翻译服务

```bash
./translate_server.sh
```

默认服务地址：

```text
http://0.0.0.0:11878
```

首次启动大概需要5-10分钟，会自动创建虚拟环境、安装依赖、下载模型。

### OCR 服务（可选）

```bash
./ocr_server.sh
```

默认服务地址：

```text
http://0.0.0.0:11879
```

## 验证服务

服务启动后，另开一个终端执行：

```bash
./tools/verify_translate.sh   # 验证翻译服务
./tools/verify_ocr.sh         # 验证 OCR 服务
```

## 网页访问

1. 启动翻译服务（和 OCR 服务，如需 OCR 功能）
2. 再开一个终端启动网页：
```bash
./web_launch.sh
```
3. 手机和电脑连接同一个 WiFi 后，打开类似下面的地址：
```text
http://电脑局域网IP:11888
```

### 反向代理
如果你觉得直接使用端口号不友好，你可以执行下列操作，这样你将获得一个`http://IP/translate`的代理入口

1. 编辑 `/etc/apache2/httpd.conf`
2. 搜索 `LoadModule proxy_module`，解开注释
3. 搜索 `LoadModule proxy_http_module`，解开注释
4. 文件尾部添加以下内容
```bash
# 开启反向代理功能
ProxyRequests Off
# 保留原始请求的域名
ProxyPreserveHost On

# 将所有访问 IP/translate 的请求，转发到本地的 11888 端口
ProxyPass /translate http://0.0.0.0:11888/
ProxyPassReverse /translate http://0.0.0.0:11888/
```
5. `sudo apachectl restart`，重启 apache 服务

## Raycast 对接

1. 先启动本地服务
2. 在 Raycast 输入 Create Script Command
3. 选择 `tools/fanyi.sh`

使用方式：

- 输入 `fanyi`，按 Tab，输入文本后执行

## 文件说明

```
hy-mt-server/
├── translate_server.sh    # 启动翻译模型服务
├── ocr_server.sh          # 启动 OCR 服务
├── web_launch.sh          # 启动网页服务
├── src/
│   ├── ocr_server.py      # OCR 服务实现（GLM-OCR）
│   └── web.py             # 网页翻译入口
├── tools/
│   ├── verify_translate.sh  # 验证翻译服务
│   ├── verify_ocr.sh        # 验证 OCR 服务
│   └── fanyi.sh             # Raycast 翻译脚本
├── models/                # 下载的模型
│   ├── Hy-MT2-1.8B/       # 翻译模型（原始）
│   ├── Hy-MT2-1.8B-mlx-8bit/  # 翻译模型（MLX 8bit）
│   └── GLM-OCR/           # OCR 模型
└── hy-mt-env/             # Python 虚拟环境（自动创建）
```