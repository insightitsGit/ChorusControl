"""Tenant CRUD + max_tenants enforcement."""

from __future__ import annotations

import json
import time
from typing import Any


async def ensure_default_tenant(store) -> None:
    await store.execute(
        "INSERT OR IGNORE INTO tenants(tenant_id, name, created_at, settings_json) VALUES(?,?,?,?)",
        ("default", "Default", time.time(), "{}"),
    )


async def list_tenants(store) -> list[dict[str, Any]]:
    rows = await store.fetchall("SELECT * FROM tenants ORDER BY created_at ASC")
    return [
        {
            "tenant_id": r["tenant_id"],
            "name": r["name"],
            "created_at": r["created_at"],
            "settings": json.loads(r["settings_json"] or "{}"),
        }
        for r in rows
    ]


async def create_tenant(
    store,
    *,
    tenant_id: str,
    name: str,
    settings: dict[str, Any] | None,
    max_tenants: int,
) -> dict[str, Any]:
    count_row = await store.fetchone("SELECT COUNT(*) AS c FROM tenants")
    count = int((count_row or {}).get("c") or 0)
    existing = await store.fetchone("SELECT tenant_id FROM tenants WHERE tenant_id=?", (tenant_id,))
    if existing:
        raise ValueError("tenant already exists")
    if count >= max_tenants:
        raise ValueError("TENANT_LIMIT")
    now = time.time()
    await store.execute(
        "INSERT INTO tenants(tenant_id, name, created_at, settings_json) VALUES(?,?,?,?)",
        (tenant_id, name, now, json.dumps(settings or {})),
    )
    return {"tenant_id": tenant_id, "name": name, "created_at": now, "settings": settings or {}}


async def delete_tenant(store, tenant_id: str) -> None:
    if tenant_id == "default":
        raise ValueError("cannot delete default tenant")
    row = await store.fetchone("SELECT tenant_id FROM tenants WHERE tenant_id=?", (tenant_id,))
    if not row:
        raise ValueError("tenant not found")
    await store.execute("DELETE FROM tenants WHERE tenant_id=?", (tenant_id,))
