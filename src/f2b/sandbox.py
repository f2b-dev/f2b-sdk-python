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

    def write(
        self,
        path: str,
        content: str | bytes,
        *,
        encoding: str | None = None,
    ) -> None:
        """写文件。bytes 自动 base64；encoding 为 utf8|base64。"""
        import base64 as b64mod

        if isinstance(content, (bytes, bytearray)):
            body = {
                "path": path,
                "content": b64mod.b64encode(bytes(content)).decode("ascii"),
                "encoding": "base64",
            }
        else:
            enc = encoding or "utf8"
            body = {"path": path, "content": content, "encoding": enc}
        self._client.request(
            "POST",
            self._client.sandboxes_path(f"/{urllib.parse.quote(self.id)}/files"),
            body,
        )

    def read(self, path: str, *, encoding: str = "utf8") -> str:
        """读文件。encoding=utf8|base64，返回对应编码的字符串。"""
        q = urllib.parse.urlencode({"path": path, "encoding": encoding})
        data = self._client.request(
            "GET",
            f"{self._client.sandboxes_path(f'/{urllib.parse.quote(self.id)}/files')}?{q}",
        )
        return str(data["file"]["content"])

    def read_bytes(self, path: str) -> bytes:
        """以二进制读取文件。"""
        import base64 as b64mod

        return b64mod.b64decode(self.read(path, encoding="base64"))

    def list_files(self, path: str = "/home/user") -> list[dict[str, Any]]:
        q = urllib.parse.urlencode({"list": "1", "path": path})
        data = self._client.request(
            "GET",
            f"{self._client.sandboxes_path(f'/{urllib.parse.quote(self.id)}/files')}?{q}",
        )
        return list(data.get("entries") or [])

    def delete_file(self, path: str, *, recursive: bool = False) -> None:
        """删除文件；目录需 recursive=True。"""
        params: dict[str, str] = {"path": path}
        if recursive:
            params["recursive"] = "1"
        q = urllib.parse.urlencode(params)
        self._client.request(
            "DELETE",
            f"{self._client.sandboxes_path(f'/{urllib.parse.quote(self.id)}/files')}?{q}",
        )

    def mkdir(self, path: str, *, recursive: bool = True) -> None:
        """创建目录；默认 recursive=True。"""
        self._client.request(
            "POST",
            self._client.sandboxes_path(
                f"/{urllib.parse.quote(self.id)}/files/mkdir"
            ),
            {"path": path, "recursive": recursive},
        )

    def rename(self, from_path: str, to_path: str) -> None:
        """重命名或移动文件/目录。"""
        self._client.request(
            "POST",
            self._client.sandboxes_path(
                f"/{urllib.parse.quote(self.id)}/files/rename"
            ),
            {"from": from_path, "to": to_path},
        )

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
