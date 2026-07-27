from __future__ import annotations

import json
import time
from typing import Any


async def upsert_asset(store, *, kind: str, tenant_id: str, name: str, meta: dict[str, Any]) -> str:
    asset_id = f"{kind}:{tenant_id}:{name}"
    now = time.time()
    prev = await store.fetchone("SELECT meta_json FROM assets WHERE asset_id=?", (asset_id,))
    await store.execute(
        "INSERT INTO assets(asset_id, kind, tenant_id, name, meta_json, updated_at) VALUES(?,?,?,?,?,?) "
        "ON CONFLICT(asset_id) DO UPDATE SET meta_json=excluded.meta_json, updated_at=excluded.updated_at",
        (asset_id, kind, tenant_id, name, json.dumps(meta), now),
    )
    # Version history when meta changes
    if not prev or prev["meta_json"] != json.dumps(meta):
        version = time.strftime("%Y%m%dT%H%M%SZ", time.gmtime(now))
        await store.execute(
            "INSERT INTO asset_versions(asset_id, version, meta_json, created_at) VALUES(?,?,?,?)",
            (asset_id, version, json.dumps(meta), now),
        )
    pg = getattr(store, "postgres", None)
    if pg is not None and getattr(pg, "control_plane", False):
        try:
            await pg.upsert_asset(
                {
                    "asset_id": asset_id,
                    "kind": kind,
                    "tenant_id": tenant_id,
                    "name": name,
                    "meta_json": json.dumps(meta),
                    "updated_at": now,
                }
            )
        except Exception:  # noqa: BLE001
            pass
    return asset_id


async def add_edge(store, src: str, dst: str, rel: str) -> None:
    await store.execute(
        "INSERT OR IGNORE INTO asset_edges(src, dst, rel) VALUES(?,?,?)",
        (src, dst, rel),
    )
    pg = getattr(store, "postgres", None)
    if pg is not None and getattr(pg, "control_plane", False):
        try:
            await pg.upsert_edge(src, dst, rel)
        except Exception:  # noqa: BLE001
            pass


async def sync_from_fleet(state) -> dict[str, Any]:
    """Asset Graph v1 — fleet + tenants + policies + partitions + memory + incidents."""
    # Attach postgres for dual-write helpers
    if state.postgres is not None:
        state.store.postgres = state.postgres

    org = await upsert_asset(
        state.store,
        kind="organization",
        tenant_id="*",
        name=state.license_status.claims.sub if state.license_status.claims else "unknown",
        meta={"tier": state.license_status.claims.tier if state.license_status.claims else None},
    )

    tenants = await state.store.fetchall("SELECT * FROM tenants")
    for t in tenants:
        tid = await upsert_asset(
            state.store,
            kind="tenant",
            tenant_id=t["tenant_id"],
            name=t["tenant_id"],
            meta={"name": t.get("name")},
        )
        await add_edge(state.store, org, tid, "contains")

    nodes = await state.fleet.list_nodes()
    created = 0
    for n in nodes:
        agent_id = await upsert_asset(
            state.store,
            kind="agent",
            tenant_id=n["tenant_id"],
            name=n["node_id"],
            meta={
                "role": n["role"],
                "zone": n["network_zone"],
                "products": n["products"],
                "memory_endpoint": n.get("memory_endpoint"),
            },
        )
        await add_edge(state.store, org, agent_id, "contains")
        tenant_asset = f"tenant:{n['tenant_id']}:{n['tenant_id']}"
        await add_edge(state.store, tenant_asset, agent_id, "runs")
        for prod, ver in (n["products"] or {}).items():
            pid = await upsert_asset(
                state.store,
                kind="product",
                tenant_id=n["tenant_id"],
                name=f"{n['node_id']}/{prod}",
                meta={"version": ver},
            )
            await add_edge(state.store, agent_id, pid, "runs")
            created += 1
        if n.get("memory_endpoint"):
            mem = await upsert_asset(
                state.store,
                kind="memory",
                tenant_id=n["tenant_id"],
                name=n["node_id"],
                meta={"endpoint": n["memory_endpoint"], "role": n.get("role")},
            )
            await add_edge(state.store, agent_id, mem, "uses")
        pol = state.intended_policies.get(n["tenant_id"]) or state.intended_policies.get("default")
        if pol:
            policy_id = await upsert_asset(
                state.store,
                kind="policy",
                tenant_id=n["tenant_id"],
                name="guard",
                meta=pol,
            )
            await add_edge(state.store, agent_id, policy_id, "governed_by")
        try:
            parts = await state.rag.partitions(n["tenant_id"])
            for p in parts:
                kid = await upsert_asset(
                    state.store,
                    kind="knowledge_base",
                    tenant_id=n["tenant_id"],
                    name=p.get("partition", "kb"),
                    meta=p,
                )
                await add_edge(state.store, agent_id, kid, "uses")
                await add_edge(state.store, kid, agent_id, "depends_on")
        except Exception:  # noqa: BLE001
            pass

    # Link open incidents into graph
    incidents = await state.store.fetchall(
        "SELECT * FROM incidents WHERE state IN ('open','investigating') ORDER BY created_at DESC LIMIT 50"
    )
    for inc in incidents:
        iid = await upsert_asset(
            state.store,
            kind="incident",
            tenant_id=inc["tenant_id"],
            name=inc["incident_id"],
            meta={"title": inc["title"], "state": inc["state"]},
        )
        await add_edge(state.store, org, iid, "contains")

    return {
        "organization": org,
        "agents": len(nodes),
        "tenants": len(tenants),
        "product_assets": created,
        "incidents": len(incidents),
    }


async def graph_query(store, tenant_id: str | None = None) -> dict[str, Any]:
    if tenant_id:
        assets = await store.fetchall(
            "SELECT * FROM assets WHERE tenant_id=? OR tenant_id='*'", (tenant_id,)
        )
    else:
        assets = await store.fetchall("SELECT * FROM assets")
    edges = await store.fetchall("SELECT * FROM asset_edges")
    return {
        "assets": [{**a, "meta": json.loads(a["meta_json"])} for a in assets],
        "edges": edges,
    }


async def blast_radius(store, asset_id: str) -> dict[str, Any]:
    """What depends on this asset / what it impacts."""
    outbound = await store.fetchall(
        "SELECT * FROM asset_edges WHERE src=?", (asset_id,)
    )
    inbound = await store.fetchall(
        "SELECT * FROM asset_edges WHERE dst=?", (asset_id,)
    )
    related_ids = {asset_id}
    for e in outbound + inbound:
        related_ids.add(e["src"])
        related_ids.add(e["dst"])
    assets = []
    for aid in related_ids:
        row = await store.fetchone("SELECT * FROM assets WHERE asset_id=?", (aid,))
        if row:
            assets.append({**row, "meta": json.loads(row["meta_json"])})
    return {
        "asset_id": asset_id,
        "depends_on": [e for e in outbound if e["rel"] in ("depends_on", "uses", "runs")],
        "impacted_by": inbound,
        "impacts": outbound,
        "assets": assets,
    }


async def assistant_ask(
    state,
    question: str,
    principal_user: str,
    *,
    confirm: bool = False,
    execute: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Ops Assistant — delegates to dashboard-literate assistant service."""
    from choruscontrol.services.assistant import assistant_ask as _ask

    return await _ask(
        state, question, principal_user, confirm=confirm, execute=execute
    )


async def recommendations(state) -> dict[str, Any]:
    """Predictive + RCA recommendations from retained metric samples."""
    from choruscontrol.services.metrics import predictive_recommendations

    return await predictive_recommendations(state)
