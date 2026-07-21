#!/usr/bin/env python3
"""对 f2b-sandbox（+ 可选 tunnel）的冒烟：create → run → files → pause → templates/usage → tunnels → kill。"""

from __future__ import annotations

import http.server
import os
import sys
import threading
import urllib.request

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from f2b import ErrorCode, F2bClient, F2bError, Sandbox


def main() -> int:
    base = os.environ.get("F2B_SANDBOX_URL", "http://127.0.0.1:13287")
    tunnel_base = os.environ.get("F2B_TUNNEL_URL")  # 可选
    client = F2bClient(
        base_url=base,
        api_key=os.environ.get("F2B_API_KEY"),
        tunnel_base_url=tunnel_base,
    )

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

        paused = sbx.pause()
        if paused.get("status") != "paused":
            print("pause failed:", paused, file=sys.stderr)
            return 6
        try:
            sbx.run("echo should-fail")
            print("expected SANDBOX_NOT_RUNNING while paused", file=sys.stderr)
            return 7
        except F2bError as e:
            if e.code != ErrorCode.SANDBOX_NOT_RUNNING:
                print("unexpected pause error:", e, file=sys.stderr)
                return 7

        resumed = sbx.resume()
        if resumed.get("status") != "running":
            print("resume failed:", resumed, file=sys.stderr)
            return 8
        r2 = sbx.run("echo after-resume")
        if "after-resume" not in (r2.get("stdout") or ""):
            print("run after resume failed:", r2, file=sys.stderr)
            return 9

        templates = client.list_templates()
        ids = {t.get("id") for t in templates}
        if "base" not in ids:
            print("templates missing base:", templates, file=sys.stderr)
            return 10

        usage = client.get_usage(7)
        if not isinstance(usage, dict):
            print("usage shape:", usage, file=sys.stderr)
            return 11

        if tunnel_base:
            class _H(http.server.BaseHTTPRequestHandler):
                def do_GET(self) -> None:  # noqa: N802
                    body = b'{"ok":true,"marker":"py-tunnel-ok"}'
                    self.send_response(200)
                    self.send_header("content-type", "application/json")
                    self.end_headers()
                    self.wfile.write(body)

                def log_message(self, *_args: object) -> None:
                    return

            upstream = http.server.HTTPServer(("127.0.0.1", 0), _H)
            port = upstream.server_address[1]
            th = threading.Thread(target=upstream.serve_forever, daemon=True)
            th.start()
            try:
                tun = client.create_tunnel(
                    sandboxId=sbx.id,
                    port=port,
                    name="py-smoke-tun",
                    targetUrl=f"http://127.0.0.1:{port}",
                )
                public = tun["publicUrl"]
                with urllib.request.urlopen(public + "hello", timeout=10) as res:
                    text = res.read().decode()
                if "py-tunnel-ok" not in text:
                    print("tunnel proxy failed:", text, file=sys.stderr)
                    return 12
                closed = client.close_tunnel(tun["id"])
                if closed.get("status") != "closed":
                    print("close tunnel failed:", closed, file=sys.stderr)
                    return 13
            finally:
                upstream.shutdown()

        killed = sbx.kill()
        if killed.get("status") != "killed":
            print("kill failed:", killed, file=sys.stderr)
            return 14

        print("PY_SDK_SMOKE_OK", sbx.id)
        return 0
    except F2bError as e:
        print("smoke error:", e, file=sys.stderr)
        try:
            sbx.kill()
        except Exception:
            pass
        return 99


if __name__ == "__main__":
    raise SystemExit(main())
