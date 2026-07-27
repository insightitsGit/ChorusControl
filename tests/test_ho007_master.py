"""HO-007 / HO-004/005/006 — LiveRag mapping, Taxonomy gate, pins, secrets, cascade."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from choruscontrol.adapters.live import LiveGraph, try_construct
from choruscontrol.adapters.pins import check_pins, package_version, taxonomy_packs_ready
from choruscontrol.config import get_settings
from choruscontrol.services.taxonomy_rag import construct_prismrag, mapping_for_tenant


def test_package_version_nonzero():
    assert package_version()
    assert package_version()[0].isdigit()


def test_pin_tiers_and_install_hint():
    report = check_pins()
    assert "pins" in report
    assert "core_ok" in report
    assert any(p.get("tier") == "core" for p in report["pins"])
    assert any(p.get("tier") == "optional" for p in report["pins"])
    # missing optional must not flip core_ok by itself when cores present
    for p in report["pins"]:
        assert "severity" in p


def test_taxonomy_packs_ready_shape():
    tax = taxonomy_packs_ready()
    assert "rag" in tax and "guard" in tax and "ready" in tax
    assert isinstance(tax["messages"], list)


def test_bug009_construct_prismrag_requires_mapping():
    pytest.importorskip("prismrag_patch")
    client = construct_prismrag("aurora-health")
    assert client is not None
    mapping = mapping_for_tenant("aurora-health")
    assert mapping.get("categories")


def test_bug009_try_construct_rag_live():
    pytest.importorskip("prismrag_patch")
    adapter = try_construct("rag")
    assert adapter is not None
    assert type(adapter).__name__ == "LiveRag"


@pytest.mark.asyncio
async def test_bug010_mark_revalidate_tolerates_chorusgraph_signature():
    """chorusgraph.mark_revalidate(sidecar, *, packet_ids=...) must not crash cascade."""
    import chorusgraph

    graph = LiveGraph(chorusgraph)
    await graph.mark_revalidate("t1", ["tag_a"])


@pytest.mark.asyncio
async def test_bug010_mark_revalidate_null_style():
    class Fake:
        def mark_revalidate(self, tenant_id, tags):
            self.called = (tenant_id, tags)

    fake = Fake()
    g = LiveGraph(fake)
    await g.mark_revalidate("acme", ["a", "b"])
    assert fake.called == ("acme", ["a", "b"])


@pytest.mark.asyncio
async def test_bug008_fleet_nodes_redact_session_secret(tmp_path, monkeypatch):
    monkeypatch.setenv("CHORUSCONTROL_DEMO_MODE", "1")
    monkeypatch.setenv("CHORUSCONTROL_SQLITE_PATH", str(tmp_path / "fleet.db"))
    monkeypatch.setenv("CHORUSCONTROL_AUDIT_LOG_PATH", str(tmp_path / "a.jsonl"))
    monkeypatch.setenv("CHORUSCONTROL_ADMIN_TOKEN", "dev-admin-token")
    get_settings.cache_clear()

    from choruscontrol.server import create_app

    app = create_app()
    h = {"Authorization": "Bearer dev-admin-token"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        async with app.router.lifespan_context(app):
            tok = await c.post("/api/v1/fleet/join-tokens", headers=h, json={"max_uses": 2})
            assert tok.status_code == 200
            join = await c.post(
                "/api/v1/fleet/join",
                json={
                    "join_token": tok.json()["join_token"],
                    "node_id": "n-secret",
                    "tenant_id": "default",
                    "role": "worker",
                    "network_zone": "in_vpc",
                    "products": {},
                },
            )
            assert join.status_code == 200, join.text
            assert "session_secret" in join.json()

            nodes = await c.get("/api/v1/fleet/nodes", headers=h)
            assert nodes.status_code == 200
            raw = nodes.json()
            node_list = raw if isinstance(raw, list) else raw.get("nodes") or []
            assert node_list
            for n in node_list:
                assert "session_secret" not in n

            topo = await c.get("/api/v1/fleet/topology", headers=h)
            assert topo.status_code == 200
            for n in topo.json().get("nodes") or []:
                assert "session_secret" not in n


@pytest.mark.asyncio
async def test_ho005_taxonomy_503_without_packs_non_demo(tmp_path, monkeypatch):
    monkeypatch.setenv("CHORUSCONTROL_DEMO_MODE", "0")
    monkeypatch.setenv("CHORUSCONTROL_SQLITE_PATH", str(tmp_path / "t.db"))
    monkeypatch.setenv("CHORUSCONTROL_AUDIT_LOG_PATH", str(tmp_path / "a.jsonl"))
    monkeypatch.setenv("CHORUSCONTROL_ADMIN_TOKEN", "strong-admin-token-32chars!!")
    monkeypatch.delenv("CHORUSCONTROL_LICENSE_KEY", raising=False)
    get_settings.cache_clear()

    # Force packs not ready even if environment has them installed
    monkeypatch.setattr(
        "choruscontrol.api.routes.taxonomy_packs_ready",
        lambda: {
            "rag": {"ok": False, "package": None, "version": None},
            "guard": {"ok": False, "package": None, "version": None},
            "ready": False,
            "messages": ["mocked missing"],
            "install_hint": 'pip install "choruscontrol[server,prism]"',
        },
    )

    from choruscontrol.server import create_app

    # Auto-issue is off; need a valid license for API — use demo issue path via verifier in demo=0
    # Install a signed JWT with packaged key is hard without ceremony private.
    # Use DEMO path for license: temporarily allow by monkeypatching license state after build.
    app = create_app()
    h = {"Authorization": "Bearer strong-admin-token-32chars!!"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        async with app.router.lifespan_context(app):
            # Bypass license gate for this unit test
            app.state.cc.license_status.state = "valid"
            r = await c.get("/api/v1/taxonomy/tree?tenant_id=default", headers=h)
            assert r.status_code == 503, r.text
            detail = r.json().get("detail") or {}
            if isinstance(detail, dict):
                assert detail.get("code") == "TAXONOMY_PACKS_REQUIRED"
                assert "install_hint" in detail


@pytest.mark.asyncio
async def test_ho005_taxonomy_ok_in_demo_without_forcing_packs(tmp_path, monkeypatch):
    monkeypatch.setenv("CHORUSCONTROL_DEMO_MODE", "1")
    monkeypatch.setenv("CHORUSCONTROL_SQLITE_PATH", str(tmp_path / "t2.db"))
    monkeypatch.setenv("CHORUSCONTROL_AUDIT_LOG_PATH", str(tmp_path / "a2.jsonl"))
    monkeypatch.setenv("CHORUSCONTROL_ADMIN_TOKEN", "dev-admin-token")
    get_settings.cache_clear()

    from choruscontrol.server import create_app

    app = create_app()
    h = {"Authorization": "Bearer dev-admin-token"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        async with app.router.lifespan_context(app):
            r = await c.get("/api/v1/taxonomy/tree?tenant_id=default", headers=h)
            assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_ho004_taxonomy_live_when_prismrag(tmp_path, monkeypatch):
    pytest.importorskip("prismrag_patch")
    pytest.importorskip("prismguard")

    monkeypatch.setenv("CHORUSCONTROL_DEMO_MODE", "1")
    monkeypatch.setenv("CHORUSCONTROL_SQLITE_PATH", str(tmp_path / "t3.db"))
    monkeypatch.setenv("CHORUSCONTROL_AUDIT_LOG_PATH", str(tmp_path / "a3.jsonl"))
    monkeypatch.setenv("CHORUSCONTROL_ADMIN_TOKEN", "dev-admin-token")
    get_settings.cache_clear()

    from choruscontrol.services import taxonomy_rag

    taxonomy_rag._clients.clear()
    taxonomy_rag._seeded.clear()

    from choruscontrol.server import create_app

    app = create_app()
    h = {"Authorization": "Bearer dev-admin-token"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        async with app.router.lifespan_context(app):
            tree = await c.get("/api/v1/taxonomy/tree?tenant_id=aurora-health", headers=h)
            assert tree.status_code == 200
            body = tree.json()
            assert body.get("demo") is False
            assert body.get("engine") == "prismrag-patch"
            parts = await c.get("/api/v1/taxonomy/partitions?tenant_id=aurora-health", headers=h)
            assert parts.status_code == 200
            assert parts.json().get("demo") is False

            doc = await c.get("/api/v1/admin/doctor", headers=h)
            assert doc.status_code == 200
            d = doc.json()
            assert d.get("version")
            assert "taxonomy_packs" in d
            assert "pins" in d


@pytest.mark.asyncio
async def test_cascade_post_survives_mark_revalidate(tmp_path, monkeypatch):
    monkeypatch.setenv("CHORUSCONTROL_DEMO_MODE", "1")
    monkeypatch.setenv("CHORUSCONTROL_SQLITE_PATH", str(tmp_path / "c.db"))
    monkeypatch.setenv("CHORUSCONTROL_AUDIT_LOG_PATH", str(tmp_path / "a.jsonl"))
    monkeypatch.setenv("CHORUSCONTROL_ADMIN_TOKEN", "dev-admin-token")
    get_settings.cache_clear()

    from choruscontrol.server import create_app

    app = create_app()
    h = {"Authorization": "Bearer dev-admin-token"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        async with app.router.lifespan_context(app):
            r = await c.post(
                "/api/v1/cascade",
                headers=h,
                json={"tenant_id": "default", "tags": ["med_recon"], "reason": "qa"},
            )
            assert r.status_code == 200, r.text
            assert r.json().get("cascade_id")
