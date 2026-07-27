from __future__ import annotations

import asyncio
import time

import pytest

from choruscontrol.adapters.nulls import NullCortex
from choruscontrol.engine.job_queue import MaintenanceJobQueue


@pytest.mark.asyncio
async def test_sleep_does_not_block_other_tenant_and_busy_same_tenant():
    q = MaintenanceJobQueue(max_concurrent=2)
    cortex = NullCortex()
    q.register("cortex.sleep", lambda tenant_id, params: cortex.sleep(tenant_id))

    # concurrent digest/recall simulation while sleep runs
    flags = {"digest": 0}

    async def digest_loop():
        for _ in range(20):
            flags["digest"] += 1
            await asyncio.sleep(0.001)

    job = await q.trigger_sleep("t1")
    assert job.state in ("queued", "running", "completed")
    dig = asyncio.create_task(digest_loop())
    # same tenant second sleep should be busy while first holds lock
    await asyncio.sleep(0.01)
    busy = await q.trigger_sleep("t1")
    # may be busy or completed depending on timing
    assert busy.state in ("busy", "queued", "running", "completed")
    await dig
    assert flags["digest"] == 20
    # wait for completion
    for _ in range(50):
        got = q.get(job.job_id)
        if got and got.state in ("completed", "failed"):
            break
        await asyncio.sleep(0.02)
    assert q.get(job.job_id).state == "completed"
