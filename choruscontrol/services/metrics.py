"""Time-series metric samples + predictive / RCA-style recommendations."""

from __future__ import annotations

import asyncio
import json
import time
from typing import Any


async def record_sample(store, name: str, value: float, labels: dict[str, Any] | None = None) -> None:
    await store.execute(
        "INSERT INTO metric_samples(ts, name, value, labels_json) VALUES(?,?,?,?)",
        (time.time(), name, float(value), json.dumps(labels or {})),
    )


async def prune_samples(store, retention_hours: int) -> int:
    cutoff = time.time() - retention_hours * 3600
    before = await store.fetchone("SELECT COUNT(*) AS c FROM metric_samples")
    await store.execute("DELETE FROM metric_samples WHERE ts < ?", (cutoff,))
    after = await store.fetchone("SELECT COUNT(*) AS c FROM metric_samples")
    return int((before or {}).get("c") or 0) - int((after or {}).get("c") or 0)


async def series(store, name: str, limit: int = 120) -> list[dict[str, Any]]:
    rows = await store.fetchall(
        "SELECT ts, value, labels_json FROM metric_samples WHERE name=? ORDER BY ts DESC LIMIT ?",
        (name, limit),
    )
    rows = list(reversed(rows))
    return [{"ts": r["ts"], "value": r["value"], "labels": json.loads(r["labels_json"])} for r in rows]


def _slope(points: list[float]) -> float | None:
    n = len(points)
    if n < 4:
        return None
    xs = list(range(n))
    mean_x = sum(xs) / n
    mean_y = sum(points) / n
    num = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, points))
    den = sum((x - mean_x) ** 2 for x in xs) or 1.0
    return num / den


async def predictive_recommendations(state) -> dict[str, Any]:
    """Honest predictive layer: trend slopes from retained samples + incident/version RCA hints."""
    from choruscontrol.services.caps import policy_drift

    recs: list[dict[str, Any]] = []
    hit = await series(state.store, "cache.hit_rate", 60)
    if hit:
        slope = _slope([p["value"] for p in hit])
        if slope is not None and slope < -0.002:
            recs.append(
                {
                    "id": "hit-rate-decline",
                    "severity": "high",
                    "title": "Cache hit rate trending down",
                    "detail": f"slope={slope:.5f} over {len(hit)} samples — review invalidation / warm jobs",
                    "predictive": True,
                }
            )

    cost = await series(state.store, "cache.cost_saved_usd", 60)
    if cost:
        slope = _slope([p["value"] for p in cost])
        if slope is not None and slope < -0.05:
            recs.append(
                {
                    "id": "cost-efficiency-decline",
                    "severity": "medium",
                    "title": "Token-tax savings declining",
                    "detail": f"slope={slope:.4f} — check PrismCache eviction and Driver latency",
                    "predictive": True,
                }
            )

    drifts = await policy_drift(state)
    drifted = [d for d in drifts if d["drift"]]
    if drifted:
        recs.append(
            {
                "id": "policy-drift",
                "severity": "high",
                "title": "Resolve policy drift",
                "detail": f"{len(drifted)} nodes diverge from intended ingress",
                "predictive": False,
            }
        )

    # RCA: correlate recent incidents with concrete product diffs when 2+ days exist
    incidents = await state.store.fetchall(
        "SELECT * FROM incidents ORDER BY created_at DESC LIMIT 5"
    )
    for inc in incidents:
        snaps = await state.store.fetchall(
            "SELECT * FROM version_snapshots ORDER BY id DESC LIMIT 4"
        )
        if len(snaps) >= 2:
            before = json.loads(snaps[1]["products_json"])
            after = json.loads(snaps[0]["products_json"])
            changed = {
                k: {"before": before.get(k), "after": after.get(k)}
                for k in sorted(set(before) | set(after))
                if before.get(k) != after.get(k)
            }
            if changed:
                recs.append(
                    {
                        "id": f"rca-{inc['incident_id']}",
                        "severity": "info",
                        "title": f"RCA: product churn near {inc['title'][:48]}",
                        "detail": f"Changed packages: {', '.join(list(changed)[:6])}",
                        "predictive": False,
                        "rca": True,
                        "products_before": before,
                        "products_after": after,
                        "incident_id": inc["incident_id"],
                    }
                )
                break

    # Knowledge staleness trend
    stale = await series(state.store, "rag.staleness", 40)
    if stale:
        slope = _slope([p["value"] for p in stale])
        last = stale[-1]["value"]
        if last > 0.55 or (slope is not None and slope > 0.01):
            recs.append(
                {
                    "id": "rag-staleness",
                    "severity": "high" if last > 0.7 else "medium",
                    "title": "Knowledge staleness rising",
                    "detail": f"mean_staleness={last:.3f} slope={slope}",
                    "predictive": True,
                }
            )

    metrics = await state.cache.get_metrics()
    if not recs:
        recs.append(
            {
                "id": "healthy",
                "severity": "info",
                "title": "No urgent recommendations",
                "detail": "Trends stable within retention window.",
                "predictive": True,
            }
        )

    sample_count = await state.store.fetchone("SELECT COUNT(*) AS c FROM metric_samples")
    return {
        "recommendations": recs,
        "predictive": True,
        "retention_hours": state.settings.metrics_retention_hours,
        "samples": int((sample_count or {}).get("c") or 0),
        "demo": bool(metrics.get("demo")),
    }


class MetricsSampler:
    def __init__(self, state) -> None:
        self.state = state
        self._task: asyncio.Task[None] | None = None

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass

    async def _loop(self) -> None:
        while True:
            try:
                m = await self.state.cache.get_metrics()
                await record_sample(self.state.store, "cache.hit_rate", float(m.get("hit_rate") or 0))
                await record_sample(
                    self.state.store, "cache.cost_saved_usd", float(m.get("cost_saved_usd") or 0)
                )
                await record_sample(
                    self.state.store, "cache.tokens_saved", float(m.get("tokens_saved") or 0)
                )
                # RAG staleness sample for Score + predictive
                try:
                    parts = await self.state.rag.partitions("default")
                    decays = []
                    for p in parts or []:
                        if isinstance(p, dict):
                            for k in ("staleness", "decay", "health"):
                                if p.get(k) is not None:
                                    try:
                                        decays.append(float(p[k]))
                                    except (TypeError, ValueError):
                                        pass
                    if decays:
                        await record_sample(
                            self.state.store, "rag.staleness", sum(decays) / len(decays)
                        )
                except Exception:  # noqa: BLE001
                    pass
                try:
                    from choruscontrol.services.version_intel import record_deployment_snapshot

                    await record_deployment_snapshot(self.state, "default")
                except Exception:  # noqa: BLE001
                    pass
                # Optional Side 1 license online check (~14 days)
                try:
                    await self.state.run_license_online_check(force=False)
                except Exception:  # noqa: BLE001
                    pass
                await prune_samples(self.state.store, self.state.settings.metrics_retention_hours)
                from choruscontrol.services.trace_retention import purge_traces

                await purge_traces(
                    self.state.store,
                    retention_days=self.state.settings.trace_retention_days,
                    max_rows=self.state.settings.trace_max_rows,
                )
                # cascade.auto: poll Cortex for unresolved conflicts (Null = no-op)
                await self._cascade_auto()
            except Exception:  # noqa: BLE001
                pass
            await asyncio.sleep(self.state.settings.metrics_sample_interval_seconds)

    async def _cascade_auto(self) -> None:
        from choruscontrol.services.incidents import create_incident

        s = self.state
        if not s.license_verifier.has_feature(s.license_status, "cascade.auto") and not s.settings.demo_mode:
            return
        list_fn = getattr(s.cortex, "list_unresolved_conflicts", None) or getattr(
            s.cortex, "conflicts", None
        )
        if not list_fn:
            return
        conflicts = await list_fn("default") if callable(list_fn) else []
        if not isinstance(conflicts, list):
            conflicts = (conflicts or {}).get("conflicts") or []
        for c in conflicts[:5]:
            if not isinstance(c, dict):
                continue
            if c.get("resolved"):
                continue
            title = c.get("title") or c.get("id") or "Unresolved Cortex conflict"
            await create_incident(
                s.store,
                tenant_id=c.get("tenant_id") or "default",
                title=f"cascade.auto: {title}",
                details={"source": "cascade.auto", "conflict": c},
            )
