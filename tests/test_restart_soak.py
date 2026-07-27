"""Restart soak — mother lifespan restart + re-join smoke."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from choruscontrol.config import get_settings


@pytest.mark.asyncio
async def test_restart_soak_rejoin(tmp_path, monkeypatch):
    monkeypatch.setenv("CHORUSCONTROL_DEMO_MODE", "1")
    monkeypatch.setenv("CHORUSCONTROL_SQLITE_PATH", str(tmp_path / "cc.db"))
    monkeypatch.setenv("CHORUSCONTROL_AUDIT_LOG_PATH", str(tmp_path / "a.jsonl"))
    monkeypatch.setenv("CHORUSCONTROL_ADMIN_TOKEN", "dev-admin-token")
    get_settings.cache_clear()

    from choruscontrol.server import create_app

    headers = {"Authorization": "Bearer dev-admin-token"}

    async def _cycle(app):
        transport = ASGITransport(app=app)
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            async with app.router.lifespan_context(app):
                tok = await client.post("/api/v1/fleet/join-tokens", headers=headers)
                assert tok.status_code == 200
                join_token = tok.json()["join_token"]
                joined = await client.post(
                    "/api/v1/fleet/join",
                    json={
                        "join_token": join_token,
                        "node_id": "soak-1",
                        "tenant_id": "soak",
                        "role": "GREEN",
                        "products": {"chorusgraph": "1.3.0", "prismlib-plus": "0.8.0"},
                    },
                )
                assert joined.status_code == 200
                secret = joined.json()["session_secret"]
                hb = await client.post(
                    "/api/v1/fleet/heartbeat",
                    json={
                        "node_id": "soak-1",
                        "session_secret": secret,
                        "products": {"chorusgraph": "1.3.0", "prismlib-plus": "0.8.0"},
                    },
                )
                assert hb.status_code == 200
                # enqueue command
                cmd = await client.post(
                    "/api/v1/fleet/nodes/soak-1/command",
                    headers=headers,
                    json={"type": "REQUEST_CAPS"},
                )
                assert cmd.status_code == 200
                return secret

    # first boot
    app1 = create_app()
    await _cycle(app1)
    # "restart" — new app same sqlite
    get_settings.cache_clear()
    monkeypatch.setenv("CHORUSCONTROL_DEMO_MODE", "1")
    monkeypatch.setenv("CHORUSCONTROL_SQLITE_PATH", str(tmp_path / "cc.db"))
    app2 = create_app()
    transport = ASGITransport(app=app2)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with app2.router.lifespan_context(app2):
            nodes = await client.get("/api/v1/fleet/nodes", headers=headers)
            assert nodes.status_code == 200
            assert any(n["node_id"] == "soak-1" for n in nodes.json()["nodes"])
            # re-join with new token after restart (session may rotate on re-join)
            tok = await client.post("/api/v1/fleet/join-tokens", headers=headers)
            joined = await client.post(
                "/api/v1/fleet/join",
                json={
                    "join_token": tok.json()["join_token"],
                    "node_id": "soak-1",
                    "tenant_id": "soak",
                    "role": "GREEN",
                    "products": {"chorusgraph": "1.3.0", "prismlib-plus": "0.8.0"},
                },
            )
            assert joined.status_code == 200
            secret = joined.json()["session_secret"]
            cmds = await client.get(
                "/api/v1/fleet/nodes/soak-1/commands",
                headers={"X-Node-Session": secret},
            )
            assert cmds.status_code == 200
