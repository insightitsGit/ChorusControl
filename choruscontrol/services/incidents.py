"""Incident intelligence — Guard/cascade linked incidents."""

from __future__ import annotations

import json
import time
import uuid
from typing import Any


async def create_incident(
    store,
    *,
    tenant_id: str,
    title: str,
    details: dict[str, Any],
    state: str = "open",
) -> dict[str, Any]:
    incident_id = f"inc-{uuid.uuid4().hex[:10]}"
    await store.execute(
        "INSERT INTO incidents(incident_id, tenant_id, title, state, details_json, created_at) "
        "VALUES(?,?,?,?,?,?)",
        (incident_id, tenant_id, title, state, json.dumps(details), time.time()),
    )
    return {
        "incident_id": incident_id,
        "tenant_id": tenant_id,
        "title": title,
        "state": state,
        "details": details,
    }


async def list_incidents(store, tenant_id: str | None = None, limit: int = 50) -> list[dict[str, Any]]:
    if tenant_id:
        rows = await store.fetchall(
            "SELECT * FROM incidents WHERE tenant_id=? ORDER BY created_at DESC LIMIT ?",
            (tenant_id, limit),
        )
    else:
        rows = await store.fetchall(
            "SELECT * FROM incidents ORDER BY created_at DESC LIMIT ?", (limit,)
        )
    return [{**r, "details": json.loads(r["details_json"])} for r in rows]


async def get_incident(store, incident_id: str) -> dict[str, Any] | None:
    row = await store.fetchone("SELECT * FROM incidents WHERE incident_id=?", (incident_id,))
    if not row:
        return None
    return {**row, "details": json.loads(row["details_json"])}


async def link_cascade_incident(store, cascade: dict[str, Any], tenant_id: str) -> dict[str, Any]:
    return await create_incident(
        store,
        tenant_id=tenant_id,
        title=f"Correction cascade {cascade.get('cascade_id', '?')}",
        details={"cascade": cascade, "source": "cascade"},
    )
