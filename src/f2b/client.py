"""HTTP 客户端：默认对接 f2b-sandbox `/v1`；隧道可走独立 base。"""

from __future__ import annotations

import json
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Mapping

from .errors import ErrorCode, F2bError
from .sandbox import Sandbox


class F2bClient:
    def __init__(
        self,
        *,
        base_url: str,
        path_prefix: str = "/v1",
        tunnel_base_url: str | None = None,
        tunnel_path_prefix: str = "/v1",
        api_key: str | None = None,
        timeout_sec: float = 60.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        prefix = path_prefix if path_prefix.startswith("/") else f"/{path_prefix}"
        self.path_prefix = prefix.rstrip("/")
        # 隧道默认与 base 相同；BFF 可设 tunnel_path_prefix="/api"
        self.tunnel_base_url = (tunnel_base_url or base_url).rstrip("/")
        t_prefix = (
            tunnel_path_prefix
            if tunnel_path_prefix.startswith("/")
            else f"/{tunnel_path_prefix}"
        )
        self.tunnel_path_prefix = t_prefix.rstrip("/")
        self.api_key = api_key
        self.timeout_sec = timeout_sec

    def _headers(self, json_body: bool) -> dict[str, str]:
        h: dict[str, str] = {"Accept": "application/json"}
        if json_body:
            h["Content-Type"] = "application/json"
        if self.api_key:
            h["Authorization"] = f"Bearer {self.api_key}"
        return h

    def sandboxes_path(self, sub: str = "") -> str:
        base = f"{self.path_prefix}/sandboxes"
        if not sub:
            return base
        return f"{base}{sub if sub.startswith('/') else '/' + sub}"

    def tunnels_path(self, sub: str = "") -> str:
        base = f"{self.tunnel_path_prefix}/tunnels"
        if not sub:
            return base
        return f"{base}{sub if sub.startswith('/') else '/' + sub}"

    def request_at(
        self,
        root: str,
        method: str,
        path: str,
        body: Mapping[str, Any] | None = None,
    ) -> Any:
        url = f"{root.rstrip('/')}{path}"
        data = None if body is None else json.dumps(body).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers=self._headers(body is not None),
            method=method.upper(),
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout_sec) as res:
                raw = res.read().decode("utf-8")
                status = res.status
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8") if e.fp else ""
            status = e.code
            payload = _safe_json(raw)
            err = (payload or {}).get("error") or {}
            raise F2bError(
                err.get("code") or ErrorCode.INTERNAL,
                err.get("message") or f"HTTP {status}",
                status=status,
                details=err.get("details"),
                cause=e,
            ) from e
        except urllib.error.URLError as e:
            raise F2bError(
                ErrorCode.BACKEND_UNAVAILABLE,
                str(e.reason) if getattr(e, "reason", None) else str(e),
                cause=e,
            ) from e

        if status >= 400:
            payload = _safe_json(raw) or {}
            err = payload.get("error") or {}
            raise F2bError(
                err.get("code") or ErrorCode.INTERNAL,
                err.get("message") or f"HTTP {status}",
                status=status,
                details=err.get("details"),
            )

        if not raw:
            return None
        return json.loads(raw)

    def request(
        self,
        method: str,
        path: str,
        body: Mapping[str, Any] | None = None,
    ) -> Any:
        return self.request_at(self.base_url, method, path, body)

    def iter_sse(
        self,
        path: str,
        body: Mapping[str, Any] | None = None,
    ):
        """POST 并解析 text/event-stream；yield 每个 data JSON 对象。"""
        import json as _json

        url = f"{self.base_url}{path}"
        data = None if body is None else _json.dumps(body).encode("utf-8")
        headers = self._headers(body is not None)
        headers["Accept"] = "text/event-stream, application/json"
        req = urllib.request.Request(
            url, data=data, headers=headers, method="POST"
        )
        try:
            res = urllib.request.urlopen(req, timeout=self.timeout_sec)
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8") if e.fp else ""
            payload = _safe_json(raw)
            err = (payload or {}).get("error") or {}
            raise F2bError(
                err.get("code") or ErrorCode.INTERNAL,
                err.get("message") or f"HTTP {e.code}",
                status=e.code,
                details=err.get("details"),
                cause=e,
            ) from e
        except urllib.error.URLError as e:
            raise F2bError(
                ErrorCode.BACKEND_UNAVAILABLE,
                str(e.reason) if getattr(e, "reason", None) else str(e),
                cause=e,
            ) from e

        ctype = res.headers.get("Content-Type") or ""
        if "text/event-stream" not in ctype:
            raw = res.read().decode("utf-8")
            payload = _safe_json(raw) or {}
            if payload.get("result") is not None:
                yield {"type": "result", "result": payload["result"]}
                return
            err = payload.get("error") or {}
            raise F2bError(
                err.get("code") or ErrorCode.INTERNAL,
                err.get("message") or "expected event-stream",
                status=getattr(res, "status", None),
            )

        buf = ""
        while True:
            chunk = res.read(256)
            if not chunk:
                break
            buf += chunk.decode("utf-8", errors="replace")
            while "\n\n" in buf:
                block, buf = buf.split("\n\n", 1)
                data_line = None
                for line in block.split("\n"):
                    if line.startswith("data: "):
                        data_line = line[6:]
                        break
                if data_line is None or data_line in ("", "{}"):
                    continue
                try:
                    ev = _json.loads(data_line)
                except _json.JSONDecodeError:
                    continue
                if isinstance(ev, dict):
                    yield ev

    def list_sandboxes(
        self,
        project_id: str | None = None,
        *,
        status: str | None = None,
    ) -> list[dict[str, Any]]:
        params: dict[str, str] = {}
        if project_id:
            params["projectId"] = project_id
        if status:
            params["status"] = status
        q = f"?{urllib.parse.urlencode(params)}" if params else ""
        data = self.request("GET", f"{self.sandboxes_path()}{q}")
        return list(data.get("sandboxes") or [])

    def create_sandbox(self, **input: Any) -> Sandbox:
        data = self.request("POST", self.sandboxes_path(), input or {})
        return Sandbox(self, data["sandbox"])

    def get_sandbox(self, sandbox_id: str) -> Sandbox:
        data = self.request(
            "GET",
            self.sandboxes_path(f"/{urllib.parse.quote(sandbox_id)}"),
        )
        return Sandbox(self, data["sandbox"])

    def update_sandbox(self, sandbox_id: str, **input: Any) -> Sandbox:
        """延期 timeoutMs / 合并 metadata（活动沙箱）。"""
        data = self.request(
            "PATCH",
            self.sandboxes_path(f"/{urllib.parse.quote(sandbox_id)}"),
            input or {},
        )
        return Sandbox(self, data["sandbox"])

    def get_usage(self, days: int = 7) -> dict[str, Any]:
        n = max(1, min(90, int(days)))
        data = self.request("GET", f"{self.path_prefix}/usage?days={n}")
        return data.get("usage") or data

    def list_templates(self) -> list[dict[str, Any]]:
        data = self.request("GET", f"{self.path_prefix}/templates")
        return list(data.get("templates") or [])

    def list_tunnels(self, sandbox_id: str | None = None) -> list[dict[str, Any]]:
        q = (
            f"?sandboxId={urllib.parse.quote(sandbox_id)}"
            if sandbox_id
            else ""
        )
        data = self.request_at(
            self.tunnel_base_url,
            "GET",
            f"{self.tunnels_path()}{q}",
        )
        return list(data.get("tunnels") or [])

    def create_tunnel(self, **input: Any) -> dict[str, Any]:
        data = self.request_at(
            self.tunnel_base_url,
            "POST",
            self.tunnels_path(),
            input or {},
        )
        return data["tunnel"]

    def get_tunnel(self, tunnel_id: str) -> dict[str, Any]:
        data = self.request_at(
            self.tunnel_base_url,
            "GET",
            self.tunnels_path(f"/{urllib.parse.quote(tunnel_id)}"),
        )
        return data["tunnel"]

    def close_tunnel(self, tunnel_id: str) -> dict[str, Any]:
        data = self.request_at(
            self.tunnel_base_url,
            "DELETE",
            self.tunnels_path(f"/{urllib.parse.quote(tunnel_id)}"),
        )
        return data["tunnel"]


class LingjingClient(F2bClient):
    """灵境云品牌别名。"""


def _safe_json(raw: str) -> dict[str, Any] | None:
    if not raw:
        return None
    try:
        val = json.loads(raw)
        return val if isinstance(val, dict) else None
    except json.JSONDecodeError:
        return None
