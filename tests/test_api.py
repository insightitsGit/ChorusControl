from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from choruscontrol.config import get_settings


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_api_join_and_overview(tmp_path, monkeypatch):
    monkeypatch.setenv("CHORUSCONTROL_DEMO_MODE", "1")
    monkeypatch.setenv("CHORUSCONTROL_SQLITE_PATH", str(tmp_path / "cc.db"))
    monkeypatch.setenv("CHORUSCONTROL_AUDIT_LOG_PATH", str(tmp_path / "a.jsonl"))
    monkeypatch.setenv("CHORUSCONTROL_ADMIN_TOKEN", "dev-admin-token")
    get_settings.cache_clear()

    from choruscontrol.server import create_app

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # lifespan
        async with app.router.lifespan_context(app):
            h = await client.get("/healthz")
            assert h.status_code == 200
            headers = {"Authorization": "Bearer dev-admin-token"}
            tok = await client.post("/api/v1/fleet/join-tokens", headers=headers)
            assert tok.status_code == 200
            join_token = tok.json()["join_token"]
            joined = await client.post(
                "/api/v1/fleet/join",
                json={
                    "join_token": join_token,
                    "tenant_id": "acme",
                    "role": "GREEN",
                    "products": {"chorusgraph": "1.3.0", "prismlib-plus": "0.8.0"},
                },
            )
            assert joined.status_code == 200
            node_id = joined.json()["node_id"]
            secret = joined.json()["session_secret"]
            hb = await client.post(
                "/api/v1/fleet/heartbeat",
                json={
                    "node_id": node_id,
                    "session_secret": secret,
                    "products": {"chorusgraph": "1.3.0", "prismlib-plus": "0.8.0"},
                },
            )
            assert hb.status_code == 200
            caps = await client.get("/api/v1/health/caps", headers=headers)
            assert caps.status_code == 200
            assert "guard" in caps.json()
            score = await client.get("/api/v1/metrics/ai-score", headers=headers)
            assert score.status_code == 200
            assert "overall" in score.json()
            cascade = await client.post(
                "/api/v1/cascade",
                headers=headers,
                json={"tenant_id": "acme", "tags": ["t:1"]},
            )
            assert cascade.status_code == 200
