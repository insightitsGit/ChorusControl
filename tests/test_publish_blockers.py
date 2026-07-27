"""P0 publish blockers HO-ChorusControl-001 — BUG-001…004 regressions."""

from __future__ import annotations

import time
from pathlib import Path

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from httpx import ASGITransport, AsyncClient

from choruscontrol.config import get_settings
from choruscontrol.license.keys import packaged_side1_public_pem, resolve_verify_public_pem
from choruscontrol.license.verifier import LicenseClaims, LicenseVerifier


FIXTURE_PRIV = Path(__file__).parent / "fixtures" / "side1_dev_private.pem"


def _side1_private() -> Ed25519PrivateKey:
    return serialization.load_pem_private_key(FIXTURE_PRIV.read_bytes(), password=None)


def test_bug001_packaged_trust_anchor_verifies_side1_jwt():
    pem, source = resolve_verify_public_pem()
    assert source == "packaged"
    assert "BEGIN PUBLIC KEY" in pem
    assert packaged_side1_public_pem() == pem or packaged_side1_public_pem().strip() in pem

    priv = _side1_private()
    v = LicenseVerifier(public_pem=pem)
    now = int(time.time())
    token = v.issue_dev_token(
        LicenseClaims(sub="acme", iat=now, exp=now + 3600, license_id="lic_side1"),
        private=priv,
    )
    assert v.verify(token).state == "valid"

    # Foreign key must fail
    other = Ed25519PrivateKey.generate()
    bad = v.issue_dev_token(
        LicenseClaims(sub="x", iat=now, exp=now + 3600, license_id="lic_bad"),
        private=other,
    )
    assert v.verify(bad).state == "invalid"


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
    h = {"Authorization": "Bearer dev-admin-token"}
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
