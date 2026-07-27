"""Optional Postgres: audit sink + control-plane durability (R05).

When DATABASE_URL is set, mother dual-writes registry/cascade/join-token state and
can restore into SQLite on boot if the local DB is empty. HA story: shared Postgres
+ single active mother (no fake multi-primary).
"""

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

CONTROL_DDL = """
CREATE TABLE IF NOT EXISTS join_tokens (
  token TEXT PRIMARY KEY,
  max_uses INTEGER NOT NULL,
  uses INTEGER NOT NULL DEFAULT 0,
  expires_at DOUBLE PRECISION NOT NULL,
  zone TEXT,
  node_id_bind TEXT,
  created_at DOUBLE PRECISION NOT NULL
);

CREATE TABLE IF NOT EXISTS nodes (
  node_id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  role TEXT NOT NULL,
  network_zone TEXT NOT NULL,
  products_json TEXT NOT NULL,
  caps_digest TEXT,
  last_seen DOUBLE PRECISION NOT NULL,
  memory_endpoint TEXT,
  session_secret TEXT,
  revoked INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS cascades (
  cascade_id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  state TEXT NOT NULL,
  details_json TEXT NOT NULL,
  created_at DOUBLE PRECISION NOT NULL,
  updated_at DOUBLE PRECISION NOT NULL
);

CREATE TABLE IF NOT EXISTS cascade_acks (
  cascade_id TEXT NOT NULL,
  node_id TEXT NOT NULL,
  status TEXT NOT NULL,
  received_at DOUBLE PRECISION NOT NULL,
  PRIMARY KEY (cascade_id, node_id)
);

CREATE TABLE IF NOT EXISTS assets (
  asset_id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  tenant_id TEXT NOT NULL,
  name TEXT NOT NULL,
  meta_json TEXT NOT NULL,
  updated_at DOUBLE PRECISION NOT NULL
);

CREATE TABLE IF NOT EXISTS asset_edges (
  src TEXT NOT NULL,
  dst TEXT NOT NULL,
  rel TEXT NOT NULL,
  PRIMARY KEY (src, dst, rel)
);
"""


class PostgresSink:
    def __init__(self, database_url: str) -> None:
        self.database_url = database_url
        self._pool: Any = None
        self.ok = False
        self.last_error: str | None = None
        self.control_plane = False

    async def connect(self) -> None:
        try:
            import asyncpg
        except ImportError as exc:
            self.last_error = "asyncpg not installed; pip install choruscontrol[postgres]"
            raise RuntimeError(self.last_error) from exc
        self._pool = await asyncpg.create_pool(self.database_url, min_size=1, max_size=5)
        async with self._pool.acquire() as conn:
            await conn.execute(AUDIT_DDL)
            await conn.execute(CONTROL_DDL)
        self.ok = True
        self.control_plane = True
        self.last_error = None
        log.info("postgres audit + control-plane sink connected")

    async def close(self) -> None:
        if self._pool:
            await self._pool.close()
            self._pool = None
        self.ok = False
        self.control_plane = False

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

    async def upsert_join_token(self, row: dict[str, Any]) -> None:
        if not self._pool:
            return
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO join_tokens(token, max_uses, uses, expires_at, zone, node_id_bind, created_at)
                VALUES($1,$2,$3,$4,$5,$6,$7)
                ON CONFLICT (token) DO UPDATE SET
                  max_uses=EXCLUDED.max_uses, uses=EXCLUDED.uses, expires_at=EXCLUDED.expires_at,
                  zone=EXCLUDED.zone, node_id_bind=EXCLUDED.node_id_bind
                """,
                row["token"],
                int(row["max_uses"]),
                int(row.get("uses") or 0),
                float(row["expires_at"]),
                row.get("zone"),
                row.get("node_id_bind"),
                float(row["created_at"]),
            )

    async def upsert_node(self, row: dict[str, Any]) -> None:
        if not self._pool:
            return
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO nodes(node_id, tenant_id, role, network_zone, products_json, caps_digest,
                  last_seen, memory_endpoint, session_secret, revoked)
                VALUES($1,$2,$3,$4,$5,$6,$7,$8,$9,$10)
                ON CONFLICT (node_id) DO UPDATE SET
                  tenant_id=EXCLUDED.tenant_id, role=EXCLUDED.role, network_zone=EXCLUDED.network_zone,
                  products_json=EXCLUDED.products_json, caps_digest=EXCLUDED.caps_digest,
                  last_seen=EXCLUDED.last_seen, memory_endpoint=EXCLUDED.memory_endpoint,
                  session_secret=EXCLUDED.session_secret, revoked=EXCLUDED.revoked
                """,
                row["node_id"],
                row["tenant_id"],
                row["role"],
                row["network_zone"],
                row["products_json"] if isinstance(row["products_json"], str) else json.dumps(row["products_json"]),
                row.get("caps_digest"),
                float(row["last_seen"]),
                row.get("memory_endpoint"),
                row.get("session_secret"),
                int(row.get("revoked") or 0),
            )

    async def upsert_cascade(self, row: dict[str, Any]) -> None:
        if not self._pool:
            return
        details = row.get("details_json")
        if not isinstance(details, str):
            details = json.dumps(details or {})
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO cascades(cascade_id, tenant_id, state, details_json, created_at, updated_at)
                VALUES($1,$2,$3,$4,$5,$6)
                ON CONFLICT (cascade_id) DO UPDATE SET
                  state=EXCLUDED.state, details_json=EXCLUDED.details_json, updated_at=EXCLUDED.updated_at
                """,
                row["cascade_id"],
                row["tenant_id"],
                row["state"],
                details,
                float(row["created_at"]),
                float(row["updated_at"]),
            )

    async def upsert_cascade_ack(self, cascade_id: str, node_id: str, status: str, received_at: float) -> None:
        if not self._pool:
            return
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO cascade_acks(cascade_id, node_id, status, received_at)
                VALUES($1,$2,$3,$4)
                ON CONFLICT (cascade_id, node_id) DO UPDATE SET
                  status=EXCLUDED.status, received_at=EXCLUDED.received_at
                """,
                cascade_id,
                node_id,
                status,
                float(received_at),
            )

    async def upsert_asset(self, row: dict[str, Any]) -> None:
        if not self._pool:
            return
        meta = row.get("meta_json")
        if not isinstance(meta, str):
            meta = json.dumps(meta or {})
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO assets(asset_id, kind, tenant_id, name, meta_json, updated_at)
                VALUES($1,$2,$3,$4,$5,$6)
                ON CONFLICT (asset_id) DO UPDATE SET
                  meta_json=EXCLUDED.meta_json, updated_at=EXCLUDED.updated_at, name=EXCLUDED.name
                """,
                row["asset_id"],
                row["kind"],
                row["tenant_id"],
                row["name"],
                meta,
                float(row["updated_at"]),
            )

    async def upsert_edge(self, src: str, dst: str, rel: str) -> None:
        if not self._pool:
            return
        async with self._pool.acquire() as conn:
            await conn.execute(
                """
                INSERT INTO asset_edges(src, dst, rel) VALUES($1,$2,$3)
                ON CONFLICT (src, dst, rel) DO NOTHING
                """,
                src,
                dst,
                rel,
            )

    async def restore_control_plane_into_sqlite(self, store) -> dict[str, int]:
        """If SQLite has no nodes, hydrate registry/cascade from Postgres."""
        if not self._pool:
            return {"restored": 0}
        existing = await store.fetchone("SELECT COUNT(*) AS c FROM nodes")
        if int((existing or {}).get("c") or 0) > 0:
            return {"restored": 0, "skipped": "sqlite_has_nodes"}
        counts = {"nodes": 0, "join_tokens": 0, "cascades": 0, "cascade_acks": 0, "assets": 0, "edges": 0}
        async with self._pool.acquire() as conn:
            for table, cols in (
                (
                    "join_tokens",
                    "token, max_uses, uses, expires_at, zone, node_id_bind, created_at",
                ),
                (
                    "nodes",
                    "node_id, tenant_id, role, network_zone, products_json, caps_digest, "
                    "last_seen, memory_endpoint, session_secret, revoked",
                ),
                ("cascades", "cascade_id, tenant_id, state, details_json, created_at, updated_at"),
                ("cascade_acks", "cascade_id, node_id, status, received_at"),
                ("assets", "asset_id, kind, tenant_id, name, meta_json, updated_at"),
                ("asset_edges", "src, dst, rel"),
            ):
                rows = await conn.fetch(f"SELECT {cols} FROM {table}")
                key = {
                    "join_tokens": "join_tokens",
                    "nodes": "nodes",
                    "cascades": "cascades",
                    "cascade_acks": "cascade_acks",
                    "assets": "assets",
                    "asset_edges": "edges",
                }[table]
                col_list = [c.strip() for c in cols.split(",")]
                ph = ",".join("?" * len(col_list))
                for r in rows:
                    vals = tuple(r[c] for c in col_list)
                    await store.execute(
                        f"INSERT OR REPLACE INTO {table}({cols}) VALUES({ph})",
                        vals,
                    )
                    counts[key] += 1
        log.info("restored control plane from postgres: %s", counts)
        return {"restored": 1, **counts}
