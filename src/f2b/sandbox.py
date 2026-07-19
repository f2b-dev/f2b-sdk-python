"""Sandbox 句柄：run / files / kill。"""

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
