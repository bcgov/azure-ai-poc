"""Auth-specific error types and helpers.

We use a dedicated exception so the API can return consistent structured
error bodies for authentication/authorization failures.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from fastapi import HTTPException


def _utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass(frozen=True)
class AuthErrorBody:
    detail: str
    code: str
    timestamp: str

    def to_dict(self) -> dict[str, str]:
        return {"detail": self.detail, "code": self.code, "timestamp": self.timestamp}


class AuthError(HTTPException):
    """HTTPException with a stable error code and timestamped payload."""

    def __init__(
        self,
        *,
        status_code: int,
        detail: str,
        code: str,
        headers: dict[str, str] | None = None,
    ) -> None:
        super().__init__(status_code=status_code, detail=detail, headers=headers)
        self.code = code
        self.timestamp = _utc_now_iso()

    def to_payload(self) -> dict[str, str]:
        return AuthErrorBody(
            detail=str(self.detail), code=self.code, timestamp=self.timestamp
        ).to_dict()


def auth_error_payload(*, detail: str, code: str) -> dict[str, str]:
    """Create a structured error payload (for middleware-controlled responses)."""

    return AuthErrorBody(detail=detail, code=code, timestamp=_utc_now_iso()).to_dict()
