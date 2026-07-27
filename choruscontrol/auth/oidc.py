from __future__ import annotations

from typing import Any

import httpx
import jwt
from fastapi import HTTPException
from jwt import PyJWKClient

from choruscontrol.auth.rbac import Principal, Role


class OIDCValidator:
    """Validate bearer JWTs from an IdP (OIDC). Maps chorus_roles claim → RBAC."""

    def __init__(
        self,
        *,
        issuer: str,
        audience: str,
        jwks_url: str,
        role_claim: str = "chorus_roles",
    ) -> None:
        self.issuer = issuer
        self.audience = audience
        self.jwks_url = jwks_url
        self.role_claim = role_claim
        self._jwks = PyJWKClient(jwks_url, cache_keys=True)

    def validate(self, token: str) -> Principal:
        try:
            key = self._jwks.get_signing_key_from_jwt(token)
            claims = jwt.decode(
                token,
                key.key,
                algorithms=["RS256", "ES256", "EdDSA"],
                audience=self.audience,
                issuer=self.issuer,
                options={"require": ["exp", "iat", "sub"]},
            )
        except Exception as exc:  # noqa: BLE001
            raise HTTPException(status_code=401, detail=f"oidc invalid: {exc}") from exc
        sub = str(claims.get("sub") or claims.get("email") or "oidc-user")
        role = self._map_role(claims)
        return Principal(sub, role, auth="oidc")

    def _map_role(self, claims: dict[str, Any]) -> Role:
        raw = claims.get(self.role_claim) or claims.get("roles") or []
        if isinstance(raw, str):
            raw = [raw]
        roles = {str(r).lower() for r in raw}
        for candidate in ("admin", "security", "operator", "viewer"):
            if candidate in roles:
                return candidate  # type: ignore[return-value]
        realm = claims.get("realm_access") or {}
        roles |= {str(r).lower() for r in (realm.get("roles") or [])}
        for candidate in ("admin", "security", "operator", "viewer"):
            if candidate in roles or f"chorus_{candidate}" in roles:
                return candidate  # type: ignore[return-value]
        return "viewer"


_oidc: OIDCValidator | None = None


def get_oidc() -> OIDCValidator | None:
    global _oidc
    from choruscontrol.config import get_settings

    s = get_settings()
    if not s.oidc_enabled:
        return None
    if _oidc is None:
        if not (s.oidc_issuer and s.oidc_audience and s.oidc_jwks_url):
            raise RuntimeError("OIDC enabled but issuer/audience/jwks_url incomplete")
        _oidc = OIDCValidator(
            issuer=s.oidc_issuer,
            audience=s.oidc_audience,
            jwks_url=s.oidc_jwks_url,
            role_claim=s.oidc_role_claim,
        )
    return _oidc


def reset_oidc_cache() -> None:
    global _oidc
    _oidc = None


async def discover_oidc(issuer: str) -> dict[str, Any]:
    url = issuer.rstrip("/") + "/.well-known/openid-configuration"
    async with httpx.AsyncClient(timeout=10.0) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.json()
