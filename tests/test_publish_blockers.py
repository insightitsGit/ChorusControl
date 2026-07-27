"""P0/P1 publish blockers — BUG-001…004, BUG-007 regressions."""

from __future__ import annotations

import time
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from httpx import ASGITransport, AsyncClient

from choruscontrol.config import get_settings
from choruscontrol.license.keys import (
    packaged_side1_public_pem,
    public_pem_from_raw_hex,
    resolve_verify_public_pem,
)
from choruscontrol.license.verifier import LicenseClaims, LicenseVerifier

# Prod Key Vault ceremony public (2026-07-27) — BUG-007
CEREMONY_PUBLIC_HEX = "5d78a9a4e654312c8ae5dd10792d46b53974868f8c8b5346cb3c5abef320e37c"

FIXTURE_PRIV = Path(__file__).parent / "fixtures" / "side1_dev_private.pem"


def _dev_private() -> Ed25519PrivateKey:
    """Dev-only signing key (matches historical placeholder — not ceremony)."""
    return serialization.load_pem_private_key(FIXTURE_PRIV.read_bytes(), password=None)


def test_bug007_packaged_pubkey_is_ceremony():
    packaged_side1_public_pem.cache_clear()
    hex_path = Path(__file__).resolve().parents[1] / "choruscontrol" / "license" / "side1_public.hex"
    assert hex_path.read_text(encoding="utf-8").strip() == CEREMONY_PUBLIC_HEX
    expected_pem = public_pem_from_raw_hex(CEREMONY_PUBLIC_HEX).strip()
    assert packaged_side1_public_pem().strip() == expected_pem
    pem, source = resolve_verify_public_pem()
    assert source == "packaged"
    assert pem.strip() == expected_pem


def test_bug007_jwt_verifies_with_packaged_key_matching_keypair():
    """Crypto path: JWT signed for the packaged public verifies without env override.

    Uses an ephemeral keypair whose public is injected as the packaged PEM via
    LicenseVerifier(public_pem=...) equal to packaged-resolution shape — proves
    verify(public) accepts matching signatures. Ceremony private is Side 1 only;
    hex pin is asserted in test_bug007_packaged_pubkey_is_ceremony.
    """
    packaged_side1_public_pem.cache_clear()
    pem, source = resolve_verify_public_pem()
    assert source == "packaged"

    # Sign with a key that matches the *packaged* public is impossible without
    # ceremony private. Prove verifier accepts when public PEM matches signer,
    # using the same resolution helper customers use (hex → PEM).
    priv = Ed25519PrivateKey.generate()
    pub_raw = priv.public_key().public_bytes(
        encoding=serialization.Encoding.Raw,
        format=serialization.PublicFormat.Raw,
    )
    match_pem = public_pem_from_raw_hex(pub_raw.hex())
    v = LicenseVerifier(public_pem=match_pem)
    now = int(time.time())
    token = v.issue_dev_token(
        LicenseClaims(sub="acme", iat=now, exp=now + 3600, license_id="lic_pair"),
        private=priv,
    )
    assert v.verify(token).state == "valid"

    # Packaged ceremony public must reject foreign signatures
    v_pkg = LicenseVerifier(public_pem=pem)
    assert v_pkg.verify(token).state == "invalid"


def test_bug001_packaged_trust_anchor_rejects_foreign_and_accepts_dev_fixture_on_match():
    packaged_side1_public_pem.cache_clear()
    pem, source = resolve_verify_public_pem()
    assert source == "packaged"
    assert "BEGIN PUBLIC KEY" in pem

    # Dev fixture is the old placeholder keypair — must NOT verify against ceremony pubkey
    now = int(time.time())
    v = LicenseVerifier(public_pem=pem)
    bad = v.issue_dev_token(
        LicenseClaims(sub="acme", iat=now, exp=now + 3600, license_id="lic_dev"),
        private=_dev_private(),
    )
    assert v.verify(bad).state == "invalid"

    other = Ed25519PrivateKey.generate()
    foreign = v.issue_dev_token(
        LicenseClaims(sub="x", iat=now, exp=now + 3600, license_id="lic_bad"),
        private=other,
    )
    assert v.verify(foreign).state == "invalid"

    # Env hex override still works for ops that pin explicitly (legacy Aurora path)
    match_pem = public_pem_from_raw_hex(
        _dev_private()
        .public_key()
        .public_bytes(encoding=serialization.Encoding.Raw, format=serialization.PublicFormat.Raw)
        .hex()
    )
    v_env = LicenseVerifier(public_pem=match_pem)
    ok = v_env.issue_dev_token(
        LicenseClaims(sub="acme", iat=now, exp=now + 3600, license_id="lic_env"),
        private=_dev_private(),
    )
    assert v_env.verify(ok).state == "valid"


@pytest.mark.asyncio
async def test_bug002_no_auto_issue_outside_demo(tmp_path, monkeypatch):
    monkeypatch.setenv("CHORUSCONTROL_DEMO_MODE", "0")
    monkeypatch.delenv("CHORUSCONTROL_LICENSE_KEY", raising=False)
    monkeypatch.setenv("CHORUSCONTROL_SQLITE_PATH", str(tmp_path / "nolic.db"))
    monkeypatch.setenv("CHORUSCONTROL_AUDIT_LOG_PATH", str(tmp_path / "a.jsonl"))
    monkeypatch.setenv("CHORUSCONTROL_ADMIN_TOKEN", "strong-admin-token-32chars!!")
    get_settings.cache_clear()

    from choruscontrol.app_state import build_state
    from choruscontrol.config import Settings

    settings = Settings()
    state = await build_state(settings)
    try:
        assert state.license_status.state == "missing"
        assert "assistant.ops" not in (
            state.license_status.claims.features if state.license_status.claims else set()
        )
    finally:
        if state.metrics_sampler:
            await state.metrics_sampler.stop()
        await state.audit.stop()


def test_bug003_refuse_weak_admin_token():
    from choruscontrol.config_security import admin_token_is_weak

    assert admin_token_is_weak("dev-admin-token") is True
    assert admin_token_is_weak("") is True
    assert admin_token_is_weak("short") is True
    assert admin_token_is_weak("healthcare-demo-token") is False
    assert admin_token_is_weak("strong-admin-token-32chars!!") is False


@pytest.mark.asyncio
async def test_bug004_fleet_ack_ledger_require_session(tmp_path, monkeypatch):
    monkeypatch.setenv("CHORUSCONTROL_DEMO_MODE", "1")
    monkeypatch.setenv("CHORUSCONTROL_SQLITE_PATH", str(tmp_path / "fleet.db"))
    monkeypatch.setenv("CHORUSCONTROL_AUDIT_LOG_PATH", str(tmp_path / "a.jsonl"))
    monkeypatch.setenv("CHORUSCONTROL_ADMIN_TOKEN", "dev-admin-token")
    get_settings.cache_clear()

    from choruscontrol.server import create_app

    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        async with app.router.lifespan_context(app):
            s = app.state.cc
            token = await s.fleet.create_join_token(max_uses=2)
            join = await s.fleet.join(
                join_token=token,
                node_id="n-auth",
                tenant_id="default",
                role="worker",
                network_zone="in_vpc",
                products={},
                caps_digest=None,
                memory_endpoint=None,
                max_nodes=16,
            )
            secret = join["session_secret"]

            denied = await c.post(
                "/api/v1/fleet/ack",
                json={"node_id": "n-auth", "cascade_id": "c1", "status": "ok"},
            )
            assert denied.status_code == 401

            ok = await c.post(
                "/api/v1/fleet/ack",
                headers={"X-Node-Session": secret},
                json={"node_id": "n-auth", "cascade_id": "c1", "status": "ok"},
            )
            assert ok.status_code == 200

            denied_l = await c.post(
                "/api/v1/fleet/ledger-batch",
                json={
                    "node_id": "n-auth",
                    "tenant_id": "default",
                    "entries": [{"stage": "guard", "decision": "allow"}],
                    "truncated": False,
                },
            )
            assert denied_l.status_code == 401

            ok_l = await c.post(
                "/api/v1/fleet/ledger-batch",
                headers={"X-Node-Session": secret},
                json={
                    "node_id": "n-auth",
                    "tenant_id": "default",
                    "entries": [{"stage": "guard", "decision": "allow"}],
                    "truncated": False,
                },
            )
            assert ok_l.status_code == 200

            # WS without token rejected (close) — httpx doesn't do WS easily; use starlette test
            from starlette.testclient import TestClient

            with TestClient(app) as tc:
                with pytest.raises(Exception):
                    with tc.websocket_connect("/api/v1/fleet/live") as ws:
                        ws.receive_json()
                with tc.websocket_connect("/api/v1/fleet/live?token=dev-admin-token") as ws:
                    msg = ws.receive_json()
                    assert msg["type"] == "snapshot"
