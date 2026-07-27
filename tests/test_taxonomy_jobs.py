"""Taxonomy warm / reindex must mutate visible partition state."""

import pytest
from httpx import ASGITransport, AsyncClient

from choruscontrol.config import get_settings


@pytest.mark.asyncio
async def test_taxonomy_warm_and_reindex_bump_versions(tmp_path, monkeypatch):
    monkeypatch.setenv("CHORUSCONTROL_DEMO_MODE", "1")
    monkeypatch.setenv("CHORUSCONTROL_SQLITE_PATH", str(tmp_path / "cc.db"))
    monkeypatch.setenv("CHORUSCONTROL_AUDIT_LOG_PATH", str(tmp_path / "a.jsonl"))
    monkeypatch.setenv("CHORUSCONTROL_ADMIN_TOKEN", "dev-admin-token")
    get_settings.cache_clear()

    from choruscontrol.server import create_app

    app = create_app()
    h = {"Authorization": "Bearer dev-admin-token"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        async with app.router.lifespan_context(app):
            await c.post(
                "/api/v1/admin/tenants",
                headers=h,
                json={"tenant_id": "aurora-health", "name": "Aurora Health"},
            )
            before = await c.get(
                "/api/v1/taxonomy/partitions",
                headers=h,
                params={"tenant_id": "aurora-health"},
            )
            assert before.status_code == 200
            parts = before.json()["partitions"]
            assert any(p["partition"] == "kb_clinical_guidelines" for p in parts)
            ver0 = next(p["version"] for p in parts if p["partition"] == "kb_clinical_guidelines")

            health0 = await c.get(
                "/api/v1/taxonomy/chunks/health",
                headers=h,
                params={"tenant_id": "aurora-health"},
            )
            stale0 = health0.json()["decay"][0]["staleness"]

            warm = await c.post(
                "/api/v1/jobs/warm-partition",
                headers=h,
                json={
                    "tenant_id": "aurora-health",
                    "partition": "kb_clinical_guidelines",
                },
            )
            assert warm.status_code == 200
            job_id = warm.json()["job_id"]
            import asyncio

            st = None
            for _ in range(50):
                st = await c.get(f"/api/v1/jobs/{job_id}", headers=h)
                if st.json()["state"] in ("completed", "failed"):
                    break
                await asyncio.sleep(0.05)
            assert st is not None and st.json()["state"] == "completed"

            after = await c.get(
                "/api/v1/taxonomy/partitions",
                headers=h,
                params={"tenant_id": "aurora-health"},
            )
            ver1 = next(
                p["version"]
                for p in after.json()["partitions"]
                if p["partition"] == "kb_clinical_guidelines"
            )
            assert ver1 == ver0 + 1

            health1 = await c.get(
                "/api/v1/taxonomy/chunks/health",
                headers=h,
                params={"tenant_id": "aurora-health"},
            )
            assert health1.json()["decay"][0]["staleness"] < stale0

            reindex = await c.post(
                "/api/v1/jobs/reindex",
                headers=h,
                json={"tenant_id": "aurora-health"},
            )
            assert reindex.status_code == 200
            rid = reindex.json()["job_id"]
            for _ in range(50):
                st = await c.get(f"/api/v1/jobs/{rid}", headers=h)
                if st.json()["state"] in ("completed", "failed"):
                    break
                await asyncio.sleep(0.05)
            assert st.json()["state"] == "completed"

            after2 = await c.get(
                "/api/v1/taxonomy/partitions",
                headers=h,
                params={"tenant_id": "aurora-health"},
            )
            ver2 = next(
                p["version"]
                for p in after2.json()["partitions"]
                if p["partition"] == "kb_clinical_guidelines"
            )
            assert ver2 >= ver1 + 1

            search = await c.post(
                "/api/v1/taxonomy/search",
                headers=h,
                json={"tenant_id": "aurora-health", "query": "med recon"},
            )
            assert search.status_code == 200
            assert len(search.json()["results"]) >= 1
