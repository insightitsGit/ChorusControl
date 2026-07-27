from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass, field
from typing import Any

from choruscontrol.adapters.factory import build_adapters
from choruscontrol.audit.logger import AuditLogger, load_or_create_audit_key
from choruscontrol.config import Settings
from choruscontrol.engine.cascade import CascadeService, InvalidationBroadcaster
from choruscontrol.engine.job_queue import MaintenanceJobQueue
from choruscontrol.fleet.registry import FleetRegistry
from choruscontrol.license import LicenseStatus, LicenseVerifier
from choruscontrol.license.store import resolve_license_key
from choruscontrol.persistence import Store
from choruscontrol.services.metrics import MetricsSampler
from choruscontrol.services.tenants import ensure_default_tenant

log = logging.getLogger("choruscontrol.app_state")


@dataclass
class AppState:
    settings: Settings
    store: Store
    license_verifier: LicenseVerifier
    license_status: LicenseStatus
    audit: AuditLogger
    fleet: FleetRegistry
    jobs: MaintenanceJobQueue
    cascade: CascadeService
    cache: Any
    fabric: Any
    guard: Any
    shine: Any
    cortex: Any
    graph: Any
    rag: Any
    adapter_sources: dict[str, str] = field(default_factory=dict)
    adapter_pins: dict[str, Any] = field(default_factory=dict)
    pending_commands: dict[str, list[dict[str, Any]]] = field(default_factory=dict)
    intended_policies: dict[str, dict[str, Any]] = field(default_factory=dict)
    trace_subscribers: list[Any] = field(default_factory=list)
    fleet_subscribers: list[Any] = field(default_factory=list)
    node_stats: dict[str, dict[str, Any]] = field(default_factory=dict)
    postgres: Any | None = None
    metrics_sampler: MetricsSampler | None = None

    async def refresh_license(self) -> LicenseStatus:
        key = resolve_license_key(self.settings)
        self.license_status = self.license_verifier.verify(key)
        return self.license_status

    async def broadcast_fleet(self, event: dict[str, Any]) -> None:
        dead = []
        for ws in list(self.fleet_subscribers):
            try:
                await ws.send_json(event)
            except Exception:  # noqa: BLE001
                dead.append(ws)
        for ws in dead:
            if ws in self.fleet_subscribers:
                self.fleet_subscribers.remove(ws)


async def build_state(settings: Settings) -> AppState:
    store = Store(settings.sqlite_path)
    async with store.session():
        pass
    await ensure_default_tenant(store)

    verifier = LicenseVerifier(
        grace_days=settings.license_grace_days,
        clock_skew_seconds=settings.license_clock_skew_seconds,
    )
    resolved = resolve_license_key(settings)
    if settings.demo_mode or not resolved:
        from choruscontrol.license import LicenseClaims

        now = int(time.time())
        claims = LicenseClaims(
            sub="demo",
            iat=now,
            exp=now + 86400 * 365,
            license_id="lic_demo",
            features={
                "trace.replay",
                "guard.shadow",
                "audit.export",
                "assistant.ops",
                "caps.read",
                "fleet.topology",
                "cascade.auto",
                "guard.policy",
                "caps.aggregate",
            },
        )
        issued = verifier.issue_dev_token(claims)
        settings.license_key = issued

    key = resolve_license_key(settings) or settings.license_key
    status = verifier.verify(key)
    audit_key = load_or_create_audit_key(settings.audit_private_key_pem)

    postgres = None
    if settings.database_url:
        from choruscontrol.persistence.postgres import PostgresSink

        postgres = PostgresSink(settings.database_url)
        try:
            await postgres.connect()
        except Exception as exc:  # noqa: BLE001
            postgres.ok = False
            postgres.last_error = str(exc)

    audit = AuditLogger(audit_key, settings.audit_log_path, postgres=postgres)
    audit.start()

    bundle = build_adapters(force_demo=settings.demo_mode)
    cache, fabric = bundle.cache, bundle.fabric
    guard, shine = bundle.guard, bundle.shine
    cortex, graph, rag = bundle.cortex, bundle.graph, bundle.rag

    fleet = FleetRegistry(store)
    jobs = MaintenanceJobQueue(settings.jobs_max_concurrent)
    jobs.register("cortex.sleep", lambda tenant_id, params: cortex.sleep(tenant_id))

    def _reindex(tenant_id: str, params: dict[str, Any]) -> None:
        fn = getattr(rag, "reindex", None) or getattr(rag, "reindex_category", None)
        if fn:
            fn(tenant_id, params.get("category_id"))
        else:
            time.sleep(0.05)

    jobs.register("taxonomy.reindex", _reindex)

    def _warm(tenant_id: str, params: dict[str, Any]) -> None:
        part = params.get("partition") or "kb_markdown"
        warm = getattr(rag, "warm_partition", None)
        if warm:
            warm(tenant_id, part)
        else:
            time.sleep(0.05)

    jobs.register("taxonomy.warm_partition", _warm)

    broadcaster = InvalidationBroadcaster(fabric, settings.invalidation_threshold)

    async def _mark(tenant_id: str, tags: list[str]) -> None:
        await graph.mark_revalidate(tenant_id, tags)

    cascade = CascadeService(store, broadcaster, cache, _mark)

    async def _cascade_job(tenant_id: str, params: dict[str, Any]) -> None:
        await cascade.run(
            tenant_id,
            list(params.get("tags") or []),
            params.get("probe_vector"),
            params.get("reason") or "job",
        )

    jobs.register("cascade.run", _cascade_job)

    default_policy = {
        "ingress_profile": "web_chat",
        "ingress_use_onnx": False,
        "shadow_profile": "light",
        "shadow_enabled": True,
        "enforce_shadow": False,
        "recommended_preset": "finance_hub",
    }
    await store.execute(
        "INSERT OR IGNORE INTO guard_policies(tenant_id, policy_json, updated_at) VALUES(?,?,?)",
        ("default", json.dumps(default_policy), time.time()),
    )

    if settings.allow_insecure_external:
        log.warning(
            "CHORUSCONTROL_ALLOW_INSECURE_EXTERNAL=1 — external-zone agents may join over plaintext HTTP"
        )

    state = AppState(
        settings=settings,
        store=store,
        license_verifier=verifier,
        license_status=status,
        audit=audit,
        fleet=fleet,
        jobs=jobs,
        cascade=cascade,
        cache=cache,
        fabric=fabric,
        guard=guard,
        shine=shine,
        cortex=cortex,
        graph=graph,
        rag=rag,
        adapter_sources=bundle.sources,
        adapter_pins=bundle.pins,
        intended_policies={"default": default_policy},
        postgres=postgres,
    )
    sampler = MetricsSampler(state)
    if settings.demo_mode and settings.metrics_sample_interval_seconds > 5:
        settings.metrics_sample_interval_seconds = 5.0
    sampler.start()
    state.metrics_sampler = sampler
    return state
