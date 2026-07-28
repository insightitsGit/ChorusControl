"""Ops Assistant teaches + gated-executes Client AI chat Admin actions."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from choruscontrol.config import get_settings
from choruscontrol.services.assistant_glossary import explain_client_chats


def test_explain_client_chats_live_counts():
    ans = explain_client_chats(
        {
            "chats": {
                "count": 2,
                "raw": 1,
                "dirty": 1,
                "compacted": 0,
                "tenant_hint": "acme",
                "sessions": [
                    {
                        "session_id": "sess-a",
                        "title": "Billing",
                        "tenant_id": "acme",
                        "message_count": 3,
                        "compact_status": "raw",
                    }
                ],
            }
        }
    )
    assert "Client AI chats" in ans
    assert "raw=1" in ans
    assert "sess-a" in ans
    assert "Ops Assistant" in ans
    assert "PrismCortex" in ans or "compact" in ans.lower()


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_assistant_teaches_and_compacts_client_chats(tmp_path, monkeypatch):
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
            seeded = await c.post(
                "/api/v1/chats/ingest",
                headers=h,
                json={
                    "session_id": "sess-assist-1",
                    "tenant_id": "default",
                    "title": "Assist teach",
                    "messages": [
                        {"role": "user", "content": "Hello admin teach", "message_id": "t1"},
                        {"role": "assistant", "content": "Hi", "message_id": "t2"},
                    ],
                },
            )
            assert seeded.status_code == 200

            teach = await c.post(
                "/api/v1/assistant/ask",
                headers=h,
                json={"question": "What are Client AI chats on Admin?"},
            )
            assert teach.status_code == 200
            body = teach.json()
            assert "Client AI" in body["answer"] or "client" in body["answer"].lower()
            assert "sess-assist-1" in body["answer"] or body["actions"]
            assert any(
                (a.get("type") or a.get("command") or "").startswith("chats.")
                for a in (body.get("actions") or [])
            )

            compact_ask = await c.post(
                "/api/v1/assistant/ask",
                headers=h,
                json={"question": "Compact raw client chat sessions"},
            )
            assert compact_ask.status_code == 200
            actions = compact_ask.json().get("actions") or []
            compact_action = next(
                (
                    a
                    for a in actions
                    if (a.get("type") or a.get("command"))
                    in ("chats.compact", "chats.compact_tenant")
                ),
                None,
            )
            assert compact_action is not None

            # Needs confirmation first
            pending = await c.post(
                "/api/v1/assistant/ask",
                headers=h,
                json={
                    "question": "Execute confirmed action",
                    "confirm": False,
                    "execute": compact_action,
                },
            )
            assert pending.status_code == 200
            assert pending.json()["execution"]["status"] == "needs_confirmation"

            done = await c.post(
                "/api/v1/assistant/ask",
                headers=h,
                json={
                    "question": "Execute confirmed action",
                    "confirm": True,
                    "execute": compact_action,
                },
            )
            assert done.status_code == 200
            ex = done.json()["execution"]
            assert ex["status"] == "ok"
            assert "compact" in ex or "compact_tenant" in ex

            listed = await c.get("/api/v1/chats/sessions", headers=h)
            row = next(
                s for s in listed.json()["sessions"] if s["session_id"] == "sess-assist-1"
            )
            assert row["compact_status"] == "compacted"


@pytest.mark.asyncio
async def test_assistant_cortex_sleep_action(tmp_path, monkeypatch):
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
            r = await c.post(
                "/api/v1/assistant/ask",
                headers=h,
                json={"question": "Run cortex sleep for this tenant"},
            )
            assert r.status_code == 200
            actions = r.json().get("actions") or []
            sleep = next((a for a in actions if a.get("type") == "cortex.sleep"), None)
            assert sleep is not None
            done = await c.post(
                "/api/v1/assistant/ask",
                headers=h,
                json={
                    "question": "Execute confirmed action",
                    "confirm": True,
                    "execute": sleep,
                },
            )
            assert done.status_code == 200
            assert done.json()["execution"]["status"] == "ok"
