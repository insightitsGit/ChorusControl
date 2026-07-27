"""End-to-end smoke of Side 2 mother APIs — run against ASGI app (no live server required)."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from choruscontrol.config import get_settings


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_full_product_smoke(tmp_path, monkeypatch):
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
            assert (await c.get("/healthz")).status_code == 200
            assert (await c.get("/readyz")).status_code == 200
            assert (await c.get("/overview")).status_code == 200
            assert "Ops Assistant" in (await c.get("/overview")).text
            assert (await c.get("/static/app.js")).status_code == 200
            assert (await c.get("/static/viz.js")).status_code == 200

            # Overview / metrics
            for path in [
                "/api/v1/health/matrix",
                "/api/v1/health/caps",
                "/api/v1/metrics/token-tax",
                "/api/v1/metrics/ai-score",
                "/api/v1/metrics/prismdriver",
                "/api/v1/status/dogfood",
                "/api/v1/policy/drift",
                "/api/v1/recommendations",
                "/api/v1/pipelines/live",
                "/api/v1/admin/license",
                "/api/v1/admin/doctor",
                "/api/v1/guard/policy",
                "/api/v1/guard/logs",
                "/api/v1/guard/shadow/compare",
                "/api/v1/taxonomy/tree",
                "/api/v1/taxonomy/partitions",
                "/api/v1/taxonomy/chunks/health",
                "/api/v1/memory/facts",
                "/api/v1/memory/conflicts",
                "/api/v1/graph",
                "/api/v1/fleet/topology",
                "/api/v1/incidents",
            ]:
                r = await c.get(path, headers=h)
                assert r.status_code == 200, f"{path} -> {r.status_code} {r.text}"

            # Guard policy validation
            bad = await c.put(
                "/api/v1/guard/policy",
                headers=h,
                json={"tenant_id": "default", "policy": {"ingress_profile": "web_chat", "ingress_use_onnx": True}},
            )
            assert bad.status_code == 400

            ok_pol = await c.put(
                "/api/v1/guard/policy",
                headers=h,
                json={
                    "tenant_id": "default",
                    "policy": {
                        "ingress_profile": "web_chat",
                        "ingress_use_onnx": False,
                        "shadow_enabled": True,
                        "shadow_profile": "light",
                        "recommended_preset": "finance_hub",
                    },
                },
            )
            assert ok_pol.status_code == 200

            # Trace + replay
            seed = await c.post("/api/v1/traces/seed", headers=h, json={"tenant_id": "default"})
            assert seed.status_code == 200
            run_id = seed.json()["run_id"]
            tr = await c.get(f"/api/v1/traces/{run_id}", headers=h)
            assert tr.status_code == 200
            replay = await c.post(f"/api/v1/traces/{run_id}/replay", headers=h, json={})
            assert replay.status_code == 200
            assert replay.json()["llm_calls"] == 0
            assert replay.json()["ok"] is True

            # Fleet join + command NACK path + heartbeat
            tok = await c.post("/api/v1/fleet/join-tokens", headers=h, json={"max_uses": 5})
            assert tok.status_code == 200
            join = await c.post(
                "/api/v1/fleet/join",
                json={
                    "join_token": tok.json()["join_token"],
                    "node_id": "smoke-1",
                    "tenant_id": "smoke",
                    "role": "GREEN",
                    "products": {
                        "chorusgraph": "1.3.0",
                        "prismlib-plus": "0.8.0",
                        "prismguard": "0.1.10",
                        "prismcortex": "0.3.0",
                    },
                },
            )
            assert join.status_code == 200
            secret = join.json()["session_secret"]
            hb = await c.post(
                "/api/v1/fleet/heartbeat",
                json={
                    "node_id": "smoke-1",
                    "session_secret": secret,
                    "products": join.json() and {
                        "chorusgraph": "1.3.0",
                        "prismlib-plus": "0.8.0",
                    },
                },
            )
            # heartbeat products from body
            hb = await c.post(
                "/api/v1/fleet/heartbeat",
                json={
                    "node_id": "smoke-1",
                    "session_secret": secret,
                    "products": {"chorusgraph": "1.3.0", "prismlib-plus": "0.8.0"},
                },
            )
            assert hb.status_code == 200

            cmd = await c.post(
                "/api/v1/fleet/nodes/smoke-1/command",
                headers=h,
                json={"type": "REQUEST_CAPS"},
            )
            assert cmd.status_code == 200
            assert cmd.json()["status"] == "queued"

            # Cascade + conflict resolve
            cascade = await c.post(
                "/api/v1/cascade",
                headers=h,
                json={"tenant_id": "smoke", "tags": ["t:smoke"]},
            )
            assert cascade.status_code == 200
            cid = cascade.json()["cascade_id"]
            st = await c.get(f"/api/v1/cascade/{cid}", headers=h)
            assert st.status_code == 200

            conflicts = await c.get("/api/v1/memory/conflicts", headers=h)
            assert conflicts.status_code == 200
            clist = conflicts.json().get("conflicts") or []
            if clist:
                res = await c.post(
                    f"/api/v1/memory/conflicts/{clist[0]['id']}/resolve",
                    headers=h,
                    json={"tenant_id": "default", "resolution": {"keep": "new"}},
                )
                assert res.status_code == 200
                assert "cascade" in res.json()

            # Jobs
            for path, body in [
                ("/api/v1/jobs/sleep", {"tenant_id": "default"}),
                ("/api/v1/jobs/reindex", {"tenant_id": "default"}),
                ("/api/v1/jobs/warm-partition", {"tenant_id": "default", "partition": "kb_markdown"}),
            ]:
                jr = await c.post(path, headers=h, json=body)
                assert jr.status_code == 200, path

            # Assistant
            ask = await c.post(
                "/api/v1/assistant/ask",
                headers=h,
                json={"question": "Show me the live pipeline"},
            )
            assert ask.status_code == 200
            assert ask.json().get("answer")

            # Memory explain / recall
            assert (
                await c.post(
                    "/api/v1/memory/explain",
                    headers=h,
                    json={"tenant_id": "default", "query": "budget"},
                )
            ).status_code == 200
            assert (
                await c.post(
                    "/api/v1/memory/recall_at",
                    headers=h,
                    json={"tenant_id": "default", "query": "budget", "ts": 1.0},
                )
            ).status_code == 200

            # Pipelines after fleet
            pipes = await c.get("/api/v1/pipelines/live", headers=h)
            assert pipes.status_code == 200
            assert pipes.json()["execution"]["stages"]
            assert any(n["id"] == "smoke-1" for n in pipes.json()["fleet"])

            # Graph blast radius
            graph = await c.get("/api/v1/graph", headers=h)
            assets = graph.json().get("assets") or []
            if assets:
                br = await c.get(
                    "/api/v1/graph/blast-radius",
                    headers=h,
                    params={"asset_id": assets[0]["asset_id"]},
                )
                assert br.status_code == 200

            # SOC2 export
            soc2 = await c.get("/api/v1/admin/soc2-export", headers=h)
            assert soc2.status_code == 200
            assert "zip" in (soc2.headers.get("content-type") or "")

            # Lexicon
            assert (
                await c.put(
                    "/api/v1/guard/lexicon",
                    headers=h,
                    json={"tenant_id": "default", "terms": ["fx", "rate"]},
                )
            ).status_code == 200
