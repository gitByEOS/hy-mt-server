# 离线翻译

用于在 Mac 本地启动腾讯 HY-MT 翻译模型服务，配合对话式网页，实现离线翻译

支持：

- Apple Silicon：ModelScope 下载原始模型，本地转换为 MLX 8bit 后使用 `mlx-lm`
- Intel Mac：使用 `llama-cpp-python` + ModelScope GGUF 模型
- OCR: 使用 Mac Vision python库

## 环境要求

- macOS
- Python 3

## 启动服务

```bash
./server.sh
```

默认服务地址：

```text
http://127.0.0.1:11878
```

首次启动大概需要5-10分钟，会自动创建虚拟环境、安装依赖、下载模型。

## 验证服务

服务启动后，另开一个终端执行：

```bash
./verify.sh
```

## 网页访问

1. 启动模型服务
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
ProxyPass /translate http://127.0.0.1:11888/
ProxyPassReverse /translate http://127.0.0.1:11888/
```
5. `sudo apachectl restart`，重启 apache 服务

## Raycast 对接

1. 先启动本地服务
2. 在 Raycast 输入 Create Script Command
3. 选择`fanyi.sh`

使用方式：

- 输入 `fanyi`，按 Tab，输入文本后执行

## 文件说明

- `server.sh`：启动模型服务
- `verify.sh`：验证模型服务是否正常
- `fanyi.sh`：翻译脚本
- `web_launch.sh`：启动网页并安装网页 OCR 依赖
- `web.py`：手机网页翻译入口
- `models/`：下载的模型
- `hy-mt-env/`：脚本自动创建的 Python 虚拟环境
