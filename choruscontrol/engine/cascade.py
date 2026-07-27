from __future__ import annotations

import time
import uuid
from typing import Any, Literal

from choruscontrol.adapters.base import CachePort, FabricPort


class InvalidationBroadcaster:
    def __init__(self, fabric: FabricPort, default_threshold: float = 0.55) -> None:
        self.fabric = fabric
        self.default_threshold = default_threshold

    async def broadcast_invalidation(
        self,
        tags: list[str],
        probe_vector: list[float] | None = None,
        mode: Literal["tags", "where"] = "tags",
        threshold: float | None = None,
        correlation_id: str | None = None,
        cascade_id: str | None = None,
        force_refresh: bool = False,
    ) -> dict[str, Any]:
        payload = {
            "event": "INVALIDATE_CACHE",
            "v": 1,
            "correlation_id": correlation_id or str(uuid.uuid4()),
            "cascade_id": cascade_id,
            "tags": tags,
            "probe_vector": probe_vector,
            "threshold": threshold if threshold is not None else self.default_threshold,
            "mode": mode,
            "force_refresh": force_refresh,
            "issued_at": time.time(),
        }
        await self.fabric.broadcast_signal(payload)
        return payload


class CascadeService:
    def __init__(
        self,
        store,
        broadcaster: InvalidationBroadcaster,
        cache: CachePort,
        mark_revalidate,
    ) -> None:
        self.store = store
        self.broadcaster = broadcaster
        self.cache = cache
        self.mark_revalidate = mark_revalidate

    async def run(
        self,
        tenant_id: str,
        tags: list[str],
        probe_vector: list[float] | None = None,
        reason: str = "manual",
    ) -> dict[str, Any]:
        import json

        cascade_id = str(uuid.uuid4())
        now = time.time()
        details = {"reason": reason, "tags": tags, "steps": []}
        await self.store.execute(
            "INSERT INTO cascades(cascade_id, tenant_id, state, details_json, created_at, updated_at) "
            "VALUES(?,?,?,?,?,?)",
            (cascade_id, tenant_id, "running", json.dumps(details), now, now),
        )
        # local eviction (mother demo / colocated)
        n = await self.cache.invalidate_tags(tags)
        details["steps"].append({"step": "local_invalidate_tags", "evicted": n})
        if probe_vector:
            n2 = await self.cache.invalidate_where(probe_vector, 0.55)
            details["steps"].append({"step": "local_invalidate_where", "evicted": n2})
        await self.mark_revalidate(tenant_id, tags)
        details["steps"].append({"step": "mark_revalidate", "ok": True})
        payload = await self.broadcaster.broadcast_invalidation(
            tags=tags,
            probe_vector=probe_vector,
            cascade_id=cascade_id,
            force_refresh=True,
        )
        details["steps"].append({"step": "broadcast", "correlation_id": payload["correlation_id"]})
        await self.store.execute(
            "UPDATE cascades SET state=?, details_json=?, updated_at=? WHERE cascade_id=?",
            ("completed", json.dumps(details), time.time(), cascade_id),
        )
        return {"cascade_id": cascade_id, "details": details, "broadcast": payload}

    async def record_ack(self, cascade_id: str, node_id: str, status: str = "ok") -> None:
        await self.store.execute(
            "INSERT OR REPLACE INTO cascade_acks(cascade_id, node_id, status, received_at) VALUES(?,?,?,?)",
            (cascade_id, node_id, status, time.time()),
        )

    async def consistency_slo(self, cascade_id: str) -> dict[str, Any]:
        """I02 — time until fleet consistent after correction."""
        cascade = await self.store.fetchone("SELECT * FROM cascades WHERE cascade_id=?", (cascade_id,))
        if not cascade:
            return {"error": "not found"}
        acks = await self.store.fetchall(
            "SELECT * FROM cascade_acks WHERE cascade_id=?", (cascade_id,)
        )
        nodes = await self.store.fetchall("SELECT node_id FROM nodes WHERE revoked=0")
        started = cascade["created_at"]
        if not acks:
            return {
                "cascade_id": cascade_id,
                "acked": 0,
                "expected": len(nodes),
                "consistent": False,
                "time_to_consistent_ms": None,
            }
        last = max(a["received_at"] for a in acks)
        return {
            "cascade_id": cascade_id,
            "acked": len(acks),
            "expected": len(nodes),
            "consistent": len(acks) >= len(nodes) and len(nodes) > 0,
            "time_to_consistent_ms": int((last - started) * 1000),
        }
