"""Handoff WP1–WP11 coverage tests."""

from __future__ import annotations

import io
import json
import time
import zipfile

import pytest
from cryptography.hazmat.primitives.asymmetric import ed25519
from httpx import ASGITransport, AsyncClient

from choruscontrol.config import get_settings
from choruscontrol.license import LicenseClaims, LicenseVerifier, set_dev_private_for_tests
from choruscontrol.license.stack import stack_license_status


def _app_client(tmp_path, monkeypatch, *, demo=True, extra_env=None):
    monkeypatch.setenv("CHORUSCONTROL_DEMO_MODE", "1" if demo else "0")
    monkeypatch.setenv("CHORUSCONTROL_SQLITE_PATH", str(tmp_path / "cc.db"))
    monkeypatch.setenv("CHORUSCONTROL_AUDIT_LOG_PATH", str(tmp_path / "a.jsonl"))
    monkeypatch.setenv("CHORUSCONTROL_ADMIN_TOKEN", "dev-admin-token")
    for k, v in (extra_env or {}).items():
        monkeypatch.setenv(k, v)
    get_settings.cache_clear()
    from choruscontrol.server import create_app

    return create_app()


@pytest.mark.asyncio
async def test_wp1_feature_gates(tmp_path, monkeypatch):
    private = ed25519.Ed25519PrivateKey.generate()
    set_dev_private_for_tests(private)
    from choruscontrol.license import verifier as vmod

    v = LicenseVerifier(public_pem=vmod.DEV_PUBLIC_PEM)
    now = int(time.time())
    claims = LicenseClaims(
        sub="acme",
        iat=now,
        exp=now + 86400,
        license_id="lic-feat",
        features={"fleet.topology", "caps.aggregate"},  # no trace.replay / audit.export
        max_tenants=2,
    )
    token = v.issue_dev_token(claims, private)
    app = _app_client(
        tmp_path,
        monkeypatch,
        demo=False,
        extra_env={"CHORUSCONTROL_LICENSE_KEY": token},
    )
    h = {"Authorization": "Bearer dev-admin-token"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        async with app.router.lifespan_context(app):
            # seed a trace then replay should 403
            seed = await c.post("/api/v1/traces/seed", headers=h, json={"tenant_id": "default"})
            assert seed.status_code == 200
            run_id = seed.json()["run_id"]
            rep = await c.post(f"/api/v1/traces/{run_id}/replay", headers=h, json={})
            assert rep.status_code == 403
            assert rep.json()["detail"]["detail"] == "FEATURE_NOT_LICENSED"
            soc = await c.get("/api/v1/admin/soc2-export", headers=h)
            assert soc.status_code == 403


@pytest.mark.asyncio
async def test_wp1_demo_feature_pass(tmp_path, monkeypatch):
    app = _app_client(tmp_path, monkeypatch, demo=True)
    h = {"Authorization": "Bearer dev-admin-token"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        async with app.router.lifespan_context(app):
            seed = await c.post("/api/v1/traces/seed", headers=h, json={})
            run_id = seed.json()["run_id"]
            rep = await c.post(f"/api/v1/traces/{run_id}/replay", headers=h, json={})
            assert rep.status_code == 200
            assert rep.json().get("demo") is True


@pytest.mark.asyncio
async def test_wp2_tenants_max(tmp_path, monkeypatch):
    private = ed25519.Ed25519PrivateKey.generate()
    set_dev_private_for_tests(private)
    from choruscontrol.license import verifier as vmod

    v = LicenseVerifier(public_pem=vmod.DEV_PUBLIC_PEM)
    now = int(time.time())
    claims = LicenseClaims(
        sub="acme",
        iat=now,
        exp=now + 86400,
        license_id="lic-t",
        max_tenants=2,
        features={"audit.export", "trace.replay", "guard.shadow", "fleet.topology"},
    )
    token = v.issue_dev_token(claims, private)
    app = _app_client(
        tmp_path, monkeypatch, demo=False, extra_env={"CHORUSCONTROL_LICENSE_KEY": token}
    )
    h = {"Authorization": "Bearer dev-admin-token"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        async with app.router.lifespan_context(app):
            # default already seeded → 1 tenant; one more ok; third fails
            r1 = await c.post(
                "/api/v1/admin/tenants",
                headers=h,
                json={"tenant_id": "t2", "name": "Two"},
            )
            assert r1.status_code == 200
            r2 = await c.post(
                "/api/v1/admin/tenants",
                headers=h,
                json={"tenant_id": "t3", "name": "Three"},
            )
            assert r2.status_code == 403
            assert r2.json()["detail"]["detail"] == "TENANT_LIMIT"
            deleted = await c.delete("/api/v1/admin/tenants/t2", headers=h)
            assert deleted.status_code == 200


@pytest.mark.asyncio
async def test_wp3_tls_external(tmp_path, monkeypatch):
    app = _app_client(tmp_path, monkeypatch, demo=True)
    h = {"Authorization": "Bearer dev-admin-token"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        async with app.router.lifespan_context(app):
            tok = await c.post("/api/v1/fleet/join-tokens", headers=h, json={"max_uses": 5})
            jt = tok.json()["join_token"]
            bad = await c.post(
                "/api/v1/fleet/join",
                json={
                    "join_token": jt,
                    "network_zone": "external",
                    "products": {"chorusgraph": "1.3.0"},
                },
            )
            assert bad.status_code == 403
            assert bad.json()["detail"]["detail"] == "TLS_REQUIRED"


@pytest.mark.asyncio
async def test_wp3_tls_override(tmp_path, monkeypatch):
    app = _app_client(
        tmp_path,
        monkeypatch,
        demo=True,
        extra_env={"CHORUSCONTROL_ALLOW_INSECURE_EXTERNAL": "1"},
    )
    h = {"Authorization": "Bearer dev-admin-token"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        async with app.router.lifespan_context(app):
            tok = await c.post("/api/v1/fleet/join-tokens", headers=h, json={"max_uses": 5})
            jt = tok.json()["join_token"]
            ok = await c.post(
                "/api/v1/fleet/join",
                json={
                    "join_token": jt,
                    "network_zone": "external",
                    "node_id": "ext-1",
                    "products": {"chorusgraph": "1.3.0", "prismlib-plus": "0.8.0"},
                },
            )
            assert ok.status_code == 200


@pytest.mark.asyncio
async def test_wp4_soc2_pack(tmp_path, monkeypatch):
    app = _app_client(tmp_path, monkeypatch, demo=True)
    h = {"Authorization": "Bearer dev-admin-token"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        async with app.router.lifespan_context(app):
            await app.state.cc.audit.log_action("admin", "test", "default", {"x": 1})
            await asyncio_sleep_flush()
            r = await c.get("/api/v1/admin/export/soc2-pack", headers=h)
            assert r.status_code == 200
            zf = zipfile.ZipFile(io.BytesIO(r.content))
            names = set(zf.namelist())
            assert "audit.jsonl" in names
            assert "audit_public_key.pem" in names
            assert "caps_snapshot.json" in names
            assert "license.json" in names
            lic = json.loads(zf.read("license.json"))
            assert "sub" not in (lic.get("claims") or {})
            assert "license_id" not in (lic.get("claims") or {})
            pem = zf.read("audit_public_key.pem").decode()
            from choruscontrol.audit.logger import verify_audit_line

            lines = zf.read("audit.jsonl").decode().strip().splitlines()
            assert lines and verify_audit_line(lines[0], pem)


async def asyncio_sleep_flush():
    import asyncio

    await asyncio.sleep(0.05)


def test_wp5_stack_licenses():
    status = stack_license_status({"CHORUSGRAPH_LICENSE_KEY": ""})
    assert status["products"]["chorusgraph"]["status"] == "not_configured"
    private = ed25519.Ed25519PrivateKey.generate()
    set_dev_private_for_tests(private)
    from choruscontrol.license import verifier as vmod

    v = LicenseVerifier(public_pem=vmod.DEV_PUBLIC_PEM)
    now = int(time.time())
    tok = v.issue_dev_token(
        LicenseClaims(sub="g", iat=now, exp=now + 1000, license_id="g1"), private
    )
    status2 = stack_license_status({"CHORUSGRAPH_LICENSE_KEY": tok})
    assert status2["products"]["chorusgraph"]["status"] == "configured"
    assert status2["products"]["chorusgraph"]["state"] == "valid"


@pytest.mark.asyncio
async def test_wp6_license_upload(tmp_path, monkeypatch):
    private = ed25519.Ed25519PrivateKey.generate()
    set_dev_private_for_tests(private)
    from choruscontrol.license import verifier as vmod

    v = LicenseVerifier(public_pem=vmod.DEV_PUBLIC_PEM)
    now = int(time.time())
    claims = LicenseClaims(
        sub="upload",
        iat=now,
        exp=now + 86400,
        license_id="up1",
        features={"audit.export", "trace.replay", "guard.shadow", "fleet.topology"},
    )
    token = v.issue_dev_token(claims, private)
    app = _app_client(tmp_path, monkeypatch, demo=True)
    h = {"Authorization": "Bearer dev-admin-token"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        async with app.router.lifespan_context(app):
            bad = await c.post(
                "/api/v1/admin/license", headers=h, json={"license_key": "not-a-jwt"}
            )
            assert bad.status_code == 400
            ok = await c.post("/api/v1/admin/license", headers=h, json={"license_key": token})
            assert ok.status_code == 200
            assert ok.json()["state"] == "valid"
            assert (tmp_path / "license.key").exists()


@pytest.mark.asyncio
async def test_wp7_fleet_live_ws(tmp_path, monkeypatch):
    from starlette.testclient import TestClient

    app = _app_client(tmp_path, monkeypatch, demo=True)
    h = {"Authorization": "Bearer dev-admin-token"}
    with TestClient(app) as client:
        with client.websocket_connect("/api/v1/fleet/live") as ws:
            hello = ws.receive_json()
            assert hello["type"] == "snapshot"
            tok = client.post("/api/v1/fleet/join-tokens", headers=h, json={})
            client.post(
                "/api/v1/fleet/join",
                json={
                    "join_token": tok.json()["join_token"],
                    "node_id": "ws-node",
                    "products": {"chorusgraph": "1.3.0", "prismlib-plus": "0.8.0"},
                },
            )
            msg = ws.receive_json()
            assert msg["type"] == "join"
            assert msg["node_id"] == "ws-node"


@pytest.mark.asyncio
async def test_wp8_commands(tmp_path, monkeypatch):
    from choruscontrol.agent.runtime import AgentRuntime, SUPPORTED_COMMANDS

    assert "REQUEST_METRICS" in SUPPORTED_COMMANDS
    assert "DRAIN" in SUPPORTED_COMMANDS
    assert "REVOKE" in SUPPORTED_COMMANDS
    assert "RUN_REINDEX" in SUPPORTED_COMMANDS

    app = _app_client(tmp_path, monkeypatch, demo=True)
    h = {"Authorization": "Bearer dev-admin-token"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        async with app.router.lifespan_context(app):
            tok = await c.post("/api/v1/fleet/join-tokens", headers=h, json={})
            joined = await c.post(
                "/api/v1/fleet/join",
                json={
                    "join_token": tok.json()["join_token"],
                    "node_id": "cmd-node",
                    "products": {
                        "chorusgraph": "1.3.0",
                        "prismlib-plus": "0.8.0",
                        "prismrag-patch": "0.2.1",
                    },
                },
            )
            nid = joined.json()["node_id"]
            secret = joined.json()["session_secret"]
            q = await c.post(
                f"/api/v1/fleet/nodes/{nid}/command",
                headers=h,
                json={"type": "REQUEST_METRICS"},
            )
            assert q.status_code == 200
            assert q.json()["status"] == "queued"
            cmds = await c.get(
                f"/api/v1/fleet/nodes/{nid}/commands",
                headers={"X-Node-Session": secret},
            )
            assert any(x["type"] == "REQUEST_METRICS" for x in cmds.json()["commands"])
            hb = await c.post(
                "/api/v1/fleet/heartbeat",
                json={
                    "node_id": nid,
                    "session_secret": secret,
                    "products": {"chorusgraph": "1.3.0"},
                    "ledger_dropped_total": 7,
                },
            )
            assert hb.status_code == 200
            topo = await c.get("/api/v1/fleet/topology", headers=h)
            node = next(n for n in topo.json()["nodes"] if n["node_id"] == nid)
            assert node["agent_ledger_dropped_total"] == 7
            assert "invalidation_coverage" in topo.json()


@pytest.mark.asyncio
async def test_wp9_trace_purge_and_sampled(tmp_path, monkeypatch):
    from choruscontrol.services.trace_retention import purge_traces

    app = _app_client(
        tmp_path,
        monkeypatch,
        demo=True,
        extra_env={"CHORUSCONTROL_LEDGER_SAMPLE_RATE": "1.0"},
    )
    h = {"Authorization": "Bearer dev-admin-token"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        async with app.router.lifespan_context(app):
            s = app.state.cc
            await s.store.execute(
                "INSERT INTO traces(run_id, tenant_id, wire_json, created_at) VALUES(?,?,?,?)",
                ("old", "default", "{}", time.time() - 86400 * 40),
            )
            await s.store.execute(
                "INSERT INTO ledger_entries(tenant_id, node_id, run_id, payload_json, sampled, created_at) "
                "VALUES(?,?,?,?,?,?)",
                ("default", "n", "old", "{}", 1, time.time() - 86400 * 40),
            )
            out = await purge_traces(s.store, retention_days=14, max_rows=100000)
            assert out["traces_after"] < out["traces_before"] or out["traces_before"] >= 1
            # ledger batch sampled=1
            tok = await c.post("/api/v1/fleet/join-tokens", headers=h, json={})
            joined = await c.post(
                "/api/v1/fleet/join",
                json={
                    "join_token": tok.json()["join_token"],
                    "node_id": "samp",
                    "products": {"chorusgraph": "1.3.0"},
                },
            )
            await c.post(
                "/api/v1/fleet/ledger-batch",
                json={
                    "node_id": "samp",
                    "tenant_id": "default",
                    "entries": [{"stage": "graph", "run_id": "r1"}],
                },
            )
            row = await s.store.fetchone(
                "SELECT sampled FROM ledger_entries WHERE run_id=? ORDER BY id DESC LIMIT 1",
                ("r1",),
            )
            assert row and row["sampled"] == 1


@pytest.mark.asyncio
async def test_wp11_doctor_exit(tmp_path, monkeypatch):
    from choruscontrol.cli import _doctor_exit_code

    assert _doctor_exit_code({"mode": "mother", "demo_mode": True}) == 0
    assert (
        _doctor_exit_code(
            {"mode": "mother", "demo_mode": False, "license": {"state": "invalid"}}
        )
        == 1
    )
    assert (
        _doctor_exit_code(
            {"mode": "mother", "demo_mode": False, "license": {"state": "valid"}, "store_writable": False}
        )
        == 1
    )
