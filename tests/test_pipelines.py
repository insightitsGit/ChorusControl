"""Pipeline live snapshot for interactive visuals."""

import pytest
from httpx import ASGITransport, AsyncClient

from choruscontrol.config import get_settings


@pytest.mark.asyncio
async def test_pipelines_live(tmp_path, monkeypatch):
    monkeypatch.setenv("CHORUSCONTROL_DEMO_MODE", "1")
    monkeypatch.setenv("CHORUSCONTROL_SQLITE_PATH", str(tmp_path / "cc.db"))
    monkeypatch.setenv("CHORUSCONTROL_AUDIT_LOG_PATH", str(tmp_path / "a.jsonl"))
    monkeypatch.setenv("CHORUSCONTROL_ADMIN_TOKEN", "dev-admin-token")
    get_settings.cache_clear()

    from choruscontrol.server import create_app

    app = create_app()
    headers = {"Authorization": "Bearer dev-admin-token"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        async with app.router.lifespan_context(app):
            await client.post("/api/v1/traces/seed", headers=headers, json={"tenant_id": "default"})
            r = await client.get("/api/v1/pipelines/live", headers=headers)
            assert r.status_code == 200
            data = r.json()
            assert "execution" in data
            assert data["execution"]["stages"]
            assert "fleet" in data
            assert "graph" in data
            a = await client.post(
                "/api/v1/assistant/ask",
                headers=headers,
                json={"question": "Show me the live pipeline"},
            )
            assert a.status_code == 200
            assert "pipeline" in a.json()["answer"].lower() or "Guard" in a.json()["answer"]
