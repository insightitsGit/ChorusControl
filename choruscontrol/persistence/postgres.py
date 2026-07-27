"""Optional Postgres dual-write for audit (and health ping)."""

from __future__ import annotations

import json
import logging
from typing import Any

log = logging.getLogger("choruscontrol.postgres")

AUDIT_DDL = """
CREATE TABLE IF NOT EXISTS audit_events (
  event_id TEXT PRIMARY KEY,
  ts DOUBLE PRECISION NOT NULL,
  admin_user TEXT NOT NULL,
  action TEXT NOT NULL,
  tenant_id TEXT NOT NULL,
  kid TEXT,
  details_json JSONB NOT NULL,
  signature TEXT NOT NULL,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);
CREATE INDEX IF NOT EXISTS audit_events_ts_idx ON audit_events (ts DESC);
CREATE INDEX IF NOT EXISTS audit_events_tenant_idx ON audit_events (tenant_id);
"""


class PostgresSink:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        self._pool: Any = None
        self.ok = False
        self.last_error: str | None = None

    async def connect(self) -> None:
        try:
            import asyncpg
        except ImportError as exc:
            self.last_error = "asyncpg not installed; pip install choruscontrol[postgres]"
            raise RuntimeError(self.last_error) from exc
        self._pool = await asyncpg.create_pool(self.database_url, min_size=1, max_size=5)
        async with self._pool.acquire() as conn:
            await conn.execute(AUDIT_DDL)
        self.ok = True
        self.last_error = None
        log.info("postgres audit sink connected")

    async def close(self) -> None:
        if self._pool:
            await self._pool.close()
            self._pool = None
        self.ok = False

    async def ping(self) -> bool:
        if not self._pool:
            return False
        try:
            async with self._pool.acquire() as conn:
                await conn.fetchval("SELECT 1")
            self.ok = True
            self.last_error = None
            return True
        except Exception as exc:  # noqa: BLE001
            self.ok = False
            self.last_error = str(exc)
            return False

    async def write_audit(self, envelope: dict[str, Any]) -> None:
        if not self._pool:
            return
        details = envelope.get("details") or {}
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO audit_events(event_id, ts, admin_user, action, tenant_id, kid, details_json, signature)
                VALUES($1,$2,$3,$4,$5,$6,$7::jsonb,$8)
                ON CONFLICT (event_id) DO NOTHING
                """,
                envelope.get("event_id"),
                float(envelope.get("timestamp") or 0),
                envelope.get("admin_user") or "",
                envelope.get("action") or "",
                envelope.get("tenant_id") or "",
                envelope.get("kid"),
                json.dumps(details),
                envelope.get("signature") or "",
            )
