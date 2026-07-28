"""BUG-016 / BUG-017 / cascade dedupe helpers for HO-010."""

from __future__ import annotations

import json
from urllib.parse import quote, unquote

import pytest
from httpx import ASGITransport, AsyncClient

from choruscontrol.config import get_settings
from choruscontrol.services.assistant_actions import match_actions


def encode_exec_attr(obj: dict) -> str:
    """Python mirror of app.js encodeExecAttr (encodeURIComponent(JSON))."""
    return quote(json.dumps(obj, separators=(",", ":")), safe="")


def decode_exec_attr(raw: str) -> dict:
    return json.loads(unquote(raw))


def test_encode_exec_attr_survives_apostrophe_in_label():
    payload = {
        "type": "chats.list",
        "label": "List client's chats",
        "params": {"tenant_id": "acme"},
        "mutating": False,
    }
    encoded = encode_exec_attr(payload)
    assert "'" not in encoded  # safe inside single- or double-quoted HTML attrs
    assert decode_exec_attr(encoded)["label"] == "List client's chats"
    # Simulate broken old pattern: attribute wrapped in single quotes without escaping
    broken = f"data-exec='{json.dumps(payload)}'"
    assert broken.count("'") > 2  # apostrophe in label terminates attribute early


def test_cascade_match_dedupes_to_one_type():
    snap = {"tenant_hint": "default", "chats": {}, "trace": {}, "taxonomy": {}}
    actions = match_actions("Run correction cascade", snap)
    types = [a["type"] for a in actions]
    assert types.count("cascade") == 1


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.mark.asyncio
async def test_grace_allows_read_execute_denies_mutate(tmp_path, monkeypatch):
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
            # Middleware refresh_license() would overwrite a one-shot .state= assignment
            from choruscontrol.app_state import AppState

            orig = AppState.refresh_license.__get__(app.state.cc, AppState)

            async def keep_grace():
                status = await orig()
                status.state = "grace"
                app.state.cc.license_status = status
                return status

            app.state.cc.refresh_license = keep_grace  # type: ignore[method-assign]
            await app.state.cc.refresh_license()
            assert app.state.cc.license_status.state == "grace"

            read_exec = {
                "type": "chats.list",
                "mutating": False,
                "params": {"tenant_id": "default", "limit": 10},
            }
            read = await c.post(
                "/api/v1/assistant/ask",
                headers=h,
                json={
                    "question": "Execute confirmed action",
                    "confirm": True,
                    "execute": read_exec,
                },
            )
            assert read.status_code == 200, read.text
            assert read.json()["execution"]["status"] == "ok"

            logs_exec = {
                "type": "logs.search",
                "mutating": False,
                "params": {"q": "mother", "limit": 10},
            }
            logs = await c.post(
                "/api/v1/assistant/ask",
                headers=h,
                json={"question": "Execute", "confirm": True, "execute": logs_exec},
            )
            assert logs.status_code == 200
            assert logs.json()["execution"]["status"] == "ok"

            mut = await c.post(
                "/api/v1/assistant/ask",
                headers=h,
                json={
                    "question": "Execute",
                    "confirm": True,
                    "execute": {
                        "type": "cascade",
                        "mutating": True,
                        "params": {"tenant_id": "default", "tags": ["test"], "reason": "ho010"},
                    },
                },
            )
            assert mut.status_code == 200
            assert mut.json()["execution"]["status"] == "denied"
            assert "grace" in (mut.json()["execution"].get("reason") or "").lower()


@pytest.mark.asyncio
async def test_memory_redirects_to_cortex(tmp_path, monkeypatch):
    monkeypatch.setenv("CHORUSCONTROL_DEMO_MODE", "1")
    monkeypatch.setenv("CHORUSCONTROL_SQLITE_PATH", str(tmp_path / "cc.db"))
    monkeypatch.setenv("CHORUSCONTROL_AUDIT_LOG_PATH", str(tmp_path / "a.jsonl"))
    monkeypatch.setenv("CHORUSCONTROL_ADMIN_TOKEN", "dev-admin-token")
    get_settings.cache_clear()

    from choruscontrol.server import create_app

    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        async with app.router.lifespan_context(app):
            r = await c.get("/memory", follow_redirects=False)
            assert r.status_code == 307
            assert r.headers.get("location") == "/cortex"


@pytest.mark.asyncio
async def test_compliance_optional_null_not_flagged(tmp_path, monkeypatch):
    monkeypatch.setenv("CHORUSCONTROL_DEMO_MODE", "0")
    monkeypatch.setenv("CHORUSCONTROL_SQLITE_PATH", str(tmp_path / "cc.db"))
    monkeypatch.setenv("CHORUSCONTROL_AUDIT_LOG_PATH", str(tmp_path / "a.jsonl"))
    monkeypatch.setenv("CHORUSCONTROL_ADMIN_TOKEN", "dev-admin-token")
    get_settings.cache_clear()

    from choruscontrol.server import create_app
    from choruscontrol.services.compliance import run_compliance_scan

    app = create_app()
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        async with app.router.lifespan_context(app):
            # Only optional fabric null — should not raise auto.adapters.null for fabric alone
            app.state.cc.adapter_sources = {
                "guard": "live:x",
                "shine": "live:x",
                "cortex": "live:x",
                "graph": "live:x",
                "rag": "live:x",
                "cache": "live:x",
                "fabric": "null",
            }
            out = await run_compliance_scan(app.state.cc)
            codes = [f.get("code") for f in out.get("findings") or out.get("created") or []]
            # Also check DB findings
            rows = await app.state.cc.store.fetchall(
                "SELECT code, detail_json FROM compliance_findings WHERE resolved=0 AND code='auto.adapters.null'"
            )
            assert not rows, f"optional fabric null should not flag: {rows}"
