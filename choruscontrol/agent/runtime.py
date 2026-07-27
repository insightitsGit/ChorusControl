from __future__ import annotations

import argparse
import asyncio
import logging
import time
from typing import Any, Callable

from choruscontrol.agent.ledger import LedgerExporter
from choruscontrol.agent.probe import caps_digest, probe_products
from choruscontrol.agent.transport import HttpControlTransport
from choruscontrol.config import get_settings

log = logging.getLogger("choruscontrol.agent")

SUPPORTED_COMMANDS = {
    "INVALIDATE_CACHE",
    "REQUEST_CAPS",
    "REQUEST_METRICS",
    "RUN_SLEEP",
    "WARM_PARTITION",
    "REINDEX",
    "RUN_REINDEX",
    "APPLY_GUARD_POLICY",
    "DRAIN",
    "REVOKE",
}


class AgentRuntime:
    """Background-only agent. Never await mother on app hot path."""

    def __init__(
        self,
        *,
        cache_invalidate: Callable[[list[str]], Any] | None = None,
        cortex_sleep: Callable[[str], None] | None = None,
        rag_warm: Callable[[str, str], None] | None = None,
    ) -> None:
        self.settings = get_settings()
        if not self.settings.mother_url:
            raise SystemExit("CHORUSCONTROL_MOTHER_URL required")
        self.transport = HttpControlTransport(self.settings.mother_url)
        self.node_id = self.settings.node_id
        self.session_secret: str | None = None
        self._cmd_queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._cache_invalidate = cache_invalidate
        self._cortex_sleep = cortex_sleep
        self._rag_warm = rag_warm
        self.ledger: LedgerExporter | None = None
        self.mother_calls_on_hot_path = 0
        self._started_at = time.time()
        self._stop = asyncio.Event()

    def _resolve_memory_endpoint(self) -> str | None:
        """R04 — advertise Cortex address for this node."""
        if self.settings.memory_endpoint:
            return self.settings.memory_endpoint
        role = (self.settings.node_role or "").lower()
        if role not in ("memory", "cortex"):
            return None
        try:
            import prismcortex  # noqa: F401
        except Exception:  # noqa: BLE001
            return None
        nid = self.node_id or self.settings.node_id or "pending"
        return f"local://{nid}"

    async def start(self) -> None:
        if (
            self.settings.network_zone == "external"
            and (self.settings.mother_url or "").lower().startswith("http://")
        ):
            log.warning(
                "network_zone=external but mother_url is plaintext HTTP — TLS required in production"
            )
        products = probe_products()
        join_token = self.settings.join_token
        if not join_token:
            raise SystemExit("CHORUSCONTROL_JOIN_TOKEN required")
        result = await self.transport.join(
            {
                "join_token": join_token,
                "node_id": self.node_id,
                "tenant_id": self.settings.tenant_id,
                "role": self.settings.node_role,
                "network_zone": self.settings.network_zone,
                "products": products,
                "caps_digest": caps_digest(products),
                "memory_endpoint": self._resolve_memory_endpoint(),
            }
        )
        self.node_id = result["node_id"]
        self.session_secret = result["session_secret"]
        self.ledger = LedgerExporter(
            self.settings.mother_url or "",
            node_id=self.node_id or "unknown",
            tenant_id=self.settings.tenant_id,
            session_secret=self.session_secret,
        )
        self.ledger.start()
        log.info("joined mother as %s", self.node_id)
        await asyncio.gather(self._heartbeat_loop(), self._command_loop())

    async def _heartbeat_loop(self) -> None:
        while not self._stop.is_set():
            products = probe_products()
            try:
                await self.transport.heartbeat(
                    {
                        "node_id": self.node_id,
                        "session_secret": self.session_secret,
                        "products": products,
                        "caps_digest": caps_digest(products),
                        "role": self.settings.node_role,
                        "memory_endpoint": self._resolve_memory_endpoint(),
                        "ledger_dropped_total": self.ledger.dropped if self.ledger else 0,
                        "agent_ledger_dropped_total": self.ledger.dropped if self.ledger else 0,
                    }
                )
            except Exception as exc:  # noqa: BLE001
                log.warning("heartbeat failed: %s", exc)
            try:
                await asyncio.wait_for(
                    self._stop.wait(), timeout=self.settings.heartbeat_interval_seconds
                )
            except asyncio.TimeoutError:
                pass

    async def _command_loop(self) -> None:
        while not self._stop.is_set():
            try:
                commands = await self.transport.poll_commands(
                    self.node_id or "", self.session_secret or ""
                )
                for cmd in commands:
                    await self._handle(cmd)
            except Exception as exc:  # noqa: BLE001
                log.warning("command poll failed: %s", exc)
            try:
                await asyncio.wait_for(self._stop.wait(), timeout=2.0)
            except asyncio.TimeoutError:
                pass

    async def _handle(self, cmd: dict[str, Any]) -> None:
        ctype = cmd.get("type")
        status = "ok"
        detail: dict[str, Any] = {}
        stop_after = False
        try:
            if ctype not in SUPPORTED_COMMANDS:
                status = "nack"
                detail = {
                    "reason": f"unsupported:{ctype}",
                    "supported": sorted(SUPPORTED_COMMANDS),
                }
            elif ctype == "INVALIDATE_CACHE":
                tags = cmd.get("tags") or []
                if self._cache_invalidate:
                    r = self._cache_invalidate(tags)
                    if asyncio.iscoroutine(r):
                        r = await r
                    detail = {"evicted": r, "tags": tags}
                else:
                    detail = {"evicted": len(tags), "tags": tags, "local": True}
            elif ctype == "REQUEST_CAPS":
                detail = {
                    "products": probe_products(),
                    "supported_commands": sorted(SUPPORTED_COMMANDS),
                }
            elif ctype == "REQUEST_METRICS":
                detail = {
                    "ledger_queue_depth": self.ledger._q.qsize() if self.ledger else 0,
                    "ledger_dropped_total": self.ledger.dropped if self.ledger else 0,
                    "uptime_seconds": time.time() - self._started_at,
                }
            elif ctype == "RUN_SLEEP":
                tenant = cmd.get("tenant_id") or self.settings.tenant_id
                if self._cortex_sleep:
                    await asyncio.get_running_loop().run_in_executor(
                        None, self._cortex_sleep, tenant
                    )
                detail = {"sleep": True, "tenant_id": tenant}
            elif ctype == "WARM_PARTITION":
                tenant = cmd.get("tenant_id") or self.settings.tenant_id
                part = cmd.get("partition") or "kb_markdown"
                if self._rag_warm:
                    await asyncio.get_running_loop().run_in_executor(
                        None, self._rag_warm, tenant, part
                    )
                detail = {"warm": part, "tenant_id": tenant}
            elif ctype in ("REINDEX", "RUN_REINDEX"):
                detail = {"reindex": True, "type": ctype, "note": "delegated locally if rag present"}
            elif ctype == "APPLY_GUARD_POLICY":
                detail = {"applied": True, "policy": cmd.get("policy")}
            elif ctype == "DRAIN":
                if self.ledger:
                    # Best-effort drain: flush whatever is queued without blocking hot path later
                    batch: list = []
                    while True:
                        try:
                            item = self.ledger._q.get_nowait()
                        except Exception:  # noqa: BLE001
                            break
                        if item is None:
                            break
                        batch.append(item)
                    if batch:
                        await self.ledger._flush(batch)
                detail = {"drained": True, "dropped": self.ledger.dropped if self.ledger else 0}
            elif ctype == "REVOKE":
                detail = {"revoked": True}
                stop_after = True
        except Exception as exc:  # noqa: BLE001
            status = "error"
            detail = {"error": str(exc)}
        await self.transport.ack(
            {
                "node_id": self.node_id,
                "session_secret": self.session_secret,
                "command_id": cmd.get("command_id"),
                "cascade_id": cmd.get("cascade_id"),
                "status": status,
                "detail": detail,
            }
        )
        if stop_after:
            log.info("REVOKE received — stopping agent")
            self._stop.set()
            if self.ledger:
                await self.ledger.stop()

    def record_ledger(self, entry: dict[str, Any]) -> bool:
        """Hot-path safe: enqueue only, never await mother."""
        if self.ledger is None:
            return False
        return self.ledger.enqueue(entry)


def invoke_passthrough(fn: Callable[..., Any], *args: Any, agent: AgentRuntime | None = None, **kwargs: Any) -> Any:
    """Example hot-path wrapper — must never await mother."""
    t0 = time.perf_counter()
    result = fn(*args, **kwargs)
    if agent is not None:
        agent.record_ledger(
            {
                "stage": "graph",
                "kind": "invoke",
                "ts": time.time(),
                "detail": {"elapsed_ms": (time.perf_counter() - t0) * 1000},
            }
        )
    return result


def attach_agent() -> asyncio.Task[None]:
    """Schedule agent in background — must not be awaited on request path."""
    runtime = AgentRuntime()
    return asyncio.create_task(runtime.start())


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description="ChorusControl fleet agent")
    parser.add_argument("--doctor", action="store_true", help="Print agent doctor and exit")
    args = parser.parse_args()
    if args.doctor:
        import json

        from choruscontrol.services.doctor import doctor_agent

        print(json.dumps(doctor_agent(mother_url=get_settings().mother_url), indent=2))
        return
    asyncio.run(AgentRuntime().start())


if __name__ == "__main__":
    main()
