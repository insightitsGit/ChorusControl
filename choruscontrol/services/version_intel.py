"""Version intelligence — deployment snapshots + day-over-day diffs."""

from __future__ import annotations

import hashlib
import json
import time
from typing import Any


def _hash_obj(obj: Any) -> str:
    raw = json.dumps(obj, sort_keys=True, default=str)
    return hashlib.sha256(raw.encode()).hexdigest()[:16]


async def record_deployment_snapshot(state, tenant_id: str = "default") -> dict[str, Any]:
    day = time.strftime("%Y-%m-%d", time.gmtime())
    pol = state.intended_policies.get(tenant_id) or state.intended_policies.get("default") or {}
    partitions: list[Any] = []
    try:
        partitions = await state.rag.partitions(tenant_id)
    except Exception:  # noqa: BLE001
        partitions = []
    nodes = await state.fleet.list_nodes()
    products = {
        n["node_id"]: n.get("products") or {}
        for n in nodes
        if n.get("tenant_id") == tenant_id or tenant_id == "default"
    }
    policy_hash = _hash_obj(pol)
    await state.store.execute(
        "INSERT INTO deployment_snapshots(tenant_id, day, policy_hash, policy_json, partitions_json, products_json) "
        "VALUES(?,?,?,?,?,?) "
        "ON CONFLICT(tenant_id, day) DO UPDATE SET policy_hash=excluded.policy_hash, "
        "policy_json=excluded.policy_json, partitions_json=excluded.partitions_json, "
        "products_json=excluded.products_json",
        (
            tenant_id,
            day,
            policy_hash,
            json.dumps(pol),
            json.dumps(partitions),
            json.dumps(products),
        ),
    )
    return {"tenant_id": tenant_id, "day": day, "policy_hash": policy_hash}


async def version_diff(
    store,
    *,
    node_id: str | None = None,
    tenant_id: str = "default",
    day_a: str | None = None,
    day_b: str | None = None,
) -> dict[str, Any]:
    """Compare two days of node product snapshots and/or tenant deployment snapshots."""
    if node_id:
        rows = await store.fetchall(
            "SELECT * FROM version_snapshots WHERE node_id=? ORDER BY day DESC LIMIT 30",
            (node_id,),
        )
        if len(rows) < 2 and not (day_a and day_b):
            return {
                "node_id": node_id,
                "days": [r["day"] for r in rows],
                "diff": {},
                "note": "need at least two snapshot days",
            }
        by_day = {r["day"]: r for r in rows}
        if day_a and day_b:
            a, b = by_day.get(day_a), by_day.get(day_b)
        else:
            b, a = rows[0], rows[1]
        if not a or not b:
            return {"error": "day_not_found", "available": list(by_day)}
        pa, pb = json.loads(a["products_json"]), json.loads(b["products_json"])
        keys = sorted(set(pa) | set(pb))
        changed = {k: {"before": pa.get(k), "after": pb.get(k)} for k in keys if pa.get(k) != pb.get(k)}
        return {
            "node_id": node_id,
            "day_a": a["day"],
            "day_b": b["day"],
            "products_diff": changed,
            "caps_digest": {"before": a.get("caps_digest"), "after": b.get("caps_digest")},
        }

    rows = await store.fetchall(
        "SELECT * FROM deployment_snapshots WHERE tenant_id=? ORDER BY day DESC LIMIT 30",
        (tenant_id,),
    )
    if len(rows) < 2 and not (day_a and day_b):
        return {
            "tenant_id": tenant_id,
            "days": [r["day"] for r in rows],
            "diff": {},
            "note": "need at least two deployment snapshot days",
        }
    by_day = {r["day"]: r for r in rows}
    if day_a and day_b:
        a, b = by_day.get(day_a), by_day.get(day_b)
    else:
        b, a = rows[0], rows[1]
    if not a or not b:
        return {"error": "day_not_found", "available": list(by_day)}
    pa = json.loads(a["policy_json"] or "{}")
    pb = json.loads(b["policy_json"] or "{}")
    part_a = json.loads(a["partitions_json"] or "[]")
    part_b = json.loads(b["partitions_json"] or "[]")
    prod_a = json.loads(a["products_json"] or "{}")
    prod_b = json.loads(b["products_json"] or "{}")
    return {
        "tenant_id": tenant_id,
        "day_a": a["day"],
        "day_b": b["day"],
        "policy_hash": {"before": a.get("policy_hash"), "after": b.get("policy_hash")},
        "policy_changed": pa != pb,
        "policy_before": pa,
        "policy_after": pb,
        "partitions_before": part_a,
        "partitions_after": part_b,
        "products_before": prod_a,
        "products_after": prod_b,
    }
