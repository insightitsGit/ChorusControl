"""HO-009: Ops Assistant teaches dashboard values in plain English."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from choruscontrol.config import get_settings
from choruscontrol.services.assistant_glossary import (
    explain_cascade,
    explain_cortex,
    explain_doctor,
    explain_guard,
    explain_logs,
    explain_performance_zero,
    explain_taxonomy,
    explain_trace,
)


def _frozen_snap(**over):
    base = {
        "score": {
            "overall": 61.0,
            "demo": True,
            "dimensions": {
                "security": 75.0,
                "governance": 85.0,
                "reliability": 75.0,
                "performance": 0.0,
                "cost_efficiency": 37.0,
                "knowledge_quality": 78.0,
                "compliance": 80.0,
                "operational_health": 75.0,
            },
        },
        "metrics": {"hit_rate": 0.0, "cost_saved_usd": 18.5, "tokens_saved": 0, "demo": True},
        "token_tax": {"hit_rate": 0.0, "demo": True, "driver_p50_ms": None},
        "driver": {"p50_ms": None},
        "incidents": {"open_count": 5, "latest": [{"title": "med recon", "state": "open"}]},
        "fleet": {"total": 3, "online": 3, "nodes": []},
        "pipeline": {
            "run_id": "run-1",
            "stages": ["Guard", "Ledger", "Shine"],
            "stage_detail": [
                {"label": "Guard", "decision": "allow", "status": "ok"},
                {"label": "Shine", "decision": "pass", "status": "ok"},
            ],
            "cascade_state": "completed",
            "cascade_id": "c-1",
        },
        "taxonomy": {
            "engine": "prismrag-patch",
            "demo": False,
            "partitions": [{"partition": "kb_clinical_guidelines", "version": 3}],
            "category_count": 4,
            "health": {"bleed_risk": "n/a", "decay": [{"slug": "meds", "staleness": 0.1}]},
        },
        "taxonomy_packs": {"ready": True, "install_hint": None},
        "guard": {
            "ingress_profile": "web_chat",
            "shadow_profile": "light",
            "shadow_enabled": True,
            "enforce_shadow": False,
            "lexicon_count": 3,
            "caps_demo": True,
        },
        "cortex": {
            "engine": "null",
            "chunk_count": 2,
            "fact_count": 1,
            "conflict_count": 0,
            "activity_count": 1,
            "last_digest": "digest",
            "last_sleep_consolidated": 2,
        },
        "doctor": {
            "license": {"state": "valid"},
            "pins": {
                "pins": [
                    {"package": "prismguard", "ok": True, "tier": "core", "status": "ok"},
                    {"package": "chorus-fabric", "ok": False, "tier": "optional", "status": "missing"},
                ],
                "missing_core": [],
            },
            "taxonomy_packs": {"ready": True},
            "install_hint": None,
            "fleet_nodes": 3,
        },
        "trace": {"recent_count": 1, "latest_run_id": "run-1"},
        "logs": {"count": 12, "sources": ["audit", "fleet"], "levels": ["info"]},
        "license": {"state": "valid", "tier": "enterprise"},
        "lowest_dimensions": [{"key": "performance", "value": 0.0}],
        "matrix": {},
    }
    base.update(over)
    return base


def test_glossary_performance_zero_includes_live_hit_rate():
    ans = explain_performance_zero(_frozen_snap())
    assert "Performance is 0" in ans
    assert "hit_rate" in ans
    assert "0.0" in ans or "0" in ans
    assert "Token tax" in ans


def test_glossary_taxonomy_engine_and_version():
    ans = explain_taxonomy(_frozen_snap(), focus="engine")
    assert "prismrag-patch" in ans
    assert "Live now" in ans or "engine=" in ans
    ver = explain_taxonomy(_frozen_snap(), focus="partition_version")
    assert "v3" in ver or "version" in ver.lower()


def test_glossary_doctor_core_vs_optional():
    ans = explain_doctor(_frozen_snap(), focus="pin_floors")
    assert "optional" in ans.lower()
    assert "core" in ans.lower()
    assert "chorus-fabric" in ans or "optional_missing" in ans


def test_glossary_cascade_completed():
    ans = explain_cascade(_frozen_snap())
    assert "completed" in ans
    assert "invalidate" in ans.lower() or "mark_revalidate" in ans.lower()


def test_glossary_trace_replay_guard_cortex_logs():
    assert "zero-token" in explain_trace(_frozen_snap(), focus="replay").lower()
    assert "shadow" in explain_guard(_frozen_snap(), focus="shadow_compare").lower()
    assert "digest" in explain_cortex(_frozen_snap(), focus="digest").lower()
    assert "node" in explain_logs(_frozen_snap(), focus="source_filter").lower()


STARTER_QUESTIONS = [
    ("Explain the dashboard numbers in plain English", ["AI Score", "Reliability"]),
    ("Why is Performance 0?", ["Performance", "hit_rate"]),
    ("Why is Cost efficiency low?", ["Cost"]),
    ("What does Reliability mean with 5 incidents?", ["Reliability", "incident"]),
    ("What is L5 Prism pack?", ["L5", "Prism"]),
    ("What does cascade completed mean?", ["cascade", "completed"]),
    ("What is a GREEN agent?", ["GREEN"]),
    ("What does Taxonomy engine prismrag-patch mean?", ["prismrag", "engine"]),
    ("What is a partition version?", ["partition", "version"]),
    ("What does chunk staleness mean?", ["stale"]),
    ("What is Guard shadow compare?", ["shadow"]),
    ("What do pin floors mean? Core vs optional?", ["pin", "optional"]),
    ("What is taxonomy_packs.ready?", ["taxonomy_packs", "ready"]),
    ("What does Cortex digest committed mean?", ["digest"]),
    ("What is zero-token replay?", ["replay", "token"]),
]


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_assistant_starter_question_pack(tmp_path, monkeypatch):
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
            # Seed incidents so reliability teachables have live count
            for i in range(5):
                await c.post(
                    "/api/v1/incidents",
                    headers=h,
                    json={"tenant_id": "default", "title": f"inc-{i}", "details": {}},
                )
            await c.post(
                "/api/v1/cascade",
                headers=h,
                json={"tenant_id": "default", "tags": ["t:qa"], "reason": "ho009"},
            )
            # Force performance teachable path even if demo hit_rate is high:
            # still ask the question; answer must mention hit_rate / Performance.
            for q, needles in STARTER_QUESTIONS:
                r = await c.post("/api/v1/assistant/ask", headers=h, json={"question": q})
                assert r.status_code == 200, q
                ans = r.json()["answer"].lower()
                for n in needles:
                    assert n.lower() in ans, f"Q={q!r} missing {n!r} in {ans[:400]}"
                # Live grounding present
                g = r.json()["grounding"]
                assert g.get("ai_score") is not None


@pytest.mark.asyncio
async def test_snapshot_includes_tab_teachables(tmp_path, monkeypatch):
    monkeypatch.setenv("CHORUSCONTROL_DEMO_MODE", "1")
    monkeypatch.setenv("CHORUSCONTROL_SQLITE_PATH", str(tmp_path / "cc2.db"))
    monkeypatch.setenv("CHORUSCONTROL_AUDIT_LOG_PATH", str(tmp_path / "a2.jsonl"))
    monkeypatch.setenv("CHORUSCONTROL_ADMIN_TOKEN", "dev-admin-token")
    get_settings.cache_clear()

    from choruscontrol.app_state import build_state
    from choruscontrol.config import get_settings as gs
    from choruscontrol.services.assistant import dashboard_snapshot

    state = await build_state(gs())
    snap = await dashboard_snapshot(state)
    for key in ("taxonomy", "guard", "cortex", "doctor", "trace", "logs", "glossaries", "pipeline"):
        assert key in snap, key
    assert "taxonomy" in snap["glossaries"]
    assert "pin_floors" in snap["glossaries"]["doctor"]
