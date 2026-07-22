"""错误码与异常（对齐 f2b-spec ErrorCode / errors/codes.json）。"""

from __future__ import annotations

from typing import Any


class ErrorCode:
    """与 @f2b/spec ErrorCode 字符串值一致；勿自造别名（如 CAPACITY_FULL / VALIDATION）。"""

    VALIDATION_ERROR = "VALIDATION_ERROR"
    INVALID_PATH = "INVALID_PATH"
    UNAUTHORIZED = "UNAUTHORIZED"
    NOT_FOUND = "NOT_FOUND"
    SANDBOX_NOT_FOUND = "SANDBOX_NOT_FOUND"
    TUNNEL_NOT_FOUND = "TUNNEL_NOT_FOUND"
    SANDBOX_NOT_RUNNING = "SANDBOX_NOT_RUNNING"
    SANDBOX_ALREADY_TERMINAL = "SANDBOX_ALREADY_TERMINAL"
    TUNNEL_ALREADY_CLOSED = "TUNNEL_ALREADY_CLOSED"
    COMMAND_TIMEOUT = "COMMAND_TIMEOUT"
    COMMAND_FAILED = "COMMAND_FAILED"
    CAPACITY_EXCEEDED = "CAPACITY_EXCEEDED"
    BACKEND_UNAVAILABLE = "BACKEND_UNAVAILABLE"
    INTERNAL = "INTERNAL"


class F2bError(Exception):
    def __init__(
        self,
        code: str,
        message: str,
        *,
        status: int | None = None,
        details: Any = None,
        cause: BaseException | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status
        self.details = details
        self.__cause__ = cause

    def __str__(self) -> str:
        base = f"[{self.code}] {self.message}"
        if self.status is not None:
            base += f" (HTTP {self.status})"
        return base
