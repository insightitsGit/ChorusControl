"""PrismRAG taxonomy search, related terms, and online overwrite."""

import pytest
from httpx import ASGITransport, AsyncClient

from choruscontrol.config import get_settings


@pytest.mark.asyncio
async def test_taxonomy_search_related_and_overwrite(tmp_path, monkeypatch):
    pytest.importorskip("prismrag_patch")

    monkeypatch.setenv("CHORUSCONTROL_DEMO_MODE", "1")
    monkeypatch.setenv("CHORUSCONTROL_SQLITE_PATH", str(tmp_path / "cc.db"))
    monkeypatch.setenv("CHORUSCONTROL_AUDIT_LOG_PATH", str(tmp_path / "a.jsonl"))
    monkeypatch.setenv("CHORUSCONTROL_ADMIN_TOKEN", "dev-admin-token")
    get_settings.cache_clear()

    # Fresh PrismRAG clients per test process
    from choruscontrol.services import taxonomy_rag

    taxonomy_rag._clients.clear()
    taxonomy_rag._seeded.clear()

    from choruscontrol.server import create_app

    app = create_app()
    h = {"Authorization": "Bearer dev-admin-token"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        async with app.router.lifespan_context(app):
            await c.post(
                "/api/v1/admin/tenants",
                headers=h,
                json={"tenant_id": "aurora-health", "name": "Aurora"},
            )

            search = await c.post(
                "/api/v1/taxonomy/search",
                headers=h,
                json={"tenant_id": "aurora-health", "query": "med recon allergy"},
            )
            assert search.status_code == 200, search.text
            body = search.json()
            assert body["engine"] == "prismrag-patch"
            assert body["results"]
            assert body["related_terms"]
            assert any(
                t["term"] in ("insulin", "guideline", "discharge", "allergy", "prior_auth", "med_recon")
                for t in body["related_terms"]
            )

            ref = body["results"][0]["chunk_ref"]
            new_text = (
                "UPDATED ONLINE: Medication reconciliation MUST check allergies, "
                "prior_auth, and insulin interactions before discharge."
            )
            ow = await c.post(
                "/api/v1/taxonomy/chunks/overwrite",
                headers=h,
                json={
                    "tenant_id": "aurora-health",
                    "chunk_ref": ref,
                    "text": new_text,
                    "category_slug": body["results"][0].get("category_slug"),
                    "partition": "kb_clinical_guidelines",
                },
            )
            assert ow.status_code == 200, ow.text
            saved = ow.json()
            assert saved["ok"] is True
            assert saved["chunk_ref"] == ref
            assert "UPDATED ONLINE" in saved["chunk_text"]
            assert saved["embedding_dim"] > 0

            again = await c.post(
                "/api/v1/taxonomy/search",
                headers=h,
                json={"tenant_id": "aurora-health", "query": "insulin allergy"},
            )
            assert again.status_code == 200
            texts = " ".join(
                (h.get("chunk_text") or h.get("text") or "") for h in again.json()["results"]
            )
            assert "UPDATED ONLINE" in texts

            chunks = await c.get(
                "/api/v1/taxonomy/chunks",
                headers=h,
                params={"tenant_id": "aurora-health"},
            )
            assert chunks.status_code == 200
            assert chunks.json()["count"] >= 1
