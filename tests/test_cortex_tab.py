"""PrismCortex tab — activity, chunks, digest/recall."""

import pytest
from httpx import ASGITransport, AsyncClient

from choruscontrol.config import get_settings


@pytest.mark.asyncio
async def test_cortex_snapshot_digest_recall(tmp_path, monkeypatch):
    pytest.importorskip("prismcortex")

    monkeypatch.setenv("CHORUSCONTROL_DEMO_MODE", "1")
    monkeypatch.setenv("CHORUSCONTROL_SQLITE_PATH", str(tmp_path / "cc.db"))
    monkeypatch.setenv("CHORUSCONTROL_AUDIT_LOG_PATH", str(tmp_path / "a.jsonl"))
    monkeypatch.setenv("CHORUSCONTROL_ADMIN_TOKEN", "dev-admin-token")
    get_settings.cache_clear()

    from choruscontrol.services import cortex_ops

    cortex_ops._memories.clear()
    cortex_ops._activity.clear()
    cortex_ops._seeded.clear()

    from choruscontrol.server import create_app

    app = create_app()
    h = {"Authorization": "Bearer dev-admin-token"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        async with app.router.lifespan_context(app):
            # Cortex page exists
            page = await c.get("/cortex")
            assert page.status_code == 200
            assert b"cortex" in page.text.encode().lower() or "Cortex" in page.text

            # memory redirects
            mem = await c.get("/memory", follow_redirects=False)
            assert mem.status_code in (307, 302)

            snap = await c.get(
                "/api/v1/cortex/snapshot",
                headers=h,
                params={"tenant_id": "aurora-health"},
            )
            assert snap.status_code == 200, snap.text
            body = snap.json()
            assert body["engine"] == "prismcortex"
            assert body["chunks"]
            assert body["facts"]
            assert body["activity"]

            dig = await c.post(
                "/api/v1/cortex/digest",
                headers=h,
                json={
                    "tenant_id": "aurora-health",
                    "text": "Clinic hours is 08:00 to 18:00.",
                },
            )
            assert dig.status_code == 200, dig.text
            assert dig.json()["outcome"] in ("committed", "staged", "reinforced", "skipped")

            rec = await c.post(
                "/api/v1/cortex/recall",
                headers=h,
                json={"tenant_id": "aurora-health", "query": "Clinic hours"},
            )
            assert rec.status_code == 200
            assert rec.json()["answer"]

            chunks = await c.get(
                "/api/v1/cortex/chunks",
                headers=h,
                params={"tenant_id": "aurora-health"},
            )
            assert chunks.status_code == 200
            assert chunks.json()["count"] >= 1

            sleep = await c.post(
                "/api/v1/cortex/sleep",
                headers=h,
                json={"tenant_id": "aurora-health"},
            )
            assert sleep.status_code == 200
            assert "consolidated" in sleep.json()
