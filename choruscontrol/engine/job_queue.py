from __future__ import annotations

import asyncio
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from typing import Any, Callable, Literal

JobState = Literal["queued", "running", "completed", "failed", "busy"]
Handler = Callable[[str, dict[str, Any]], Any]


@dataclass
class JobStatus:
    job_id: str
    tenant_id: str
    job_type: str
    state: JobState
    params: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    created_at: float = field(default_factory=time.time)
    finished_at: float | None = None


class MaintenanceJobQueue:
    def __init__(self, max_concurrent: int = 2) -> None:
        self.max_concurrent = max_concurrent
        self._tenant_locks: dict[str, asyncio.Lock] = {}
        self._jobs: dict[str, JobStatus] = {}
        self._handlers: dict[str, Handler] = {}
        self._sem = asyncio.Semaphore(max_concurrent)
        self._executor = ThreadPoolExecutor(max_workers=max(2, max_concurrent))

    def register(self, job_type: str, handler: Handler) -> None:
        self._handlers[job_type] = handler

    def _lock_for(self, tenant_id: str) -> asyncio.Lock:
        if tenant_id not in self._tenant_locks:
            self._tenant_locks[tenant_id] = asyncio.Lock()
        return self._tenant_locks[tenant_id]

    async def submit(
        self, tenant_id: str, job_type: str, params: dict[str, Any] | None = None
    ) -> JobStatus:
        lock = self._lock_for(tenant_id)
        if lock.locked():
            active = next(
                (
                    j
                    for j in self._jobs.values()
                    if j.tenant_id == tenant_id and j.state in ("queued", "running")
                ),
                None,
            )
            return JobStatus(
                job_id=active.job_id if active else "unknown",
                tenant_id=tenant_id,
                job_type=job_type,
                state="busy",
                params=params or {},
                error=f"tenant busy; active={active.job_id if active else None}",
            )
        job = JobStatus(
            job_id=str(uuid.uuid4()),
            tenant_id=tenant_id,
            job_type=job_type,
            state="queued",
            params=params or {},
        )
        self._jobs[job.job_id] = job
        asyncio.create_task(self._run(job, lock))
        return job

    async def _run(self, job: JobStatus, lock: asyncio.Lock) -> None:
        async with lock:
            async with self._sem:
                job.state = "running"
                handler = self._handlers.get(job.job_type)
                if not handler:
                    job.state = "failed"
                    job.error = f"no handler for {job.job_type}"
                    job.finished_at = time.time()
                    return
                try:
                    loop = asyncio.get_running_loop()
                    if asyncio.iscoroutinefunction(handler):
                        await handler(job.tenant_id, job.params)
                    else:
                        await loop.run_in_executor(
                            self._executor, handler, job.tenant_id, job.params
                        )
                    job.state = "completed"
                except Exception as exc:  # noqa: BLE001
                    job.state = "failed"
                    job.error = str(exc)
                job.finished_at = time.time()

    def get(self, job_id: str) -> JobStatus | None:
        return self._jobs.get(job_id)

    async def trigger_sleep(self, tenant_id: str) -> JobStatus:
        return await self.submit(tenant_id, "cortex.sleep", {})

    async def trigger_reindex(
        self, tenant_id: str, category_id: str | None = None
    ) -> JobStatus:
        return await self.submit(tenant_id, "taxonomy.reindex", {"category_id": category_id})

    async def trigger_warm(
        self, tenant_id: str, partition: str | None = None
    ) -> JobStatus:
        return await self.submit(
            tenant_id, "taxonomy.warm_partition", {"partition": partition or "kb_markdown"}
        )
