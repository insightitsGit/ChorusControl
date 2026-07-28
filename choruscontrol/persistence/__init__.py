from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator

import aiosqlite

SCHEMA = """
CREATE TABLE IF NOT EXISTS tenants (
  tenant_id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  created_at REAL NOT NULL,
  settings_json TEXT NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS join_tokens (
  token TEXT PRIMARY KEY,
  max_uses INTEGER NOT NULL,
  uses INTEGER NOT NULL DEFAULT 0,
  expires_at REAL NOT NULL,
  zone TEXT,
  node_id_bind TEXT,
  created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS nodes (
  node_id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  role TEXT NOT NULL,
  network_zone TEXT NOT NULL,
  products_json TEXT NOT NULL,
  caps_digest TEXT,
  last_seen REAL NOT NULL,
  memory_endpoint TEXT,
  session_secret TEXT,
  revoked INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS cascades (
  cascade_id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  state TEXT NOT NULL,
  details_json TEXT NOT NULL,
  created_at REAL NOT NULL,
  updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS cascade_acks (
  cascade_id TEXT NOT NULL,
  node_id TEXT NOT NULL,
  status TEXT NOT NULL,
  received_at REAL NOT NULL,
  PRIMARY KEY (cascade_id, node_id)
);

CREATE TABLE IF NOT EXISTS version_snapshots (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  node_id TEXT NOT NULL,
  day TEXT NOT NULL,
  products_json TEXT NOT NULL,
  caps_digest TEXT,
  UNIQUE(node_id, day)
);

CREATE TABLE IF NOT EXISTS assets (
  asset_id TEXT PRIMARY KEY,
  kind TEXT NOT NULL,
  tenant_id TEXT NOT NULL,
  name TEXT NOT NULL,
  meta_json TEXT NOT NULL,
  updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS asset_edges (
  src TEXT NOT NULL,
  dst TEXT NOT NULL,
  rel TEXT NOT NULL,
  PRIMARY KEY (src, dst, rel)
);

CREATE TABLE IF NOT EXISTS ledger_entries (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id TEXT NOT NULL,
  node_id TEXT NOT NULL,
  run_id TEXT,
  payload_json TEXT NOT NULL,
  sampled INTEGER NOT NULL DEFAULT 0,
  created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS incidents (
  incident_id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  title TEXT NOT NULL,
  state TEXT NOT NULL,
  details_json TEXT NOT NULL,
  created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS guard_policies (
  tenant_id TEXT PRIMARY KEY,
  policy_json TEXT NOT NULL,
  updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS guard_lexicons (
  tenant_id TEXT PRIMARY KEY,
  terms_json TEXT NOT NULL,
  updated_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS traces (
  run_id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  wire_json TEXT NOT NULL,
  created_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS metric_samples (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  ts REAL NOT NULL,
  name TEXT NOT NULL,
  value REAL NOT NULL,
  labels_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS metric_samples_name_ts ON metric_samples(name, ts DESC);

CREATE TABLE IF NOT EXISTS asset_versions (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  asset_id TEXT NOT NULL,
  version TEXT NOT NULL,
  meta_json TEXT NOT NULL,
  created_at REAL NOT NULL
);
CREATE INDEX IF NOT EXISTS asset_versions_asset ON asset_versions(asset_id, created_at DESC);

CREATE TABLE IF NOT EXISTS incident_assets (
  incident_id TEXT NOT NULL,
  asset_id TEXT NOT NULL,
  rel TEXT NOT NULL DEFAULT 'impacted_by',
  PRIMARY KEY (incident_id, asset_id, rel)
);

CREATE TABLE IF NOT EXISTS enterprise_policies (
  policy_id TEXT PRIMARY KEY,
  domain TEXT NOT NULL,
  tenant_id TEXT NOT NULL,
  name TEXT NOT NULL,
  body_json TEXT NOT NULL,
  version INTEGER NOT NULL DEFAULT 1,
  updated_at REAL NOT NULL,
  UNIQUE(domain, tenant_id, name)
);

CREATE TABLE IF NOT EXISTS compliance_findings (
  finding_id TEXT PRIMARY KEY,
  severity TEXT NOT NULL,
  code TEXT NOT NULL,
  title TEXT NOT NULL,
  detail_json TEXT NOT NULL,
  created_at REAL NOT NULL,
  resolved INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS deployment_snapshots (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  tenant_id TEXT NOT NULL,
  day TEXT NOT NULL,
  policy_hash TEXT,
  policy_json TEXT,
  partitions_json TEXT,
  products_json TEXT,
  UNIQUE(tenant_id, day)
);

CREATE TABLE IF NOT EXISTS ops_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  log_id TEXT NOT NULL UNIQUE,
  ts REAL NOT NULL,
  source TEXT NOT NULL,
  level TEXT NOT NULL,
  tenant_id TEXT,
  node_id TEXT,
  run_id TEXT,
  message TEXT NOT NULL,
  fields_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS ops_logs_ts ON ops_logs(ts DESC);
CREATE INDEX IF NOT EXISTS ops_logs_source_ts ON ops_logs(source, ts DESC);
CREATE INDEX IF NOT EXISTS ops_logs_tenant_ts ON ops_logs(tenant_id, ts DESC);

CREATE TABLE IF NOT EXISTS client_chat_sessions (
  session_id TEXT PRIMARY KEY,
  tenant_id TEXT NOT NULL,
  node_id TEXT,
  user_ref TEXT,
  channel TEXT NOT NULL DEFAULT 'end_user',
  title TEXT,
  message_count INTEGER NOT NULL DEFAULT 0,
  started_at REAL NOT NULL,
  last_at REAL NOT NULL,
  compact_status TEXT NOT NULL DEFAULT 'raw',
  summary TEXT,
  cortex_digest_ref TEXT,
  meta_json TEXT NOT NULL DEFAULT '{}'
);
CREATE INDEX IF NOT EXISTS client_chat_sessions_tenant_last
  ON client_chat_sessions(tenant_id, last_at DESC);

CREATE TABLE IF NOT EXISTS client_chat_messages (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  message_id TEXT NOT NULL UNIQUE,
  session_id TEXT NOT NULL,
  role TEXT NOT NULL,
  content TEXT NOT NULL,
  ts REAL NOT NULL,
  pruned INTEGER NOT NULL DEFAULT 0,
  meta_json TEXT NOT NULL DEFAULT '{}',
  FOREIGN KEY(session_id) REFERENCES client_chat_sessions(session_id)
);
CREATE INDEX IF NOT EXISTS client_chat_messages_session_ts
  ON client_chat_messages(session_id, ts ASC);
"""


class Store:
    def __init__(self, sqlite_path: Path) -> None:
        self.sqlite_path = sqlite_path
        self._lock = asyncio.Lock()

    async def connect(self) -> aiosqlite.Connection:
        self.sqlite_path.parent.mkdir(parents=True, exist_ok=True)
        db = await aiosqlite.connect(self.sqlite_path)
        db.row_factory = aiosqlite.Row
        await db.execute("PRAGMA journal_mode=WAL;")
        await db.execute("PRAGMA synchronous=NORMAL;")
        await db.executescript(SCHEMA)
        await db.commit()
        return db

    @asynccontextmanager
    async def session(self) -> AsyncIterator[aiosqlite.Connection]:
        async with self._lock:
            db = await self.connect()
            try:
                yield db
                await db.commit()
            finally:
                await db.close()

    async def execute(self, sql: str, params: tuple[Any, ...] = ()) -> None:
        async with self.session() as db:
            await db.execute(sql, params)

    async def fetchone(self, sql: str, params: tuple[Any, ...] = ()) -> dict[str, Any] | None:
        async with self.session() as db:
            cur = await db.execute(sql, params)
            row = await cur.fetchone()
            return dict(row) if row else None

    async def fetchall(self, sql: str, params: tuple[Any, ...] = ()) -> list[dict[str, Any]]:
        async with self.session() as db:
            cur = await db.execute(sql, params)
            rows = await cur.fetchall()
            return [dict(r) for r in rows]
