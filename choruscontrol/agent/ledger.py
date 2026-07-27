"""Async ledger batch exporter — never blocks hot path; drops under backpressure."""

from __future__ import annotations

import asyncio
import logging
from typing import Any

import httpx

log = logging.getLogger("choruscontrol.agent.ledger")


class LedgerExporter:
    def __init__(
        self,
        mother_url: str,
        *,
        node_id: str,
        tenant_id: str,
        max_queue: int = 1000,
        batch_size: int = 50,
        flush_interval: float = 2.0,
    ) -> None:
        self.mother_url = mother_url.rstrip("/")
        self.node_id = node_id
        self.tenant_id = tenant_id
        self.max_queue = max_queue
        self.batch_size = batch_size
        self.flush_interval = flush_interval
        self._q: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue(maxsize=max_queue)
        self.dropped = 0
        self.sent = 0
        self._task: asyncio.Task[None] | None = None

    def enqueue(self, entry: dict[str, Any]) -> bool:
        """Non-blocking enqueue. Returns False if dropped."""
        try:
            self._q.put_nowait(entry)
            return True
        except asyncio.QueueFull:
            self.dropped += 1
            return False

    def start(self) -> asyncio.Task[None]:
        self._task = asyncio.create_task(self._loop())
        return self._task

    async def stop(self) -> None:
        await self._q.put(None)
        if self._task:
            await self._task

    async def _loop(self) -> None:
        batch: list[dict[str, Any]] = []
        while True:
            try:
                item = await asyncio.wait_for(self._q.get(), timeout=self.flush_interval)
            except asyncio.TimeoutError:
                item = None
                if not batch:
                    continue
            if item is None and not batch:
                # shutdown sentinel with empty batch
                if self._q.empty():
                    break
                continue
            if item is not None:
                batch.append(item)
            if item is None or len(batch) >= self.batch_size:
                await self._flush(batch)
                batch = []
                if item is None and self._q.empty():
                    # check if sentinel was consumed
                    break

    async def _flush(self, batch: list[dict[str, Any]]) -> None:
        if not batch:
            return
        truncated = self.dropped > 0
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                r = await client.post(
                    f"{self.mother_url}/api/v1/fleet/ledger-batch",
                    json={
                        "node_id": self.node_id,
                        "tenant_id": self.tenant_id,
                        "run_ids": list({e.get("run_id") for e in batch if e.get("run_id")}),
                        "entries": batch,
                        "truncated": truncated,
                    },
                )
                if r.status_code < 400:
                    self.sent += len(batch)
                else:
                    log.warning("ledger batch failed: %s", r.status_code)
        except Exception as exc:  # noqa: BLE001
            log.warning("ledger flush error: %s", exc)
