"""Sandbox 句柄：run / files / pause / resume / kill。"""

from __future__ import annotations

import urllib.parse
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .client import F2bClient


class Sandbox:
    def __init__(self, client: F2bClient, record: dict[str, Any]) -> None:
        self._client = client
        self._record = record

    @property
    def id(self) -> str:
        return str(self._record["id"])

    @property
    def data(self) -> dict[str, Any]:
        return self._record

    def refresh(self) -> dict[str, Any]:
        data = self._client.request(
            "GET",
            self._client.sandboxes_path(f"/{urllib.parse.quote(self.id)}"),
        )
        self._record = data["sandbox"]
        return self._record

    def run(
        self,
        cmd: str,
        *,
        cwd: str | None = None,
        timeout_ms: int | None = None,
        env: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        body: dict[str, Any] = {"cmd": cmd}
        if cwd is not None:
            body["cwd"] = cwd
        if timeout_ms is not None:
            body["timeoutMs"] = timeout_ms
        if env is not None:
            body["env"] = env
        data = self._client.request(
            "POST",
            self._client.sandboxes_path(f"/{urllib.parse.quote(self.id)}/commands"),
            body,
        )
        return data["result"]

    def run_stream(
        self,
        cmd: str,
        *,
        cwd: str | None = None,
        timeout_ms: int | None = None,
        env: dict[str, str] | None = None,
        on_event: Any | None = None,
    ) -> dict[str, Any]:
        """SSE 流式执行；on_event 可选回调每个事件 dict；返回最终 result。"""
        body: dict[str, Any] = {"cmd": cmd}
        if cwd is not None:
            body["cwd"] = cwd
        if timeout_ms is not None:
            body["timeoutMs"] = timeout_ms
        if env is not None:
            body["env"] = env
        result: dict[str, Any] | None = None
        stdout = ""
        stderr = ""
        for ev in self._client.iter_sse(
            self._client.sandboxes_path(
                f"/{urllib.parse.quote(self.id)}/commands/stream"
            ),
            body,
        ):
            if on_event is not None:
                on_event(ev)
            et = ev.get("type")
            if et == "stdout":
                stdout += str(ev.get("text") or "")
            elif et == "stderr":
                stderr += str(ev.get("text") or "")
            elif et == "result":
                result = ev.get("result")  # type: ignore[assignment]
            elif et == "error":
                from .errors import F2bError

                raise F2bError(
                    str(ev.get("code") or "INTERNAL"),
                    str(ev.get("message") or "stream error"),
                )
        if result is None:
            result = {
                "exitCode": 0,
                "stdout": stdout,
                "stderr": stderr,
                "durationMs": 0,
            }
        return result

    def write(self, path: str, content: str) -> None:
        self._client.request(
            "POST",
            self._client.sandboxes_path(f"/{urllib.parse.quote(self.id)}/files"),
            {"path": path, "content": content, "encoding": "utf8"},
        )

    def read(self, path: str) -> str:
        q = urllib.parse.urlencode({"path": path, "encoding": "utf8"})
        data = self._client.request(
            "GET",
            f"{self._client.sandboxes_path(f'/{urllib.parse.quote(self.id)}/files')}?{q}",
        )
        return str(data["file"]["content"])

    def list_files(self, path: str = "/home/user") -> list[dict[str, Any]]:
        q = urllib.parse.urlencode({"list": "1", "path": path})
        data = self._client.request(
            "GET",
            f"{self._client.sandboxes_path(f'/{urllib.parse.quote(self.id)}/files')}?{q}",
        )
        return list(data.get("entries") or [])

    def pause(self) -> dict[str, Any]:
        data = self._client.request(
            "POST",
            self._client.sandboxes_path(f"/{urllib.parse.quote(self.id)}/pause"),
        )
        self._record = data["sandbox"]
        return self._record

    def resume(self) -> dict[str, Any]:
        data = self._client.request(
            "POST",
            self._client.sandboxes_path(f"/{urllib.parse.quote(self.id)}/resume"),
        )
        self._record = data["sandbox"]
        return self._record

    def update(self, **input: Any) -> dict[str, Any]:
        """延期 timeoutMs / 合并 metadata。"""
        sb = self._client.update_sandbox(self.id, **input)
        self._record = sb.data
        return self._record

    def kill(self) -> dict[str, Any]:
        data = self._client.request(
            "DELETE",
            self._client.sandboxes_path(f"/{urllib.parse.quote(self.id)}"),
        )
        self._record = data["sandbox"]
        return self._record

    @classmethod
    def create(cls, client: F2bClient, **input: Any) -> Sandbox:
        return client.create_sandbox(**input)
