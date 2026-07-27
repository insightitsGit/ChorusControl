"""License trust anchor resolution (BUG-001).

Load order (non-demo):
1. CHORUSCONTROL_LICENSE_PUBLIC_PEM (full PEM text)
2. CHORUSCONTROL_LICENSE_PUBLIC_KEY_HEX (32-byte raw Ed25519 public hex from Side 1 ceremony)
3. Packaged ``side1_public.pem`` (pinned trust anchor shipped with Side 2)

Demo / tests may still use ephemeral DEV keys via LicenseVerifier(public_pem=DEV...).
Production Azure must set Side 1 ceremony public hex/PEM so issued JWTs verify.
The packaged PEM is a stable Insight ITS trust-anchor placeholder until ceremony
replaces it in release artifacts / env.
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey

log = logging.getLogger("choruscontrol.license.keys")

_PACKAGE_DIR = Path(__file__).resolve().parent
_PACKAGED_PEM = _PACKAGE_DIR / "side1_public.pem"
_PACKAGED_HEX = _PACKAGE_DIR / "side1_public.hex"


def public_pem_from_raw_hex(hex_key: str) -> str:
    raw = bytes.fromhex(hex_key.strip())
    if len(raw) != 32:
        raise ValueError(f"Ed25519 public key must be 32 bytes, got {len(raw)}")
    pub = Ed25519PublicKey.from_public_bytes(raw)
    return pub.public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode()


@lru_cache
def packaged_side1_public_pem() -> str:
    if _PACKAGED_PEM.is_file():
        return _PACKAGED_PEM.read_text(encoding="utf-8").strip() + "\n"
    if _PACKAGED_HEX.is_file():
        return public_pem_from_raw_hex(_PACKAGED_HEX.read_text(encoding="utf-8"))
    raise RuntimeError("packaged Side 1 public key missing (side1_public.pem)")


def resolve_verify_public_pem(
    *,
    public_pem: str | None = None,
    public_key_hex: str | None = None,
    demo_mode: bool = False,
    allow_dev: bool = False,
) -> tuple[str, str]:
    """Return (pem, source). source in env_pem|env_hex|packaged|dev."""
    if public_pem and public_pem.strip():
        return public_pem.strip() + "\n", "env_pem"
    if public_key_hex and public_key_hex.strip():
        return public_pem_from_raw_hex(public_key_hex), "env_hex"
    try:
        return packaged_side1_public_pem(), "packaged"
    except RuntimeError:
        if demo_mode or allow_dev:
            from choruscontrol.license.verifier import DEV_PUBLIC_PEM

            log.warning("falling back to DEV public key (demo/allow_dev only)")
            return DEV_PUBLIC_PEM, "dev"
        raise
