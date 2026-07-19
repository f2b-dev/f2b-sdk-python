"""错误码与异常（对齐 f2b-spec 语义）。"""

from __future__ import annotations

from typing import Any


class ErrorCode:
    INTERNAL = "INTERNAL"
    BACKEND_UNAVAILABLE = "BACKEND_UNAVAILABLE"
    NOT_FOUND = "NOT_FOUND"
    UNAUTHORIZED = "UNAUTHORIZED"
    VALIDATION = "VALIDATION"
    CONFLICT = "CONFLICT"


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
