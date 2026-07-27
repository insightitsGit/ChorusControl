"""Incident intelligence — graph links, state machine, cascade asset binding."""

from __future__ import annotations

import json
import time
import uuid
from typing import Any

from choruscontrol.services.graph import add_edge, upsert_asset


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
    out = []
    for r in rows:
        links = await store.fetchall(
            "SELECT * FROM incident_assets WHERE incident_id=?", (r["incident_id"],)
        )
        out.append({**r, "details": json.loads(r["details_json"]), "assets": links})
    return out


async def get_incident(store, incident_id: str) -> dict[str, Any] | None:
    row = await store.fetchone("SELECT * FROM incidents WHERE incident_id=?", (incident_id,))
    if not row:
        return None
    links = await store.fetchall(
        "SELECT * FROM incident_assets WHERE incident_id=?", (incident_id,)
    )
    return {**row, "details": json.loads(row["details_json"]), "assets": links}


async def update_incident_state(store, incident_id: str, state: str) -> dict[str, Any] | None:
    allowed = {"open", "investigating", "mitigated", "resolved", "closed"}
    if state not in allowed:
        raise ValueError(f"invalid state {state}; allowed={sorted(allowed)}")
    await store.execute(
        "UPDATE incidents SET state=? WHERE incident_id=?",
        (state, incident_id),
    )
    return await get_incident(store, incident_id)


async def link_incident_asset(store, incident_id: str, asset_id: str, rel: str = "impacted_by") -> None:
    await store.execute(
        "INSERT OR IGNORE INTO incident_assets(incident_id, asset_id, rel) VALUES(?,?,?)",
        (incident_id, asset_id, rel),
    )


async def link_cascade_incident(store, cascade: dict[str, Any], tenant_id: str) -> dict[str, Any]:
    """Open incident + graph assets for cascade blast radius."""
    inc = await create_incident(
        store,
        tenant_id=tenant_id,
        title=f"Correction cascade {cascade.get('cascade_id', '?')}",
        details={"cascade": cascade, "source": "cascade"},
    )
    casc_asset = await upsert_asset(
        store,
        kind="incident",
        tenant_id=tenant_id,
        name=inc["incident_id"],
        meta={"title": inc["title"], "cascade_id": cascade.get("cascade_id")},
    )
    await link_incident_asset(store, inc["incident_id"], casc_asset, "represents")

    tags = cascade.get("tags") or (cascade.get("details") or {}).get("tags") or []
    for tag in tags[:20]:
        kb = await upsert_asset(
            store,
            kind="knowledge_base",
            tenant_id=tenant_id,
            name=str(tag),
            meta={"tag": tag, "source": "cascade"},
        )
        await add_edge(store, casc_asset, kb, "impacted_by")
        await link_incident_asset(store, inc["incident_id"], kb, "impacted_by")

    agents = await store.fetchall(
        "SELECT asset_id FROM assets WHERE kind='agent' AND tenant_id=?",
        (tenant_id,),
    )
    for a in agents[:10]:
        await add_edge(store, casc_asset, a["asset_id"], "impacted_by")
        await link_incident_asset(store, inc["incident_id"], a["asset_id"], "impacted_by")

    return {**inc, "asset_id": casc_asset}


async def incident_intelligence(store, incident_id: str) -> dict[str, Any] | None:
    """Timeline + impact + related assets for ops UI."""
    from choruscontrol.services.graph import blast_radius

    inc = await get_incident(store, incident_id)
    if not inc:
        return None
    related = []
    for link in inc.get("assets") or []:
        br = await blast_radius(store, link["asset_id"])
        related.append({"link": link, "blast_radius": br})
    cascade = (inc.get("details") or {}).get("cascade") or {}
    created = float(inc.get("created_at") or time.time())
    all_snaps = await store.fetchall("SELECT * FROM version_snapshots ORDER BY id DESC LIMIT 20")
    near = [
        {
            "node_id": s["node_id"],
            "day": s["day"],
            "products": json.loads(s["products_json"]),
        }
        for s in all_snaps[:5]
    ]
    return {
        "incident": inc,
        "related": related,
        "suggested_resolution": (
            "Review cascade tags, warm impacted partitions, resolve Cortex conflict if present."
            if cascade
            else "Triage details_json; link related assets; set state to investigating."
        ),
        "version_context": near,
        "created_at": created,
    }
