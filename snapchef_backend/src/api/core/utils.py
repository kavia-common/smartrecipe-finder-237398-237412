from __future__ import annotations

import re
from datetime import datetime
from typing import Any

from fastapi import Header, HTTPException, status
from pydantic import BaseModel

from src.api.core.config import get_settings


SLUG_RE = re.compile(r"[^a-zA-Z0-9_\-]")


# PUBLIC_INTERFACE
def sanitize_user_id(user_id: str) -> str:
    """Sanitize a demo user id to safe characters for storage."""
    user_id = user_id.strip()
    user_id = SLUG_RE.sub("_", user_id)
    return user_id[:64] if len(user_id) > 64 else user_id


class Pagination(BaseModel):
    limit: int
    offset: int


# PUBLIC_INTERFACE
def parse_pagination(limit: int | None, offset: int | None) -> Pagination:
    """Parse and clamp pagination query params."""
    settings = get_settings()
    lim = limit if limit is not None else settings.default_page_size
    off = offset if offset is not None else 0

    if lim < 1:
        lim = settings.default_page_size
    if off < 0:
        off = 0
    if lim > settings.max_page_size:
        lim = settings.max_page_size

    return Pagination(limit=lim, offset=off)


# PUBLIC_INTERFACE
def http_error(code: str, message: str, http_status: int = status.HTTP_400_BAD_REQUEST, details: dict[str, Any] | None = None):
    """Raise a consistent HTTPException with structured error fields."""
    raise HTTPException(status_code=http_status, detail={"code": code, "message": message, "details": details})


# PUBLIC_INTERFACE
def now_utc_iso() -> str:
    """Return current UTC time as ISO string (for correlation ids / debug)."""
    return datetime.utcnow().isoformat() + "Z"


# PUBLIC_INTERFACE
def get_demo_user_header(x_demo_user: str | None = Header(default=None, alias="X-Demo-User")) -> str | None:
    """FastAPI dependency to extract demo user id header.

    Clients should send X-Demo-User: <user_id> for all user-scoped operations.
    """
    if x_demo_user is None:
        return None
    return sanitize_user_id(x_demo_user)
