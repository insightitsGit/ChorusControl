"""Ops Assistant per-tab actionable catalog."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from choruscontrol.config import get_settings
from choruscontrol.services.assistant_actions import (
    ACTION_CATALOG,
    actions_for_tab_teach,
    catalog_by_tab,
    match_actions,
)


def test_catalog_covers_all_primary_tabs():
    by = catalog_by_tab()
    for tab in ("overview", "trace", "taxonomy", "cortex", "guard", "logs", "admin"):
        assert tab in by, f"missing tab {tab}"
        assert by[tab], f"empty tab {tab}"
    assert len(ACTION_CATALOG) >= 20


def test_match_actions_reindex_and_join_token():
    snap = {
        "tenant_hint": "default",
        "trace": {"latest_run_id": "run-abc"},
        "taxonomy": {"partitions": [{"partition": "kb_clinical_guidelines"}]},
        "chats": {"sessions": [], "tenant_hint": "default"},
    }
    a = match_actions("Reindex taxonomy", snap)
    assert a and a[0]["type"] == "taxonomy.reindex"
    b = match_actions("Create join token", snap)
    assert b and b[0]["type"] == "fleet.join_token"
    c = match_actions("Seed demo trace", snap)
    assert c and c[0]["type"] == "traces.seed"
    d = match_actions("Show fleet logs", snap)
    assert d and d[0]["type"] == "logs.search"


def test_teach_tab_actions_text():
    text = actions_for_tab_teach("admin")
    assert "Create join token" in text or "chats" in text.lower()
    assert "`" in text


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_assistant_lists_and_executes_catalog_actions(tmp_path, monkeypatch):
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
            listed = await c.post(
                "/api/v1/assistant/ask",
                headers=h,
                json={"question": "What can you do on taxonomy?"},
            )
            assert listed.status_code == 200
            ans = listed.json()["answer"]
            assert "reindex" in ans.lower() or "Warm" in ans or "taxonomy" in ans.lower()

            ask = await c.post(
                "/api/v1/assistant/ask",
                headers=h,
                json={"question": "Create join token"},
            )
            assert ask.status_code == 200
            actions = ask.json().get("actions") or []
            join = next((a for a in actions if a.get("type") == "fleet.join_token"), None)
            assert join is not None

            done = await c.post(
                "/api/v1/assistant/ask",
                headers=h,
                json={
                    "question": "Execute confirmed action",
                    "confirm": True,
                    "execute": join,
                },
            )
            assert done.status_code == 200
            ex = done.json()["execution"]
            assert ex["status"] == "ok"
            assert ex.get("join_token")

            seed_ask = await c.post(
                "/api/v1/assistant/ask",
                headers=h,
                json={"question": "Seed demo trace"},
            )
            seed_act = next(
                (a for a in (seed_ask.json().get("actions") or []) if a.get("type") == "traces.seed"),
                None,
            )
            assert seed_act
            seeded = await c.post(
                "/api/v1/assistant/ask",
                headers=h,
                json={"question": "Execute", "confirm": True, "execute": seed_act},
            )
            assert seeded.json()["execution"]["status"] == "ok"
            assert seeded.json()["execution"]["seed"]["run_id"]
