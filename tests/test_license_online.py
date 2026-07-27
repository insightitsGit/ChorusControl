"""Optional Side 1 online license validate (14-day interval)."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, patch

import pytest

from choruscontrol.config import Settings
from choruscontrol.license.online import apply_online_to_status, due_for_check, run_online_check
from choruscontrol.license.verifier import LicenseClaims, LicenseStatus, LicenseVerifier


def test_due_for_check_respects_interval_and_airgap(tmp_path):
    settings = Settings(
        CHORUSCONTROL_SQLITE_PATH=str(tmp_path / "cc.db"),
        CHORUSCONTROL_LICENSE_ONLINE_CHECK=True,
        CHORUSCONTROL_LICENSE_ONLINE_INTERVAL_DAYS=14,
        CHORUSCONTROL_DEMO_MODE=False,
    )
    assert due_for_check(settings, None) is True
    assert due_for_check(settings, {"checked_at_unix": time.time()}) is False
    assert (
        due_for_check(settings, {"checked_at_unix": time.time() - 15 * 86400}) is True
    )

    settings_off = Settings(
        CHORUSCONTROL_SQLITE_PATH=str(tmp_path / "cc2.db"),
        CHORUSCONTROL_LICENSE_ONLINE_CHECK=False,
    )
    assert due_for_check(settings_off, None) is False


def test_apply_online_revoked_fail_closed():
    offline = LicenseStatus("valid", LicenseClaims(sub="x", iat=1, exp=9_999_999_999, license_id="lic"), "valid")
    revoked = apply_online_to_status(offline, {"status": "revoked", "registryStatus": "cancelled"})
    assert revoked.state == "invalid"
    assert "revoked" in revoked.message.lower()

    ok = apply_online_to_status(offline, {"status": "active", "valid": True})
    assert ok.state == "valid"


@pytest.mark.asyncio
async def test_run_online_check_skipped_in_demo(tmp_path):
    cfg = Settings(
        CHORUSCONTROL_DEMO_MODE=True,
        CHORUSCONTROL_SQLITE_PATH=str(tmp_path / "d.db"),
        CHORUSCONTROL_LICENSE_ONLINE_CHECK=True,
    )

    class S:
        settings = cfg
        online_license = None

    out = await run_online_check(S(), force=True)
    assert out.get("skipped") is True
    assert out.get("reason") == "demo_mode"


@pytest.mark.asyncio
async def test_run_online_check_calls_side1(tmp_path):
    cfg = Settings(
        CHORUSCONTROL_DEMO_MODE=False,
        CHORUSCONTROL_SQLITE_PATH=str(tmp_path / "e.db"),
        CHORUSCONTROL_LICENSE_KEY="fake.jwt.here",
        CHORUSCONTROL_LICENSE_ONLINE_CHECK=True,
        CHORUSCONTROL_SIDE1_API_BASE_URL="http://127.0.0.1:5000",
        CHORUSCONTROL_LICENSE_ONLINE_CHECK_IN_DEMO=False,
    )

    class S:
        settings = cfg
        online_license = None

    fake = {
        "valid": True,
        "status": "active",
        "registryStatus": "active",
        "recommendedCheckIntervalDays": 14,
        "offlineOk": True,
        "phoneHomeRequired": False,
    }
    with patch("choruscontrol.license.online.validate_online", new=AsyncMock(return_value=fake)):
        out = await run_online_check(S(), force=True)
    assert out.get("ok") is True
    assert out["result"]["status"] == "active"


@pytest.mark.asyncio
async def test_admin_online_check_route(tmp_path, monkeypatch):
    monkeypatch.setenv("CHORUSCONTROL_DEMO_MODE", "1")
    monkeypatch.setenv("CHORUSCONTROL_SQLITE_PATH", str(tmp_path / "cc.db"))
    monkeypatch.setenv("CHORUSCONTROL_AUDIT_LOG_PATH", str(tmp_path / "a.jsonl"))
    monkeypatch.setenv("CHORUSCONTROL_ADMIN_TOKEN", "dev-admin-token")
    from choruscontrol.config import get_settings

    get_settings.cache_clear()
    from httpx import ASGITransport, AsyncClient

    from choruscontrol.server import create_app

    app = create_app()
    h = {"Authorization": "Bearer dev-admin-token"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        async with app.router.lifespan_context(app):
            lic = await c.get("/api/v1/admin/license", headers=h)
            assert lic.status_code == 200
            assert "online_check" in lic.json()
            # demo skips real call
            r = await c.post("/api/v1/admin/license/online-check", headers=h, json={})
            assert r.status_code == 200
            assert r.json()["check"].get("skipped") is True
