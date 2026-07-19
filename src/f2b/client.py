"""HTTP 客户端：默认对接 f2b-sandbox `/v1/sandboxes`。"""

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
        api_key: str | None = None,
        timeout_sec: float = 60.0,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        prefix = path_prefix if path_prefix.startswith("/") else f"/{path_prefix}"
        self.path_prefix = prefix.rstrip("/")
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

    def request(
        self,
        method: str,
        path: str,
        body: Mapping[str, Any] | None = None,
    ) -> Any:
        url = f"{self.base_url}{path}"
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

    def list_sandboxes(self, project_id: str | None = None) -> list[dict[str, Any]]:
        q = f"?projectId={urllib.parse.quote(project_id)}" if project_id else ""
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
