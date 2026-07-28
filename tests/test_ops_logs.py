from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from choruscontrol.config import get_settings


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_ops_logs_search_and_ingest(tmp_path, monkeypatch):
    monkeypatch.setenv("CHORUSCONTROL_DEMO_MODE", "1")
    monkeypatch.setenv("CHORUSCONTROL_SQLITE_PATH", str(tmp_path / "cc.db"))
    monkeypatch.setenv("CHORUSCONTROL_AUDIT_LOG_PATH", str(tmp_path / "a.jsonl"))
    monkeypatch.setenv("CHORUSCONTROL_ADMIN_TOKEN", "dev-admin-token")
    get_settings.cache_clear()

    from choruscontrol.server import create_app

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with app.router.lifespan_context(app):
            headers = {"Authorization": "Bearer dev-admin-token"}

            # Mother boot should emit a system log
            boot = await client.get("/api/v1/logs?source=system&limit=20", headers=headers)
            assert boot.status_code == 200
            assert any("mother online" in (e.get("message") or "") for e in boot.json()["entries"])

            # Audit actions mirror into ops logs
            tok = await client.post("/api/v1/fleet/join-tokens", headers=headers)
            assert tok.status_code == 200
            join_token = tok.json()["join_token"]
            joined = await client.post(
                "/api/v1/fleet/join",
                json={
                    "join_token": join_token,
                    "tenant_id": "acme",
                    "role": "GREEN",
                    "products": {"chorusgraph": "1.3.0"},
                },
            )
            assert joined.status_code == 200
            node_id = joined.json()["node_id"]
            secret = joined.json()["session_secret"]

            audit_logs = await client.get(
                "/api/v1/logs?source=audit&q=fleet.join_token&limit=50", headers=headers
            )
            assert audit_logs.status_code == 200
            assert len(audit_logs.json()["entries"]) >= 1

            fleet_logs = await client.get("/api/v1/logs?source=fleet&limit=50", headers=headers)
            assert fleet_logs.status_code == 200
            assert any(node_id in (e.get("message") or "") for e in fleet_logs.json()["entries"])

            # Agent push path
            pushed = await client.post(
                "/api/v1/fleet/logs-batch",
                headers={"X-Node-Session": secret},
                json={
                    "node_id": node_id,
                    "tenant_id": "acme",
                    "entries": [
                        {
                            "source": "agent",
                            "level": "warn",
                            "message": "agent heartbeat lag high",
                            "run_id": "run-xyz",
                        }
                    ],
                },
            )
            assert pushed.status_code == 200
            assert pushed.json()["accepted"] == 1

            found = await client.get(
                "/api/v1/logs?q=heartbeat%20lag&source=agent&limit=20", headers=headers
            )
            assert found.status_code == 200
            assert len(found.json()["entries"]) >= 1
            assert found.json()["entries"][0]["node_id"] == node_id

            # Logs tab is registered
            page = await client.get("/logs")
            assert page.status_code == 200
            assert b'data-tab="logs"' in page.content
