from __future__ import annotations

import json
import time
from dataclasses import dataclass
from typing import Any, Literal

import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
from pydantic import BaseModel, Field


# Dev/public keypair for offline tests (NOT for production issuance — Side 1 holds prod private).
_DEV_PRIVATE = ed25519.Ed25519PrivateKey.generate()
DEV_PUBLIC_PEM = _DEV_PRIVATE.public_key().public_bytes(
    encoding=serialization.Encoding.PEM,
    format=serialization.PublicFormat.SubjectPublicKeyInfo,
).decode()


def set_dev_private_for_tests(key: ed25519.Ed25519PrivateKey) -> None:
    global _DEV_PRIVATE, DEV_PUBLIC_PEM
    _DEV_PRIVATE = key
    DEV_PUBLIC_PEM = key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()


class LicenseClaims(BaseModel):
    iss: str = "insightits.com"
    sub: str
    iat: int
    exp: int
    tier: Literal["starter", "enterprise", "sovereign"] = "enterprise"
    max_nodes: int = 16
    max_tenants: int = 50
    features: set[str] = Field(
        default_factory=lambda: {
            "trace.replay",
            "guard.shadow",
            "guard.policy",
            "audit.export",
            "cascade.auto",
            "fleet.topology",
            "caps.aggregate",
            "assistant.ops",
        }
    )
    license_id: str


LicenseState = Literal["valid", "grace", "invalid", "missing"]


@dataclass
class LicenseStatus:
    state: LicenseState
    claims: LicenseClaims | None
    message: str
    seconds_to_exp: float | None = None
    grace_remaining_seconds: float | None = None


class LicenseVerifier:
    def __init__(
        self,
        public_pem: str | None = None,
        grace_days: int = 14,
        clock_skew_seconds: int = 86400,
    ) -> None:
        self.public_pem = public_pem or DEV_PUBLIC_PEM
        self.grace_days = grace_days
        self.clock_skew_seconds = clock_skew_seconds
        self._public = serialization.load_pem_public_key(self.public_pem.encode())

    def issue_dev_token(self, claims: LicenseClaims, private: ed25519.Ed25519PrivateKey | None = None) -> str:
        key = private or _DEV_PRIVATE
        payload = claims.model_dump()
        payload["features"] = sorted(payload["features"])
        return jwt.encode(payload, key, algorithm="EdDSA")

    def verify(self, token: str | None, now: float | None = None) -> LicenseStatus:
        if not token:
            return LicenseStatus("missing", None, "CHORUSCONTROL_LICENSE_KEY not set")
        now = now if now is not None else time.time()
        try:
            raw = jwt.decode(
                token,
                self._public,
                algorithms=["EdDSA"],
                options={"verify_exp": False},
            )
            claims = LicenseClaims.model_validate(raw)
        except Exception as exc:  # noqa: BLE001
            return LicenseStatus("invalid", None, f"license verify failed: {exc}")

        skew = self.clock_skew_seconds
        if claims.iat - skew > now:
            return LicenseStatus("invalid", claims, "license iat in the future (beyond skew)")

        seconds_to_exp = claims.exp - now
        if seconds_to_exp >= -skew:
            # still within exp (+skew)
            if seconds_to_exp < 0:
                # inside skew after exp — treat valid
                return LicenseStatus("valid", claims, "valid (within clock skew)", seconds_to_exp)
            return LicenseStatus("valid", claims, "valid", seconds_to_exp)

        grace_seconds = self.grace_days * 86400
        overdue = -seconds_to_exp
        if overdue <= grace_seconds:
            return LicenseStatus(
                "grace",
                claims,
                "license expired — grace read-only mode",
                seconds_to_exp,
                grace_seconds - overdue,
            )
        return LicenseStatus("invalid", claims, "license expired (past grace)", seconds_to_exp)

    def has_feature(self, status: LicenseStatus, feature: str) -> bool:
        if status.state not in ("valid", "grace") or not status.claims:
            return False
        if status.state == "grace":
            # grace: allow read features only
            return feature.startswith("caps.") or feature in {"fleet.topology"}
        return feature in status.claims.features
