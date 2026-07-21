# f2b · f2b-sdk-python

灵境云官方 **Python** SDK：创建沙箱 → 命令 → 文件 → 暂停/恢复 → 销毁；模板 / 用量 / 隧道。

> **1.0 前不发布 PyPI**。本地用 editable 或 `PYTHONPATH=src`。

## 安装（开发期）

```bash
cd f2b-sdk-python
python3 -m pip install -e .
# 或不安装：
export PYTHONPATH=src
```

## 60 秒 quickstart

先启动 [f2b-sandbox](https://github.com/f2b-dev/f2b-sandbox)：

```bash
cd ../f2b-sandbox && F2B_SANDBOX_BACKEND=fake pnpm dev
# → http://127.0.0.1:13287
```

```python
from f2b import F2bClient, Sandbox

client = F2bClient(base_url="http://127.0.0.1:13287")
# client = F2bClient(base_url="...", api_key="sk_live_...")  # F2B_AUTH_MODE=api_key 时

sbx = Sandbox.create(client, template="base")
print(sbx.run("echo hello")["stdout"])
sbx.write("/home/user/a.txt", "ok")
print(sbx.read("/home/user/a.txt"))
sbx.pause()
sbx.resume()
print(client.list_templates())
print(client.get_usage(7))
sbx.kill()
```

隧道（需 [f2b-tunnel](https://github.com/f2b-dev/f2b-tunnel)）：

```python
client = F2bClient(
    base_url="http://127.0.0.1:13287",
    tunnel_base_url="http://127.0.0.1:8790",
)
# 或经 BFF：
# client = F2bClient(base_url="http://127.0.0.1:13200", path_prefix="/api",
#                    tunnel_path_prefix="/api")

tun = client.create_tunnel(sandboxId=sbx.id, port=3000, targetUrl="http://127.0.0.1:3000")
print(tun["publicUrl"])
client.close_tunnel(tun["id"])
```

本仓：

```bash
# 需 sandbox :13287；可选 F2B_TUNNEL_URL=http://127.0.0.1:8790
python3 scripts/smoke.py     # → PY_SDK_SMOKE_OK
python3 examples/quickstart.py
```

## API 路径

| 配置 | 用途 |
|------|------|
| `base_url=http://127.0.0.1:13287`（默认 `path_prefix="/v1"`） | 直连 **f2b-sandbox** |
| `path_prefix="/api"` | 兼容 BFF `/api/sandboxes` |
| `tunnel_base_url` + `tunnel_path_prefix` | 直连 tunnel 或 BFF `/api/tunnels` |

浏览器控制台请走 **f2b-web BFF**，不要在前端塞管理密钥。本 SDK 适合 **服务端 / Agent 运行时**。

## 导出

- `F2bClient` / `LingjingClient`（别名）
- `Sandbox`（`create` / `run` / `run_stream` / `write` / `read` / `list_files` / `pause` / `resume` / `kill`）
- `F2bClient.get_usage` / `list_templates` / `list_tunnels` / `create_tunnel` / `close_tunnel`
- `F2bError` / `ErrorCode`

仅依赖 **Python 标准库**（`urllib`）。

## 相关

- 契约：https://github.com/f2b-dev/f2b-spec  
- 沙箱服务：https://github.com/f2b-dev/f2b-sandbox  
- TS SDK：https://github.com/f2b-dev/f2b-sdk-js  
- 组织：https://github.com/f2b-dev  

Apache-2.0
