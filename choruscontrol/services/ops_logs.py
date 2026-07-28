"""Unified ops log bus — searchable history + realtime fan-out for the mother UI."""

from __future__ import annotations

import json
import logging
import time
import uuid
from typing import Any

log = logging.getLogger("choruscontrol.ops_logs")

# Sources we intentionally capture (not full process stdout of every sibling).
KNOWN_SOURCES = frozenset(
    {
        "audit",
        "fleet",
        "ledger",
        "cascade",
        "guard",
        "graph",
        "shine",
        "cortex",
        "taxonomy",
        "agent",
        "system",
        "assistant",
        "incident",
        "license",
    }
)


class OpsLogBus:
    """Persist ops events to SQLite and push to WebSocket subscribers."""

    def __init__(self, store, *, max_retain: int = 5000) -> None:
        self.store = store
        self.max_retain = max_retain
        self.subscribers: list[Any] = []

    async def emit(
        self,
        *,
        source: str,
        message: str,
        level: str = "info",
        tenant_id: str | None = None,
        node_id: str | None = None,
        run_id: str | None = None,
        fields: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        src = (source or "system").strip().lower()[:64]
        if src not in KNOWN_SOURCES:
            src = "system"
        entry = {
            "log_id": str(uuid.uuid4()),
            "ts": time.time(),
            "source": src,
            "level": (level or "info").strip().lower()[:16],
            "tenant_id": (tenant_id or "")[:128] or None,
            "node_id": (node_id or "")[:128] or None,
            "run_id": (run_id or "")[:128] or None,
            "message": (message or "")[:4000],
            "fields": fields or {},
        }
        try:
            await self.store.execute(
                "INSERT INTO ops_logs(log_id, ts, source, level, tenant_id, node_id, run_id, "
                "message, fields_json) VALUES(?,?,?,?,?,?,?,?,?)",
                (
                    entry["log_id"],
                    entry["ts"],
                    entry["source"],
                    entry["level"],
                    entry["tenant_id"],
                    entry["node_id"],
                    entry["run_id"],
                    entry["message"],
                    json.dumps(entry["fields"], default=str),
                ),
            )
            # Best-effort retention trim
            count_row = await self.store.fetchone("SELECT COUNT(*) AS c FROM ops_logs")
            if count_row and int(count_row.get("c") or 0) > self.max_retain:
                await self.store.execute(
                    "DELETE FROM ops_logs WHERE id IN ("
                    "SELECT id FROM ops_logs ORDER BY id ASC LIMIT ?"
                    ")",
                    (max(100, int(count_row["c"]) - self.max_retain),),
                )
        except Exception as exc:  # noqa: BLE001
            log.warning("ops_logs persist failed: %s", exc)
        await self._broadcast({"type": "log", "entry": entry})
        return entry

    async def search(
        self,
        *,
        q: str | None = None,
        source: str | None = None,
        level: str | None = None,
        tenant_id: str | None = None,
        node_id: str | None = None,
        since: float | None = None,
        limit: int = 100,
    ) -> list[dict[str, Any]]:
        clauses: list[str] = []
        params: list[Any] = []
        if q:
            clauses.append("(message LIKE ? OR fields_json LIKE ? OR run_id LIKE ?)")
            like = f"%{q}%"
            params.extend([like, like, like])
        if source:
            clauses.append("source=?")
            params.append(source.strip().lower())
        if level:
            clauses.append("level=?")
            params.append(level.strip().lower())
        if tenant_id:
            clauses.append("tenant_id=?")
            params.append(tenant_id)
        if node_id:
            clauses.append("node_id=?")
            params.append(node_id)
        if since is not None:
            clauses.append("ts>=?")
            params.append(float(since))
        where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
        lim = max(1, min(int(limit or 100), 500))
        rows = await self.store.fetchall(
            f"SELECT * FROM ops_logs{where} ORDER BY ts DESC LIMIT ?",
            tuple(params + [lim]),
        )
        out = []
        for r in rows:
            fields = {}
            try:
                fields = json.loads(r.get("fields_json") or "{}")
            except Exception:  # noqa: BLE001
                fields = {}
            out.append(
                {
                    "log_id": r["log_id"],
                    "ts": r["ts"],
                    "source": r["source"],
                    "level": r["level"],
                    "tenant_id": r.get("tenant_id"),
                    "node_id": r.get("node_id"),
                    "run_id": r.get("run_id"),
                    "message": r["message"],
                    "fields": fields,
                }
            )
        return out

    async def _broadcast(self, event: dict[str, Any]) -> None:
        dead = []
        for ws in list(self.subscribers):
            try:
                await ws.send_json(event)
            except Exception:  # noqa: BLE001
                dead.append(ws)
        for ws in dead:
            if ws in self.subscribers:
                self.subscribers.remove(ws)


async def emit_ops(state, **kwargs: Any) -> dict[str, Any] | None:
    bus = getattr(state, "ops_logs", None)
    if bus is None:
        return None
    return await bus.emit(**kwargs)
