"""Safe-default checks for serve / Azure (BUG-003)."""

from __future__ import annotations

WEAK_ADMIN_TOKENS = frozenset(
    {
        "",
        "dev-admin-token",
        "changeme",
        "admin",
        "password",
        "secret",
    }
)


def admin_token_is_weak(token: str | None) -> bool:
    t = (token or "").strip()
    if not t:
        return True
    if t.lower() in WEAK_ADMIN_TOKENS:
        return True
    if len(t) < 16:
        return True
    return False
