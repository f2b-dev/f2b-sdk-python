#!/usr/bin/env python3
"""对 f2b-sandbox 的最小冒烟：create → run → write/read → list → kill。"""

from __future__ import annotations

import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from f2b import F2bClient, F2bError, Sandbox


def main() -> int:
    base = os.environ.get("F2B_SANDBOX_URL", "http://127.0.0.1:8787")
    client = F2bClient(base_url=base, api_key=os.environ.get("F2B_API_KEY"))

    try:
        sbx = Sandbox.create(client, name="py-smoke", template="base")
    except F2bError as e:
        print("create failed:", e, file=sys.stderr)
        return 1

    try:
        r = sbx.run("echo py-smoke-ok")
        out = (r.get("stdout") or "") + (r.get("stderr") or "")
        if r.get("exitCode") != 0 or "py-smoke-ok" not in out:
            print("run failed:", r, file=sys.stderr)
            return 2

        sbx.write("/home/user/smoke.txt", "py-ok")
        content = sbx.read("/home/user/smoke.txt")
        if content != "py-ok":
            print("file roundtrip failed:", content, file=sys.stderr)
            return 3

        entries = sbx.list_files("/home/user")
        if not isinstance(entries, list):
            print("list_files failed:", entries, file=sys.stderr)
            return 4

        listed = client.list_sandboxes()
        if not any(s.get("id") == sbx.id for s in listed):
            print("list_sandboxes missing id", file=sys.stderr)
            return 5

        killed = sbx.kill()
        if killed.get("status") != "killed":
            print("kill failed:", killed, file=sys.stderr)
            return 6

        print("PY_SDK_SMOKE_OK", sbx.id)
        return 0
    except F2bError as e:
        print("smoke error:", e, file=sys.stderr)
        try:
            sbx.kill()
        except Exception:
            pass
        return 10


if __name__ == "__main__":
    raise SystemExit(main())
