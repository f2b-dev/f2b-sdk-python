#!/usr/bin/env python3
"""60 秒 quickstart：create → echo → write/read → kill。"""

from __future__ import annotations

import os
import sys

# 允许未 editable 安装时从 src 直接跑
_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from f2b import F2bClient, Sandbox


def main() -> None:
    base = os.environ.get("F2B_SANDBOX_URL", "http://127.0.0.1:13287")
    client = F2bClient(base_url=base, api_key=os.environ.get("F2B_API_KEY"))

    sbx = Sandbox.create(client, name="py-quickstart", template="base")
    print("created", sbx.id, sbx.data.get("status"))

    result = sbx.run("echo hello-from-python")
    print("stdout:", (result.get("stdout") or "").strip())

    sbx.write("/home/user/hello.txt", "lingjing-python")
    print("read:", sbx.read("/home/user/hello.txt"))

    print("pause", sbx.pause().get("status"))
    print("resume", sbx.resume().get("status"))
    print("templates", [t.get("id") for t in client.list_templates()])

    killed = sbx.kill()
    print("killed", killed.get("status"))


if __name__ == "__main__":
    main()
