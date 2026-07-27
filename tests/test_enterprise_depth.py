"""Enterprise depth WPs — graph enrichment, policies, compliance, version diff, cold-audit honesty."""

from __future__ import annotations

import json
import time

import pytest
from httpx import ASGITransport, AsyncClient

from choruscontrol.config import get_settings


@pytest.mark.asyncio
async def test_enterprise_depth_suite(tmp_path, monkeypatch):
    monkeypatch.setenv("CHORUSCONTROL_DEMO_MODE", "1")
    monkeypatch.setenv("CHORUSCONTROL_SQLITE_PATH", str(tmp_path / "cc.db"))
    monkeypatch.setenv("CHORUSCONTROL_AUDIT_LOG_PATH", str(tmp_path / "a.jsonl"))
    monkeypatch.setenv("CHORUSCONTROL_ADMIN_TOKEN", "dev-admin-token")
    monkeypatch.setenv("CHORUSCONTROL_METRICS_SAMPLE_INTERVAL", "3600")
    get_settings.cache_clear()

    from choruscontrol.server import create_app
    from choruscontrol.services.enterprise_policy import check_allowed, upsert_policy
    from choruscontrol.services.graph import sync_from_fleet
    from choruscontrol.services.incidents import link_cascade_incident

    app = create_app()
    h = {"Authorization": "Bearer dev-admin-token"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        async with app.router.lifespan_context(app):
            s = app.state.cc

            # WP-E1 cold audit honesty
            cold = await c.post("/api/v1/metrics/cold-audit", headers=h, json={"queries": ["a", "b"]})
            assert cold.status_code == 200
            assert cold.json().get("simulated") is False
            assert cold.json().get("estimated_cache_hits") is None

            # WP-P1 enterprise policies
            pol = await upsert_policy(
                s.store,
                domain="memory.write",
                tenant_id="default",
                name="writers",
                body={"allow": ["admin"], "mode": "allowlist"},
            )
            assert pol["version"] == 1
            denied = await check_allowed(
                s.store,
                domain="memory.write",
                tenant_id="default",
                action="digest",
                context={"role": "viewer"},
            )
            assert denied["allowed"] is False
            assert (await c.get("/api/v1/enterprise/policies", headers=h)).status_code == 200

            # WP-C1 compliance
            scan = await c.post("/api/v1/compliance/scan", headers=h, json={})
            assert scan.status_code == 200
            assert "findings" in scan.json()

            # WP-R04 memory endpoint
            await s.store.execute(
                "INSERT INTO nodes(node_id, tenant_id, role, network_zone, products_json, caps_digest, "
                "last_seen, memory_endpoint, session_secret, revoked) VALUES(?,?,?,?,?,?,?,?,?,0)",
                (
                    "mem-1",
                    "default",
                    "memory",
                    "in_vpc",
                    json.dumps({"prismcortex": "0.3.0"}),
                    "x",
                    time.time(),
                    "local://mem-1",
                    "secret",
                ),
            )
            assert await s.fleet.memory_endpoint_for_tenant("default") == "local://mem-1"

            # WP-I1 / WP-G1 incident + graph
            casc = await s.cascade.run("default", ["kb"], reason="test")
            inc = await link_cascade_incident(s.store, casc, "default")
            assert inc.get("asset_id")
            intel = await c.get(f"/api/v1/incidents/{inc['incident_id']}/intelligence", headers=h)
            assert intel.status_code == 200
            assert "suggested_resolution" in intel.json()
            await sync_from_fleet(s)
            g = await c.get("/api/v1/graph", headers=h)
            assert g.status_code == 200
            assert len(g.json().get("assets") or []) >= 1

            # WP-V1 version diff
            await s.store.execute(
                "INSERT INTO version_snapshots(node_id, day, products_json, caps_digest) VALUES(?,?,?,?)",
                ("n1", "2026-07-01", json.dumps({"chorusgraph": "1.0.0"}), "a"),
            )
            await s.store.execute(
                "INSERT INTO version_snapshots(node_id, day, products_json, caps_digest) VALUES(?,?,?,?)",
                ("n1", "2026-07-02", json.dumps({"chorusgraph": "1.3.0"}), "b"),
            )
            diff = await c.get("/api/v1/fleet/version-diff?node_id=n1", headers=h)
            assert diff.status_code == 200
            assert "chorusgraph" in (diff.json().get("products_diff") or {})

            # WP-S1 score inputs
            score = await c.get("/api/v1/metrics/ai-score", headers=h)
            assert score.status_code == 200
            assert "inputs" in score.json()

            # WP-A1 assistant execute incident
            ask = await c.post(
                "/api/v1/assistant/ask",
                headers=h,
                json={
                    "question": "open an incident",
                    "confirm": True,
                    "execute": {
                        "type": "incident.create",
                        "params": {"tenant_id": "default", "title": "Test from assistant"},
                    },
                },
            )
            assert ask.status_code == 200
            body = ask.json()
            assert body.get("execution", {}).get("status") == "ok"

            # Cortex serving field
            snap = await c.get("/api/v1/cortex/snapshot?tenant_id=default", headers=h)
            assert snap.status_code == 200
            assert "engine" in snap.json()
