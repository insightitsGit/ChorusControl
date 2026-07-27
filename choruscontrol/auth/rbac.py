from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from fastapi import Depends, Header, HTTPException

Role = Literal["viewer", "operator", "security", "admin"]

ROLE_RANK = {"viewer": 1, "operator": 2, "security": 3, "admin": 4}


@dataclass
class Principal:
    user: str
    role: Role
    auth: Literal["token", "oidc"] = "token"


def parse_bearer(authorization: str | None, admin_token: str) -> Principal:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="missing bearer token")
    token = authorization.split(" ", 1)[1].strip()

    if token == admin_token:
        return Principal("admin", "admin", auth="token")
    if "|" in token:
        parts = token.split("|")
        if len(parts) == 3 and parts[0] == admin_token:
            role = parts[2] if parts[2] in ROLE_RANK else "viewer"
            return Principal(parts[1], role, auth="token")  # type: ignore[arg-type]
    if ":" in token:
        base, role = token.rsplit(":", 1)
        if base == admin_token and role in ROLE_RANK:
            return Principal("admin", role, auth="token")  # type: ignore[arg-type]

    if token.count(".") == 2:
        from choruscontrol.auth.oidc import get_oidc

        oidc = get_oidc()
        if oidc is None:
            raise HTTPException(status_code=401, detail="OIDC not enabled")
        return oidc.validate(token)

    raise HTTPException(status_code=401, detail="invalid token")


def require_role(min_role: Role):
    async def _dep(
        authorization: str | None = Header(default=None),
        x_chorus_role: str | None = Header(default=None),
    ) -> Principal:
        from choruscontrol.config import get_settings

        settings = get_settings()
        principal = parse_bearer(authorization, settings.admin_token)
        if x_chorus_role and x_chorus_role in ROLE_RANK:
            if ROLE_RANK[x_chorus_role] <= ROLE_RANK[principal.role]:  # type: ignore[index]
                principal.role = x_chorus_role  # type: ignore[assignment]
        if ROLE_RANK[principal.role] < ROLE_RANK[min_role]:
            raise HTTPException(status_code=403, detail=f"requires role {min_role}")
        return principal

    return Depends(_dep)
