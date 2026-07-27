from __future__ import annotations

import pytest

from choruscontrol.adapters.nulls import NullCache, NullFabric, NullGraph
from choruscontrol.engine.cascade import CascadeService, InvalidationBroadcaster
from choruscontrol.persistence import Store


@pytest.mark.asyncio
async def test_cascade_and_invalidation(tmp_path):
    store = Store(tmp_path / "t.db")
    async with store.session():
        pass
    fabric = NullFabric()
    cache = NullCache()
    graph = NullGraph()
    broadcaster = InvalidationBroadcaster(fabric, 0.55)

    async def mark(tenant_id, tags):
        await graph.mark_revalidate(tenant_id, tags)

    svc = CascadeService(store, broadcaster, cache, mark)
    result = await svc.run("acme", ["person_a"], reason="test")
    assert result["cascade_id"]
    assert fabric.signals
    assert fabric.signals[0]["event"] == "INVALIDATE_CACHE"
    assert fabric.signals[0]["force_refresh"] is True
    await svc.record_ack(result["cascade_id"], "n1", "ok")
    slo = await svc.consistency_slo(result["cascade_id"])
    assert slo["acked"] == 1
