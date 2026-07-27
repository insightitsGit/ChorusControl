"""Optional live Prism adapters — try-import at pin floors; never hard-require siblings."""

from __future__ import annotations

import logging
from typing import Any

from choruscontrol.adapters.pins import package_ready

log = logging.getLogger("choruscontrol.adapters.live")


class LiveCache:
    def __init__(self, backend: Any) -> None:
        self._b = backend

    async def get_metrics(self) -> dict[str, Any]:
        if hasattr(self._b, "get_metrics"):
            m = self._b.get_metrics()
            if hasattr(m, "__await__"):
                m = await m
            out = dict(m) if isinstance(m, dict) else {"raw": m}
            out["demo"] = False
            return out
        return {
            "hit_rate": 0.0,
            "tokens_saved": 0,
            "cost_saved_usd": 0,
            "demo": False,
            "note": "no get_metrics",
        }

    async def invalidate_tags(self, tags: list[str]) -> int:
        fn = getattr(self._b, "invalidate_tags", None) or getattr(self._b, "evict_tags", None)
        if fn is None:
            return 0
        r = fn(tags)
        if hasattr(r, "__await__"):
            r = await r
        return int(r or 0)

    async def invalidate_where(self, probe: list[float], threshold: float) -> int:
        fn = getattr(self._b, "invalidate_where", None)
        if fn is None:
            return 0
        r = fn(probe, threshold)
        if hasattr(r, "__await__"):
            r = await r
        return int(r or 0)


class LiveGuard:
    def __init__(self, backend: Any) -> None:
        self._b = backend

    async def caps(self, profile: str) -> dict[str, Any]:
        fn = getattr(self._b, "caps", None)
        if fn is None:
            return {"profile": profile, "demo": False, "note": "no caps()"}
        r = fn(profile) if callable(fn) else fn
        if hasattr(r, "__await__"):
            r = await r
        out = dict(r) if isinstance(r, dict) else {"raw": r, "profile": profile}
        out["demo"] = False
        return out

    async def recent_logs(self, limit: int = 50) -> list[dict[str, Any]]:
        fn = getattr(self._b, "recent_logs", None) or getattr(self._b, "logs", None)
        if fn is None:
            return []
        r = fn(limit) if callable(fn) else fn
        if hasattr(r, "__await__"):
            r = await r
        return list(r or [])[:limit]

    async def shadow_compare(self, profile: str, shadow: str) -> dict[str, Any]:
        fn = getattr(self._b, "shadow_compare", None)
        if fn is None:
            return {"profile": profile, "shadow": shadow, "demo": False, "diff": []}
        r = fn(profile, shadow)
        if hasattr(r, "__await__"):
            r = await r
        return dict(r) if isinstance(r, dict) else {"raw": r}


class LiveShine:
    def __init__(self, backend: Any) -> None:
        self._b = backend

    async def capabilities(self) -> dict[str, Any]:
        fn = getattr(self._b, "capabilities", None) or getattr(self._b, "caps", None)
        if fn is None:
            return {"demo": False, "note": "no capabilities"}
        r = fn() if callable(fn) else fn
        if hasattr(r, "__await__"):
            r = await r
        out = dict(r) if isinstance(r, dict) else {"raw": r}
        out["demo"] = False
        return out


class LiveCortex:
    def __init__(self, backend: Any) -> None:
        self._b = backend

    async def facts(self, tenant_id: str) -> list[dict[str, Any]]:
        fn = getattr(self._b, "facts", None)
        if fn is None:
            return []
        r = fn(tenant_id)
        if hasattr(r, "__await__"):
            r = await r
        return list(r or [])

    async def conflicts(self, tenant_id: str) -> list[dict[str, Any]]:
        fn = getattr(self._b, "conflicts", None)
        if fn is None:
            return []
        r = fn(tenant_id)
        if hasattr(r, "__await__"):
            r = await r
        return list(r or [])

    async def resolve_conflict(
        self, tenant_id: str, conflict_id: str, resolution: dict[str, Any]
    ) -> dict[str, Any]:
        fn = getattr(self._b, "resolve_conflict", None)
        if fn is None:
            return {"resolved": conflict_id, "note": "backend has no resolve"}
        r = fn(tenant_id, conflict_id, resolution)
        if hasattr(r, "__await__"):
            r = await r
        return dict(r) if isinstance(r, dict) else {"resolved": conflict_id}

    def sleep(self, tenant_id: str) -> None:
        fn = getattr(self._b, "sleep", None)
        if fn:
            fn(tenant_id)

    async def explain(self, tenant_id: str, query: str) -> dict[str, Any]:
        fn = getattr(self._b, "explain", None)
        if fn is None:
            return {"tenant_id": tenant_id, "query": query, "note": "no explain"}
        r = fn(tenant_id, query)
        if hasattr(r, "__await__"):
            r = await r
        return dict(r) if isinstance(r, dict) else {"result": r}

    async def recall_at(self, tenant_id: str, ts: float, query: str) -> dict[str, Any]:
        fn = getattr(self._b, "recall_at", None)
        if fn is None:
            return {"tenant_id": tenant_id, "ts": ts, "query": query, "note": "no recall_at"}
        r = fn(tenant_id, ts, query)
        if hasattr(r, "__await__"):
            r = await r
        return dict(r) if isinstance(r, dict) else {"result": r}


class LiveGraph:
    def __init__(self, backend: Any) -> None:
        self._b = backend

    async def dogfood(self) -> dict[str, Any]:
        fn = getattr(self._b, "dogfood", None) or getattr(self._b, "health", None)
        if fn is None:
            return {"ok": True, "demo": False}
        r = fn() if callable(fn) else fn
        if hasattr(r, "__await__"):
            r = await r
        out = dict(r) if isinstance(r, dict) else {"ok": bool(r), "raw": r}
        out["demo"] = False
        return out

    async def mark_revalidate(self, tenant_id: str, tags: list[str]) -> None:
        """Call sibling mark_revalidate with signature tolerance (BUG-010).

        NullGraph / adapter style: ``(tenant_id, tags)``.
        chorusgraph public helper needs a SidecarStore — without one we no-op
        so cascade still completes.
        """
        fn = getattr(self._b, "mark_revalidate", None)
        if not fn:
            return
        for kwargs_only in (False, True):
            try:
                r = (
                    fn(tenant_id=tenant_id, tags=tags)
                    if kwargs_only
                    else fn(tenant_id, tags)
                )
                if hasattr(r, "__await__"):
                    await r
                return
            except TypeError:
                continue
        log.debug(
            "mark_revalidate skipped on %s (needs sidecar or different signature)",
            type(self._b),
        )

    async def driver_latency(self) -> dict[str, Any]:
        fn = getattr(self._b, "driver_latency", None) or getattr(self._b, "prismdriver_stats", None)
        if fn is None:
            return {"p50_ms": None, "demo": False, "note": "no driver stats"}
        r = fn() if callable(fn) else fn
        if hasattr(r, "__await__"):
            r = await r
        out = dict(r) if isinstance(r, dict) else {"raw": r}
        out["demo"] = False
        return out


class LiveRag:
    def __init__(self, backend: Any) -> None:
        self._b = backend

    async def tree(self, tenant_id: str) -> dict[str, Any]:
        from choruscontrol.services.taxonomy_rag import taxonomy_tree

        # Prefer shared PrismRAG mapping/community tree (live when package present)
        packed = taxonomy_tree(tenant_id)
        if not packed.get("demo"):
            return packed
        fn = getattr(self._b, "tree", None) or getattr(self._b, "category_tree", None)
        if fn is None:
            return packed
        r = fn(tenant_id)
        if hasattr(r, "__await__"):
            r = await r
        out = dict(r) if isinstance(r, dict) else {"categories": r}
        out.setdefault("demo", False)
        out.setdefault("engine", "live")
        return out

    async def search(self, tenant_id: str, query: str) -> list[dict[str, Any]]:
        fn = getattr(self._b, "search", None)
        if fn is None:
            return []
        r = fn(tenant_id, query)
        if hasattr(r, "__await__"):
            r = await r
        return list(r or [])

    async def partitions(self, tenant_id: str) -> list[dict[str, Any]]:
        from choruscontrol.services.taxonomy_rag import taxonomy_partitions

        packed = taxonomy_partitions(tenant_id)
        if not packed.get("demo"):
            return list(packed.get("partitions") or [])
        fn = getattr(self._b, "partitions", None)
        if fn is None:
            return list(packed.get("partitions") or [])
        r = fn(tenant_id)
        if hasattr(r, "__await__"):
            r = await r
        return list(r or [])

    async def chunks_health(self, tenant_id: str) -> dict[str, Any]:
        from choruscontrol.services.taxonomy_rag import taxonomy_chunks_health

        packed = taxonomy_chunks_health(tenant_id)
        if not packed.get("demo"):
            return packed
        fn = getattr(self._b, "chunks_health", None)
        if fn is None:
            return packed
        r = fn(tenant_id)
        if hasattr(r, "__await__"):
            r = await r
        return dict(r) if isinstance(r, dict) else {"raw": r}

    def warm_partition(self, tenant_id: str, partition: str) -> None:
        fn = getattr(self._b, "warm_partition", None)
        if fn:
            fn(tenant_id, partition)

    def reindex(self, tenant_id: str, category_id: str | None = None) -> None:
        fn = getattr(self._b, "reindex", None) or getattr(self._b, "reindex_category", None)
        if fn:
            fn(tenant_id, category_id)


class LiveFabric:
    def __init__(self, backend: Any) -> None:
        self._b = backend

    async def broadcast_signal(self, payload: dict[str, Any]) -> None:
        fn = getattr(self._b, "broadcast", None) or getattr(self._b, "broadcast_signal", None)
        if fn:
            r = fn(payload)
            if hasattr(r, "__await__"):
                await r

    async def peer_count(self) -> int:
        fn = getattr(self._b, "peer_count", None)
        if fn is None:
            return 0
        r = fn() if callable(fn) else fn
        if hasattr(r, "__await__"):
            r = await r
        return int(r or 0)


def _construct_cache() -> LiveCache | None:
    """prismlib-plus installs as import package ``prism`` (not prismlib_plus)."""
    try:
        from prism.cache import HashEmbedder, InMemoryStore, PrismCache, PrismCacheConfig

        backend = PrismCache(
            PrismCacheConfig(tenant_id="choruscontrol-mother"),
            HashEmbedder(),
            InMemoryStore(),
        )
        return LiveCache(backend)
    except Exception as exc:  # noqa: BLE001
        log.warning("live cache via prism.cache failed: %s", exc)
    try:
        from prismlib_plus import PrismCache  # type: ignore

        return LiveCache(PrismCache())
    except Exception as exc:  # noqa: BLE001
        log.warning("live cache via prismlib_plus failed: %s", exc)
    return None


def try_construct(logical: str) -> Any | None:
    ready, dist, ver = package_ready(logical)
    if not ready:
        return None
    try:
        if logical == "guard":
            import prismguard  # type: ignore

            backend = getattr(prismguard, "PrismGuard", None) or getattr(prismguard, "Guard", None)
            return LiveGuard(backend() if callable(backend) else prismguard)
        if logical == "shine":
            import prismshine  # type: ignore

            backend = getattr(prismshine, "PrismShine", None) or prismshine
            return LiveShine(backend() if callable(backend) else backend)
        if logical == "cortex":
            import prismcortex  # type: ignore

            backend = getattr(prismcortex, "Cortex", None) or prismcortex
            return LiveCortex(backend() if callable(backend) else backend)
        if logical == "graph":
            import chorusgraph  # type: ignore

            backend = getattr(chorusgraph, "ChorusGraph", None) or chorusgraph
            return LiveGraph(backend() if callable(backend) else backend)
        if logical == "rag":
            from choruscontrol.services.taxonomy_rag import construct_prismrag

            backend = construct_prismrag(tenant_id="default")
            if backend is None:
                return None
            return LiveRag(backend)
        if logical == "cache":
            return _construct_cache()
        if logical == "fabric":
            import chorus_fabric as cf  # type: ignore

            backend = getattr(cf, "Fabric", None) or cf
            return LiveFabric(backend() if callable(backend) else backend)
    except Exception as exc:  # noqa: BLE001
        log.warning("live adapter %s (%s@%s) failed: %s", logical, dist, ver, exc)
        return None
    return None
