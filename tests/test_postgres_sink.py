"""Postgres sink unit tests (no live DB required)."""

import sys

import pytest

from choruscontrol.persistence.postgres import PostgresSink


@pytest.mark.asyncio
async def test_postgres_connect_without_asyncpg(monkeypatch):
    sink = PostgresSink("postgresql://cc:cc@localhost:5432/choruscontrol")
    monkeypatch.delitem(sys.modules, "asyncpg", raising=False)

    import builtins

    real_import = builtins.__import__

    def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
        if name == "asyncpg" or (isinstance(name, str) and name.startswith("asyncpg.")):
            raise ImportError("simulated missing asyncpg")
        return real_import(name, globals, locals, fromlist, level)

    monkeypatch.setattr(builtins, "__import__", fake_import)
    with pytest.raises(RuntimeError, match="asyncpg"):
        await sink.connect()
    assert sink.ok is False
    assert "asyncpg" in (sink.last_error or "")


@pytest.mark.asyncio
async def test_postgres_ping_without_pool():
    sink = PostgresSink("postgresql://x")
    assert await sink.ping() is False
