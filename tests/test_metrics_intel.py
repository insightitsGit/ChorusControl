"""Metric samples + predictive recommendations."""

import pytest
from httpx import ASGITransport, AsyncClient

from choruscontrol.config import get_settings
from choruscontrol.services.metrics import predictive_recommendations, record_sample, series


@pytest.mark.asyncio
async def test_metric_series_and_recommendations(tmp_path, monkeypatch):
    monkeypatch.setenv("CHORUSCONTROL_DEMO_MODE", "1")
    monkeypatch.setenv("CHORUSCONTROL_SQLITE_PATH", str(tmp_path / "cc.db"))
    monkeypatch.setenv("CHORUSCONTROL_AUDIT_LOG_PATH", str(tmp_path / "a.jsonl"))
    monkeypatch.setenv("CHORUSCONTROL_ADMIN_TOKEN", "dev-admin-token")
    monkeypatch.setenv("CHORUSCONTROL_METRICS_SAMPLE_INTERVAL", "3600")
    get_settings.cache_clear()

    from choruscontrol.server import create_app

    app = create_app()
    h = {"Authorization": "Bearer dev-admin-token"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        async with app.router.lifespan_context(app):
            s = app.state.cc
            # declining hit rate
            for i, v in enumerate([0.95, 0.9, 0.85, 0.8, 0.7, 0.6]):
                await record_sample(s.store, "cache.hit_rate", v)
            pts = await series(s.store, "cache.hit_rate", 20)
            assert len(pts) >= 6
            rec = await predictive_recommendations(s)
            assert rec["predictive"] is True
            assert rec["samples"] >= 6
            r = await c.get("/api/v1/metrics/series?name=cache.hit_rate", headers=h)
            assert r.status_code == 200
            assert r.json()["points"]
            auth = await c.get("/api/v1/admin/auth")
            assert auth.status_code == 200
            assert auth.json()["local_token"] is True
            ready = await c.get("/readyz")
            assert ready.status_code == 200
            assert "postgres" in ready.json()
