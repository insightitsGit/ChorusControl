"""Sibling stack license console — honest status for env-provided keys."""

from __future__ import annotations

import os
import time
from typing import Any

import jwt

STACK_ENV_KEYS = (
    ("chorusgraph", "CHORUSGRAPH_LICENSE_KEY"),
    ("prismguard", "PRISMGUARD_LICENSE_KEY"),
    ("prismshine", "PRISMSHINE_LICENSE_KEY"),
    ("prismcortex", "PRISMCORTEX_LICENSE_KEY"),
    ("prismrag", "PRISMRAG_LICENSE_KEY"),
    ("chorusmesh", "CHORUSMESH_LICENSE_KEY"),
)


def _parse_key(raw: str | None) -> dict[str, Any]:
    if not raw or not raw.strip():
        return {"status": "not_configured"}
    token = raw.strip()
    if token.count(".") != 2:
        return {"status": "unknown_format", "hint": "expected JWT"}
    try:
        claims = jwt.decode(token, options={"verify_signature": False, "verify_exp": False})
    except Exception as exc:  # noqa: BLE001
        return {"status": "unknown_format", "error": str(exc)}
    now = time.time()
    exp = claims.get("exp")
    state = "unknown"
    if isinstance(exp, (int, float)):
        state = "valid" if exp >= now else "expired"
    return {
        "status": "configured",
        "state": state,
        "tier": claims.get("tier"),
        "exp": exp,
        "sub": claims.get("sub"),
        "iss": claims.get("iss"),
    }


def stack_license_status(environ: dict[str, str] | None = None) -> dict[str, Any]:
    env = environ if environ is not None else os.environ
    products: dict[str, Any] = {}
    for name, env_key in STACK_ENV_KEYS:
        products[name] = {"env": env_key, **_parse_key(env.get(env_key))}
    return {"products": products, "phone_home": False}
