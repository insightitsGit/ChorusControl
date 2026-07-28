from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from choruscontrol.config import get_settings


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_client_chat_ingest_list_compact(tmp_path, monkeypatch):
    monkeypatch.setenv("CHORUSCONTROL_DEMO_MODE", "1")
    monkeypatch.setenv("CHORUSCONTROL_SQLITE_PATH", str(tmp_path / "cc.db"))
    monkeypatch.setenv("CHORUSCONTROL_AUDIT_LOG_PATH", str(tmp_path / "a.jsonl"))
    monkeypatch.setenv("CHORUSCONTROL_ADMIN_TOKEN", "dev-admin-token")
    get_settings.cache_clear()

    from choruscontrol.server import create_app

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with app.router.lifespan_context(app):
            headers = {"Authorization": "Bearer dev-admin-token"}

            ingest = await client.post(
                "/api/v1/chats/ingest",
                headers=headers,
                json={
                    "session_id": "sess-demo-1",
                    "tenant_id": "acme",
                    "user_ref": "patient-42",
                    "title": "Billing question",
                    "messages": [
                        {"role": "user", "content": "What is my deductible?", "message_id": "m1"},
                        {
                            "role": "assistant",
                            "content": "Your plan deductible is $500.",
                            "message_id": "m2",
                        },
                    ],
                },
            )
            assert ingest.status_code == 200, ingest.text
            body = ingest.json()
            assert body["accepted"] == 2
            assert body["session_id"] == "sess-demo-1"
            assert body["message_count"] == 2

            listed = await client.get("/api/v1/chats/sessions?tenant_id=acme", headers=headers)
            assert listed.status_code == 200
            sessions = listed.json()["sessions"]
            assert any(s["session_id"] == "sess-demo-1" for s in sessions)
            assert sessions[0]["compact_status"] == "raw"

            detail = await client.get("/api/v1/chats/sessions/sess-demo-1", headers=headers)
            assert detail.status_code == 200
            d = detail.json()
            assert len(d["messages"]) == 2
            assert d["messages"][0]["content"].startswith("What is")

            compact = await client.post(
                "/api/v1/chats/sessions/sess-demo-1/compact",
                headers=headers,
                json={},
            )
            assert compact.status_code == 200, compact.text
            c = compact.json()
            assert c["compact_status"] == "compacted"
            assert c["pruned_messages"] == 2
            assert c["bytes_before"] >= 40
            assert c["cortex_digest_ref"]
            assert c.get("summary")

            after = await client.get("/api/v1/chats/sessions/sess-demo-1", headers=headers)
            assert after.status_code == 200
            ad = after.json()
            assert ad["compact_status"] == "compacted"
            assert ad["summary"]
            # pruned messages omitted from default view
            assert ad["messages"] == [] or all(m.get("pruned") for m in ad["messages"])

            # More turns mark session dirty again
            again = await client.post(
                "/api/v1/chats/ingest",
                headers=headers,
                json={
                    "session_id": "sess-demo-1",
                    "tenant_id": "acme",
                    "messages": [
                        {"role": "user", "content": "And copay?", "message_id": "m3"},
                    ],
                },
            )
            assert again.status_code == 200
            listed2 = await client.get("/api/v1/chats/sessions?tenant_id=acme", headers=headers)
            row = next(s for s in listed2.json()["sessions"] if s["session_id"] == "sess-demo-1")
            assert row["compact_status"] == "dirty"


@pytest.mark.asyncio
async def test_fleet_chat_batch(tmp_path, monkeypatch):
    monkeypatch.setenv("CHORUSCONTROL_DEMO_MODE", "1")
    monkeypatch.setenv("CHORUSCONTROL_SQLITE_PATH", str(tmp_path / "cc.db"))
    monkeypatch.setenv("CHORUSCONTROL_AUDIT_LOG_PATH", str(tmp_path / "a.jsonl"))
    monkeypatch.setenv("CHORUSCONTROL_ADMIN_TOKEN", "dev-admin-token")
    get_settings.cache_clear()

    from choruscontrol.server import create_app

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        async with app.router.lifespan_context(app):
            headers = {"Authorization": "Bearer dev-admin-token"}
            tok = await client.post("/api/v1/fleet/join-tokens", headers=headers)
            join_token = tok.json()["join_token"]
            joined = await client.post(
                "/api/v1/fleet/join",
                json={
                    "join_token": join_token,
                    "tenant_id": "acme",
                    "role": "GREEN",
                    "products": {"chorusgraph": "1.3.0"},
                },
            )
            assert joined.status_code == 200
            node_id = joined.json()["node_id"]
            secret = joined.json()["session_secret"]

            pushed = await client.post(
                "/api/v1/fleet/chat-batch",
                headers={"X-Node-Session": secret},
                json={
                    "node_id": node_id,
                    "tenant_id": "acme",
                    "session_id": "agent-sess-9",
                    "user_ref": "u-9",
                    "messages": [
                        {"role": "user", "content": "Hello from edge", "message_id": "a1"},
                        {"role": "assistant", "content": "Hi there", "message_id": "a2"},
                    ],
                },
            )
            assert pushed.status_code == 200, pushed.text
            assert pushed.json()["accepted"] == 2

            listed = await client.get("/api/v1/chats/sessions?tenant_id=acme", headers=headers)
            assert any(s["session_id"] == "agent-sess-9" for s in listed.json()["sessions"])
