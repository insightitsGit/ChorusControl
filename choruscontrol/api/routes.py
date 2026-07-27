from __future__ import annotations

import io
import json
import time
import uuid
import zipfile
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from choruscontrol.auth import require_feature, require_role
from choruscontrol.license.stack import stack_license_status
from choruscontrol.license.store import save_stored_license
from choruscontrol.services.caps import aggregate_caps, compute_ai_score, fleet_role_color, policy_drift
from choruscontrol.services.doctor import doctor_mother
from choruscontrol.services.graph import (
    assistant_ask,
    blast_radius,
    graph_query,
    recommendations,
    sync_from_fleet,
)
from choruscontrol.services.incidents import create_incident, get_incident, list_incidents, link_cascade_incident
from choruscontrol.services.pipelines import live_pipelines
from choruscontrol.services.policy import PolicyValidationError, shadow_promote_checklist, validate_guard_policy
from choruscontrol.services.tenants import create_tenant, delete_tenant, list_tenants
from choruscontrol.services.traces import get_ledger, get_trace, list_traces, replay_trace, seed_demo_trace

router = APIRouter(prefix="/api/v1")


def state(request: Request):
    return request.app.state.cc


def _grace_block(s) -> None:
    if s.license_status.state == "grace":
        raise HTTPException(403, detail="license grace: mutations blocked")


class JoinBody(BaseModel):
    join_token: str
    node_id: str | None = None
    tenant_id: str = "default"
    role: str = "worker"
    network_zone: str = "in_vpc"
    products: dict[str, str] = Field(default_factory=dict)
    caps_digest: str | None = None
    memory_endpoint: str | None = None


class HeartbeatBody(BaseModel):
    node_id: str
    session_secret: str
    products: dict[str, str]
    caps_digest: str | None = None
    role: str | None = None
    ledger_dropped_total: int | None = None
    agent_ledger_dropped_total: int | None = None


class TenantBody(BaseModel):
    tenant_id: str
    name: str = ""
    settings: dict[str, Any] = Field(default_factory=dict)


class LicenseInstallBody(BaseModel):
    license_key: str


def _effective_scheme(request: Request) -> str:
    fwd = (request.headers.get("x-forwarded-proto") or "").split(",")[0].strip().lower()
    if fwd:
        return fwd
    return request.url.scheme.lower()


def _redact_license_claims(claims: dict[str, Any] | None) -> dict[str, Any] | None:
    if not claims:
        return None
    features = claims.get("features")
    if isinstance(features, set):
        features = sorted(features)
    return {
        "tier": claims.get("tier"),
        "exp": claims.get("exp"),
        "max_nodes": claims.get("max_nodes"),
        "max_tenants": claims.get("max_tenants"),
        "features": features,
    }


class CascadeBody(BaseModel):
    tenant_id: str = "default"
    tags: list[str]
    probe_vector: list[float] | None = None
    reason: str = "manual"


class GuardPolicyBody(BaseModel):
    tenant_id: str = "default"
    policy: dict[str, Any]


class ResolveBody(BaseModel):
    resolution: dict[str, Any] = Field(default_factory=dict)
    tenant_id: str = "default"


class AssistantBody(BaseModel):
    question: str
    tenant_id: str = "default"
    confirm: bool = False
    execute: dict[str, Any] | None = None


class LedgerBatchBody(BaseModel):
    node_id: str
    tenant_id: str = "default"
    run_ids: list[str] = Field(default_factory=list)
    entries: list[dict[str, Any]]
    truncated: bool = False


class LexiconBody(BaseModel):
    tenant_id: str = "default"
    terms: list[str]


class MemoryQueryBody(BaseModel):
    tenant_id: str = "default"
    query: str = ""
    ts: float | None = None


class IncidentBody(BaseModel):
    tenant_id: str = "default"
    title: str
    details: dict[str, Any] = Field(default_factory=dict)


# --- Overview / health ---


@router.get("/health/matrix")
async def health_matrix(request: Request):
    s = state(request)
    await s.refresh_license()
    lic = s.license_status.state
    nodes = await s.fleet.list_nodes()
    dogfood = await s.graph.dogfood()
    live_any = any(v.startswith("live") for v in s.adapter_sources.values())
    pg_ok = True
    if s.settings.database_url and s.postgres is not None:
        pg_ok = await s.postgres.ping()
    elif s.settings.database_url:
        pg_ok = False
    return {
        "L0": {"name": "process", "ok": True},
        "L1": {"name": "license", "ok": lic in ("valid", "grace"), "state": lic},
        "L2": {
            "name": "sqlite_or_postgres",
            "ok": pg_ok,
            "sqlite": True,
            "postgres": bool(s.settings.database_url),
        },
        "L3": {"name": "fabric_or_http", "ok": True, "primary": s.settings.transport_primary},
        "L4": {"name": "workers", "ok": bool(dogfood.get("ok", True)), "count": len(nodes), "dogfood": dogfood},
        "L5": {
            "name": "prism_pack",
            "ok": True,
            "demo": not live_any or s.settings.demo_mode,
            "sources": s.adapter_sources,
        },
    }


@router.get("/health/caps")
async def health_caps(request: Request):
    return await aggregate_caps(state(request))


@router.get("/metrics/token-tax")
async def token_tax(request: Request):
    return await state(request).cache.get_metrics()


@router.get("/metrics/ai-score")
async def ai_score(request: Request):
    s = state(request)
    caps = await aggregate_caps(s)
    metrics = await s.cache.get_metrics()
    incidents = await s.store.fetchall("SELECT incident_id FROM incidents")
    return compute_ai_score(caps, metrics, len(incidents))


@router.get("/metrics/prismdriver")
async def prismdriver(request: Request):
    s = state(request)
    fn = getattr(s.graph, "driver_latency", None)
    if fn:
        return await fn()
    return {"p50_ms": None, "note": "driver stats unavailable", "demo": True}


@router.get("/status/dogfood")
async def status_dogfood(request: Request):
    return await state(request).graph.dogfood()


@router.post("/metrics/cold-audit")
async def cold_audit(request: Request, _=require_role("operator")):
    body = await request.json()
    queries = body.get("queries") or []
    return {
        "simulated": True,
        "query_count": len(queries),
        "estimated_cache_hits": int(len(queries) * 0.7),
        "note": "chorusgraph-audit-style simulation; DEMO when NullAdapters",
        "demo": state(request).adapter_sources.get("graph") == "null",
    }


# --- Fleet ---


@router.get("/fleet/nodes")
async def fleet_nodes(request: Request, _=require_role("viewer")):
    s = state(request)
    nodes = await s.fleet.list_nodes()
    drifts = await policy_drift(s)
    drift_map = {d["node_id"]: d for d in drifts}
    for n in nodes:
        n["policy_drift"] = drift_map.get(n["node_id"])
        n["features"] = sorted(s.fleet.features_for_products(n.get("products") or {}))
        n["color"] = fleet_role_color(n.get("role", ""), n.get("online", False))
    return {"nodes": nodes}


@router.get("/fleet/topology")
async def fleet_topology(request: Request, _=require_role("viewer")):
    s = state(request)
    nodes = await s.fleet.list_nodes()
    online = sum(1 for n in nodes if n.get("online"))
    total = len(nodes) or 1
    out_nodes = []
    for n in nodes:
        stats = s.node_stats.get(n["node_id"]) or {}
        out_nodes.append(
            {
                "node_id": n["node_id"],
                "role": n["role"],
                "last_health_at": n["last_seen"],
                "zone": n["network_zone"],
                "online": n["online"],
                "color": fleet_role_color(n.get("role", ""), n.get("online", False)),
                "agent_ledger_dropped_total": stats.get("ledger_dropped_total", 0),
                "products": n.get("products") or {},
            }
        )
    return {
        "nodes": out_nodes,
        "invalidation_coverage": online / total,
        "cache_contrib": True,
    }


@router.get("/fleet/consistency")
async def fleet_consistency(request: Request, cascade_id: str | None = None, _=require_role("viewer")):
    s = state(request)
    if cascade_id:
        return await s.cascade.consistency_slo(cascade_id)
    rows = await s.store.fetchall("SELECT cascade_id FROM cascades ORDER BY created_at DESC LIMIT 10")
    out = []
    for r in rows:
        out.append(await s.cascade.consistency_slo(r["cascade_id"]))
    return {"cascades": out}


@router.get("/fleet/version-snapshots")
async def version_snapshots(request: Request, node_id: str | None = None, _=require_role("viewer")):
    s = state(request)
    if node_id:
        rows = await s.store.fetchall(
            "SELECT * FROM version_snapshots WHERE node_id=? ORDER BY day DESC LIMIT 30", (node_id,)
        )
    else:
        rows = await s.store.fetchall("SELECT * FROM version_snapshots ORDER BY day DESC LIMIT 100")
    return {
        "snapshots": [{**r, "products": json.loads(r["products_json"])} for r in rows],
    }


@router.post("/fleet/join-tokens")
async def create_join_token(request: Request, principal=require_role("admin")):
    s = state(request)
    body = {}
    try:
        body = await request.json()
    except Exception:  # noqa: BLE001
        body = {}
    token = await s.fleet.create_join_token(
        ttl_seconds=int(body.get("ttl_seconds") or 3600),
        max_uses=int(body.get("max_uses") or 10),
        zone=body.get("zone"),
        node_id_bind=body.get("node_id_bind"),
    )
    await s.audit.log_action(principal.user, "fleet.join_token.create", "*", {"token_prefix": token[:6]})
    return {"join_token": token}


@router.post("/fleet/join")
async def fleet_join(body: JoinBody, request: Request):
    s = state(request)
    await s.refresh_license()
    if s.license_status.state not in ("valid", "grace") or not s.license_status.claims:
        raise HTTPException(503, detail="LICENSE_INVALID")
    if body.network_zone == "external":
        scheme = _effective_scheme(request)
        if scheme != "https" and not s.settings.allow_insecure_external:
            raise HTTPException(
                status_code=403,
                detail={"detail": "TLS_REQUIRED", "message": "external zone requires HTTPS"},
            )
        if scheme != "https" and s.settings.allow_insecure_external:
            import logging

            logging.getLogger("choruscontrol.fleet").warning(
                "allowing insecure external join (CHORUSCONTROL_ALLOW_INSECURE_EXTERNAL=1)"
            )
    try:
        result = await s.fleet.join(
            join_token=body.join_token,
            node_id=body.node_id,
            tenant_id=body.tenant_id,
            role=body.role,
            network_zone=body.network_zone,
            products=body.products,
            caps_digest=body.caps_digest,
            memory_endpoint=body.memory_endpoint,
            max_nodes=s.license_status.claims.max_nodes,
        )
    except ValueError as exc:
        raise HTTPException(400, detail=str(exc)) from exc
    await sync_from_fleet(s)
    await s.broadcast_fleet({"type": "join", "node_id": result["node_id"], "ts": time.time()})
    return result


@router.post("/fleet/heartbeat")
async def fleet_heartbeat(body: HeartbeatBody, request: Request):
    s = state(request)
    try:
        await s.fleet.heartbeat(
            node_id=body.node_id,
            session_secret=body.session_secret,
            products=body.products,
            caps_digest=body.caps_digest,
            role=body.role,
        )
    except ValueError as exc:
        raise HTTPException(401, detail=str(exc)) from exc
    dropped = body.ledger_dropped_total
    if dropped is None:
        dropped = body.agent_ledger_dropped_total
    if dropped is not None:
        s.node_stats[body.node_id] = {
            **(s.node_stats.get(body.node_id) or {}),
            "ledger_dropped_total": int(dropped),
        }
    await s.broadcast_fleet(
        {
            "type": "heartbeat",
            "node_id": body.node_id,
            "ts": time.time(),
            "agent_ledger_dropped_total": (s.node_stats.get(body.node_id) or {}).get(
                "ledger_dropped_total", 0
            ),
        }
    )
    return {"ok": True}


@router.get("/fleet/nodes/{node_id}/commands")
async def get_commands(node_id: str, request: Request, x_node_session: str = Header()):
    s = state(request)
    row = await s.store.fetchone("SELECT session_secret, revoked FROM nodes WHERE node_id=?", (node_id,))
    if not row or row["revoked"] or row["session_secret"] != x_node_session:
        raise HTTPException(401, detail="unauthorized node")
    cmds = s.pending_commands.pop(node_id, [])
    return {"commands": cmds}


@router.post("/fleet/nodes/{node_id}/command")
async def dispatch_command(node_id: str, request: Request, principal=require_role("operator")):
    s = state(request)
    _grace_block(s)
    body = await request.json()
    row = await s.store.fetchone("SELECT products_json, revoked FROM nodes WHERE node_id=?", (node_id,))
    if not row or row["revoked"]:
        raise HTTPException(404, detail="node not found")
    products = json.loads(row["products_json"])
    feats = s.fleet.features_for_products(products)
    ctype = body.get("type")
    need = {
        "INVALIDATE_CACHE": "invalidate_tags",
        "RUN_SLEEP": "cortex.sleep",
        "WARM_PARTITION": "warm_partition",
        "APPLY_GUARD_POLICY": "guard.policy",
        "REINDEX": "taxonomy.reindex",
        "RUN_REINDEX": "taxonomy.reindex",
        "REQUEST_METRICS": None,
        "DRAIN": None,
        "REVOKE": None,
    }.get(ctype)
    if need and need not in feats:
        return {"status": "nack", "reason": f"unsupported feature {need}", "features": sorted(feats)}
    if ctype == "RUN_REINDEX":
        body = {**body, "type": "RUN_REINDEX"}
    cmd = {**body, "command_id": str(uuid.uuid4())}
    s.pending_commands.setdefault(node_id, []).append(cmd)
    await s.audit.log_action(principal.user, "fleet.command", node_id, cmd)
    return {"status": "queued", "command": cmd}


@router.post("/fleet/ack")
async def fleet_ack(request: Request):
    s = state(request)
    body = await request.json()
    if body.get("cascade_id"):
        await s.cascade.record_ack(body["cascade_id"], body.get("node_id", "?"), body.get("status", "ok"))
    await s.broadcast_fleet({"type": "ack", "node_id": body.get("node_id"), "ts": time.time(), "body": body})
    return {"ok": True}


@router.post("/fleet/ledger-batch")
async def ledger_batch(body: LedgerBatchBody, request: Request):
    s = state(request)
    kept = 0
    for entry in body.entries:
        stage = (entry.get("stage") or "").lower()
        decision = (entry.get("decision") or "").lower()
        important = stage in ("guard", "shine") or decision in ("block", "flag", "error")
        import random

        drop = not important and random.random() >= s.settings.ledger_sample_rate
        if drop:
            continue
        await s.store.execute(
            "INSERT INTO ledger_entries(tenant_id, node_id, run_id, payload_json, sampled, created_at) "
            "VALUES(?,?,?,?,?,?)",
            (
                body.tenant_id,
                body.node_id,
                (body.run_ids[0] if body.run_ids else entry.get("run_id")),
                json.dumps(entry),
                1,
                time.time(),
            ),
        )
        kept += 1
        # notify WS subscribers
        for ws in list(s.trace_subscribers):
            try:
                await ws.send_json(entry)
            except Exception:  # noqa: BLE001
                pass
    return {"kept": kept, "truncated": body.truncated}


@router.delete("/fleet/nodes/{node_id}")
async def revoke_node(node_id: str, request: Request, principal=require_role("admin")):
    s = state(request)
    _grace_block(s)
    cmd = {"type": "REVOKE", "command_id": str(uuid.uuid4())}
    s.pending_commands.setdefault(node_id, []).append(cmd)
    await s.fleet.revoke(node_id)
    await s.audit.log_action(principal.user, "fleet.revoke", node_id, {})
    await s.broadcast_fleet({"type": "revoke", "node_id": node_id, "ts": time.time()})
    return {"revoked": node_id}


# --- Cascade / jobs ---


@router.post("/cascade")
async def run_cascade(body: CascadeBody, request: Request, principal=require_role("operator")):
    import asyncio

    s = state(request)
    _grace_block(s)
    job = await s.jobs.submit(
        body.tenant_id,
        "cascade.run",
        {
            "tags": body.tags,
            "probe_vector": body.probe_vector,
            "reason": body.reason,
        },
    )
    if job.state == "busy":
        raise HTTPException(409, detail={"status": "busy", "job": job.__dict__})
    for _ in range(200):
        cur = s.jobs.get(job.job_id)
        if cur and cur.state in ("completed", "failed"):
            if cur.state == "failed":
                raise HTTPException(500, detail=cur.error or "cascade job failed")
            break
        await asyncio.sleep(0.05)
    row = await s.store.fetchone(
        "SELECT * FROM cascades WHERE tenant_id=? ORDER BY created_at DESC LIMIT 1",
        (body.tenant_id,),
    )
    result = {
        "cascade_id": row["cascade_id"] if row else None,
        "job_id": job.job_id,
        "details": json.loads(row["details_json"]) if row else {},
        "state": row["state"] if row else "unknown",
    }
    if row:
        await link_cascade_incident(s.store, {"cascade_id": row["cascade_id"], **result}, body.tenant_id)
    await s.audit.log_action(principal.user, "correction_cascade", body.tenant_id, result)
    return result


@router.get("/cascade/{cascade_id}")
async def cascade_status(cascade_id: str, request: Request, _=require_role("viewer")):
    s = state(request)
    row = await s.store.fetchone("SELECT * FROM cascades WHERE cascade_id=?", (cascade_id,))
    if not row:
        raise HTTPException(404)
    slo = await s.cascade.consistency_slo(cascade_id)
    return {**row, "details": json.loads(row["details_json"]), "consistency": slo}


@router.post("/jobs/sleep")
async def job_sleep(request: Request, principal=require_role("operator")):
    body = await request.json()
    tenant_id = body.get("tenant_id", "default")
    s = state(request)
    _grace_block(s)
    job = await s.jobs.trigger_sleep(tenant_id)
    await s.audit.log_action(principal.user, "job.sleep", tenant_id, {"job_id": job.job_id})
    return job.__dict__


@router.post("/jobs/reindex")
async def job_reindex(request: Request, principal=require_role("operator")):
    body = await request.json()
    s = state(request)
    _grace_block(s)
    job = await s.jobs.trigger_reindex(body.get("tenant_id", "default"), body.get("category_id"))
    return job.__dict__


@router.post("/jobs/warm-partition")
async def job_warm(request: Request, principal=require_role("operator")):
    body = await request.json()
    s = state(request)
    _grace_block(s)
    job = await s.jobs.trigger_warm(body.get("tenant_id", "default"), body.get("partition"))
    await s.audit.log_action(principal.user, "job.warm", body.get("tenant_id", "default"), {"job_id": job.job_id})
    return job.__dict__


@router.get("/jobs/{job_id}")
async def job_get(job_id: str, request: Request, _=require_role("viewer")):
    job = state(request).jobs.get(job_id)
    if not job:
        raise HTTPException(404)
    return job.__dict__


# --- Memory ---


@router.get("/memory/facts")
async def memory_facts(request: Request, tenant_id: str = "default", _=require_role("viewer")):
    s = state(request)
    endpoint = await s.fleet.memory_endpoint_for_tenant(tenant_id)
    facts = await s.cortex.facts(tenant_id)
    return {"memory_endpoint": endpoint, "facts": facts}


@router.get("/memory/conflicts")
async def memory_conflicts(request: Request, tenant_id: str = "default", _=require_role("viewer")):
    s = state(request)
    endpoint = await s.fleet.memory_endpoint_for_tenant(tenant_id)
    return {"memory_endpoint": endpoint, "conflicts": await s.cortex.conflicts(tenant_id)}


@router.post("/memory/conflicts/{conflict_id}/resolve")
async def resolve_conflict(
    conflict_id: str, body: ResolveBody, request: Request, principal=require_role("operator")
):
    s = state(request)
    _grace_block(s)
    tenant_id = body.tenant_id
    resolved = await s.cortex.resolve_conflict(tenant_id, conflict_id, body.resolution)
    cascade = await s.cascade.run(
        tenant_id, tags=[f"conflict:{conflict_id}", f"tenant:{tenant_id}"], reason="conflict_resolve"
    )
    await link_cascade_incident(s.store, cascade, tenant_id)
    await s.audit.log_action(
        principal.user, "memory.conflict.resolve", tenant_id, {"conflict_id": conflict_id, "cascade": cascade}
    )
    return {"resolved": resolved, "cascade": cascade}


@router.post("/memory/explain")
async def memory_explain(body: MemoryQueryBody, request: Request, _=require_role("viewer")):
    s = state(request)
    fn = getattr(s.cortex, "explain", None)
    if not fn:
        raise HTTPException(501, detail="explain not available")
    return await fn(body.tenant_id, body.query)


@router.post("/memory/recall_at")
async def memory_recall_at(body: MemoryQueryBody, request: Request, _=require_role("viewer")):
    s = state(request)
    fn = getattr(s.cortex, "recall_at", None)
    if not fn:
        raise HTTPException(501, detail="recall_at not available")
    return await fn(body.tenant_id, body.ts or time.time(), body.query)


@router.get("/memory/cascade/{cascade_id}")
async def memory_cascade(cascade_id: str, request: Request, _=require_role("viewer")):
    return await cascade_status(cascade_id, request)


# --- Taxonomy ---


@router.get("/taxonomy/tree")
async def taxonomy_tree(request: Request, tenant_id: str = "default", _=require_role("viewer")):
    return await state(request).rag.tree(tenant_id)


@router.post("/taxonomy/search")
async def taxonomy_search(request: Request, _=require_role("viewer")):
    body = await request.json()
    return {
        "results": await state(request).rag.search(body.get("tenant_id", "default"), body.get("query", ""))
    }


@router.get("/taxonomy/partitions")
async def taxonomy_partitions(request: Request, tenant_id: str = "default", _=require_role("viewer")):
    return {"partitions": await state(request).rag.partitions(tenant_id)}


@router.get("/taxonomy/chunks/health")
async def taxonomy_chunks(request: Request, tenant_id: str = "default", _=require_role("viewer")):
    s = state(request)
    fn = getattr(s.rag, "chunks_health", None)
    if fn:
        return await fn(tenant_id)
    return {"tenant_id": tenant_id, "decay": [], "demo": True}


# --- Guard ---


@router.get("/guard/logs")
async def guard_logs(request: Request, _=require_role("viewer")):
    return {"logs": await state(request).guard.recent_logs()}


@router.get("/guard/policy")
async def get_policy(request: Request, tenant_id: str = "default", _=require_role("viewer")):
    s = state(request)
    row = await s.store.fetchone("SELECT policy_json FROM guard_policies WHERE tenant_id=?", (tenant_id,))
    if not row:
        return {"policy": s.intended_policies.get("default")}
    return {"policy": json.loads(row["policy_json"])}


@router.put("/guard/policy")
async def put_policy(body: GuardPolicyBody, request: Request, principal=require_role("security")):
    s = state(request)
    _grace_block(s)
    try:
        pol = validate_guard_policy(body.policy)
    except PolicyValidationError as exc:
        raise HTTPException(400, detail={"code": exc.code, "message": str(exc)}) from exc
    await s.store.execute(
        "INSERT INTO guard_policies(tenant_id, policy_json, updated_at) VALUES(?,?,?) "
        "ON CONFLICT(tenant_id) DO UPDATE SET policy_json=excluded.policy_json, updated_at=excluded.updated_at",
        (body.tenant_id, json.dumps(pol), time.time()),
    )
    s.intended_policies[body.tenant_id] = pol
    await s.audit.log_action(principal.user, "guard.policy.update", body.tenant_id, pol)
    return {"ok": True, "policy": pol}


@router.get("/guard/shadow/compare")
async def shadow_compare(
    request: Request,
    tenant_id: str = "default",
    _=require_role("viewer"),
    feat=require_feature("guard.shadow"),
):
    s = state(request)
    row = await s.store.fetchone("SELECT policy_json FROM guard_policies WHERE tenant_id=?", (tenant_id,))
    pol = json.loads(row["policy_json"]) if row else s.intended_policies.get("default", {})
    fn = getattr(s.guard, "shadow_compare", None)
    if fn:
        out = await fn(pol.get("ingress_profile", "web_chat"), pol.get("shadow_profile", "light"))
    else:
        out = {"agree_rate": 0.0, "demo": True}
    if feat.get("demo"):
        out = {**out, "demo": True}
    return out


@router.post("/guard/shadow/promote")
async def shadow_promote(
    request: Request,
    principal=require_role("security"),
    _feat=require_feature("guard.shadow"),
):
    s = state(request)
    _grace_block(s)
    body = await request.json()
    tenant_id = body.get("tenant_id", "default")
    row = await s.store.fetchone("SELECT policy_json FROM guard_policies WHERE tenant_id=?", (tenant_id,))
    pol = json.loads(row["policy_json"]) if row else dict(s.intended_policies.get("default", {}))
    fn = getattr(s.guard, "shadow_compare", None)
    compare = (
        await fn(pol.get("ingress_profile", "web_chat"), pol.get("shadow_profile", "light"))
        if fn
        else {"agree_rate": 0.0}
    )
    checklist = shadow_promote_checklist(pol, compare)
    if not checklist["ready"]:
        raise HTTPException(400, detail={"message": "promote checklist failed", **checklist})
    pol["enforce_shadow"] = True
    try:
        pol = validate_guard_policy(pol)
    except PolicyValidationError as exc:
        raise HTTPException(400, detail={"code": exc.code, "message": str(exc)}) from exc
    await s.store.execute(
        "INSERT INTO guard_policies(tenant_id, policy_json, updated_at) VALUES(?,?,?) "
        "ON CONFLICT(tenant_id) DO UPDATE SET policy_json=excluded.policy_json, updated_at=excluded.updated_at",
        (tenant_id, json.dumps(pol), time.time()),
    )
    s.intended_policies[tenant_id] = pol
    await s.audit.log_action(principal.user, "guard.shadow.promote", tenant_id, pol)
    return {"ok": True, "checklist": checklist, "policy": pol, "demo": s.settings.demo_mode}


@router.get("/guard/lexicon")
async def get_lexicon(request: Request, tenant_id: str = "default", _=require_role("viewer")):
    s = state(request)
    row = await s.store.fetchone("SELECT terms_json FROM guard_lexicons WHERE tenant_id=?", (tenant_id,))
    if row:
        return {"tenant_id": tenant_id, "terms": json.loads(row["terms_json"])}
    fn = getattr(s.guard, "get_lexicon", None)
    if fn:
        return {"tenant_id": tenant_id, "terms": await fn(tenant_id)}
    return {"tenant_id": tenant_id, "terms": []}


@router.put("/guard/lexicon")
async def put_lexicon(body: LexiconBody, request: Request, principal=require_role("security")):
    s = state(request)
    _grace_block(s)
    await s.store.execute(
        "INSERT INTO guard_lexicons(tenant_id, terms_json, updated_at) VALUES(?,?,?) "
        "ON CONFLICT(tenant_id) DO UPDATE SET terms_json=excluded.terms_json, updated_at=excluded.updated_at",
        (body.tenant_id, json.dumps(body.terms), time.time()),
    )
    fn = getattr(s.guard, "put_lexicon", None)
    if fn:
        await fn(body.tenant_id, body.terms)
    await s.audit.log_action(principal.user, "guard.lexicon.update", body.tenant_id, {"terms": body.terms})
    return {"ok": True, "terms": body.terms}


@router.post("/guard/caps")
async def guard_caps_live(request: Request, _=require_role("viewer")):
    body = await request.json()
    profile = body.get("profile", "web_chat")
    return await state(request).guard.caps(profile)


# --- Admin ---


@router.get("/admin/license")
async def admin_license(request: Request, _=require_role("viewer")):
    s = state(request)
    await s.refresh_license()
    st = s.license_status
    claims = None
    if st.claims:
        claims = st.claims.model_dump()
        if isinstance(claims.get("features"), set):
            claims["features"] = sorted(claims["features"])
    return {
        "state": st.state,
        "message": st.message,
        "claims": claims,
        "seconds_to_exp": st.seconds_to_exp,
        "grace_remaining_seconds": st.grace_remaining_seconds,
        "support_url": s.settings.insightits_support_url,
        "portal_url": s.settings.insightits_portal_url,
        "stack": {
            "adapters": s.adapter_sources,
            "pins_summary": {
                "any_live": any(v.startswith("live") for v in s.adapter_sources.values()),
                "demo_mode": s.settings.demo_mode,
            },
        },
    }


@router.post("/admin/license")
async def admin_license_install(
    body: LicenseInstallBody, request: Request, principal=require_role("admin")
):
    s = state(request)
    _grace_block(s)
    status = s.license_verifier.verify(body.license_key)
    if status.state not in ("valid", "grace"):
        raise HTTPException(400, detail={"message": status.message, "state": status.state})
    save_stored_license(s.settings, body.license_key)
    s.settings.license_key = body.license_key
    s.license_status = status
    await s.audit.log_action(
        principal.user,
        "admin.license.install",
        "*",
        {"state": status.state, "license_id": status.claims.license_id if status.claims else None},
    )
    return {
        "ok": True,
        "state": status.state,
        "message": status.message,
        "claims": _redact_license_claims(status.claims.model_dump() if status.claims else None),
    }


@router.get("/admin/stack-licenses")
async def admin_stack_licenses(request: Request, _=require_role("viewer")):
    return stack_license_status()


@router.get("/admin/tenants")
async def admin_tenants_list(request: Request, _=require_role("admin")):
    return {"tenants": await list_tenants(state(request).store)}


@router.post("/admin/tenants")
async def admin_tenants_create(body: TenantBody, request: Request, principal=require_role("admin")):
    s = state(request)
    _grace_block(s)
    await s.refresh_license()
    if not s.license_status.claims:
        raise HTTPException(503, detail="LICENSE_INVALID")
    try:
        tenant = await create_tenant(
            s.store,
            tenant_id=body.tenant_id,
            name=body.name or body.tenant_id,
            settings=body.settings,
            max_tenants=s.license_status.claims.max_tenants,
        )
    except ValueError as exc:
        msg = str(exc)
        if msg == "TENANT_LIMIT":
            raise HTTPException(403, detail={"detail": "TENANT_LIMIT", "max_tenants": s.license_status.claims.max_tenants}) from exc
        raise HTTPException(400, detail=msg) from exc
    await s.audit.log_action(principal.user, "admin.tenant.create", body.tenant_id, tenant)
    return tenant


@router.delete("/admin/tenants/{tenant_id}")
async def admin_tenants_delete(tenant_id: str, request: Request, principal=require_role("admin")):
    s = state(request)
    _grace_block(s)
    try:
        await delete_tenant(s.store, tenant_id)
    except ValueError as exc:
        raise HTTPException(400, detail=str(exc)) from exc
    await s.audit.log_action(principal.user, "admin.tenant.delete", tenant_id, {})
    return {"deleted": tenant_id}


@router.get("/admin/doctor")
async def admin_doctor(request: Request, _=require_role("admin")):
    return await doctor_mother(state(request))


@router.get("/admin/auth")
async def admin_auth(request: Request):
    """Auth modes available. In demo_mode, include token hint so UI can self-heal."""
    s = state(request).settings
    out = {
        "local_token": True,
        "oidc_enabled": s.oidc_enabled,
        "oidc_issuer": s.oidc_issuer,
        "oidc_audience": s.oidc_audience,
        "oidc_role_claim": s.oidc_role_claim,
        "demo_mode": s.demo_mode,
        "formats": [
            "Bearer <ADMIN_TOKEN>",
            "Bearer <ADMIN_TOKEN>:<role>",
            "Bearer <ADMIN_TOKEN>|<user>|<role>",
            "Bearer <OIDC_JWT> when OIDC enabled",
        ],
    }
    if s.demo_mode:
        # Local/demo only — never expose outside demo_mode
        out["demo_token"] = s.admin_token
        out["demo_token_candidates"] = list(
            dict.fromkeys(
                [
                    s.admin_token,
                    "healthcare-demo-token",
                    "dev-admin-token",
                ]
            )
        )
    return out



@router.get("/metrics/series")
async def metrics_series(request: Request, name: str = "cache.hit_rate", limit: int = 120, _=require_role("viewer")):
    from choruscontrol.services.metrics import series

    return {"name": name, "points": await series(state(request).store, name, limit)}


async def _build_soc2_zip(s) -> io.BytesIO:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        audit_path = s.settings.audit_log_path
        if audit_path.exists():
            zf.write(audit_path, arcname="audit.jsonl")
        else:
            zf.writestr("audit.jsonl", "")
        zf.writestr("audit_public_key.pem", s.audit.public_pem)
        caps = await aggregate_caps(s)
        zf.writestr("caps_snapshot.json", json.dumps(caps, indent=2, default=str))
        claims = None
        if s.license_status.claims:
            claims = _redact_license_claims(s.license_status.claims.model_dump())
        lic = {"state": s.license_status.state, "claims": claims}
        zf.writestr("license.json", json.dumps(lic, indent=2, default=str))
        doc = await doctor_mother(s)
        zf.writestr("doctor.json", json.dumps(doc, indent=2, default=str))
        zf.writestr(
            "README.txt",
            "ChorusControl SOC2 export pack\n"
            "Verify audit with: choruscontrol audit-verify audit.jsonl --pubkey audit_public_key.pem\n",
        )
    buf.seek(0)
    return buf


@router.get("/admin/soc2-export")
async def soc2_export(
    request: Request,
    principal=require_role("admin"),
    _feat=require_feature("audit.export"),
):
    from fastapi.responses import StreamingResponse

    s = state(request)
    buf = await _build_soc2_zip(s)
    await s.audit.log_action(principal.user, "admin.soc2_export", "*", {})
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=choruscontrol-soc2.zip"},
    )


@router.get("/admin/export/soc2-pack")
async def soc2_export_alias(
    request: Request,
    principal=require_role("admin"),
    _feat=require_feature("audit.export"),
):
    from fastapi.responses import StreamingResponse

    s = state(request)
    buf = await _build_soc2_zip(s)
    await s.audit.log_action(principal.user, "admin.soc2_export", "*", {"alias": True})
    return StreamingResponse(
        buf,
        media_type="application/zip",
        headers={"Content-Disposition": "attachment; filename=choruscontrol-soc2.zip"},
    )


@router.get("/admin/audit/export")
async def audit_export(
    request: Request,
    since: float | None = None,
    principal=require_role("admin"),
    _feat=require_feature("audit.export"),
):
    from fastapi.responses import StreamingResponse

    s = state(request)
    path = s.settings.audit_log_path

    def _iter():
        if not path.exists():
            return
        with open(path, encoding="utf-8") as f:
            for line in f:
                if not line.strip():
                    continue
                if since is not None:
                    try:
                        env = json.loads(line)
                        if float(env.get("timestamp") or 0) < since:
                            continue
                    except Exception:  # noqa: BLE001
                        continue
                yield line if line.endswith("\n") else line + "\n"

    await s.audit.log_action(principal.user, "admin.audit.export", "*", {"since": since})
    return StreamingResponse(
        _iter(),
        media_type="application/x-ndjson",
        headers={"Content-Disposition": "attachment; filename=audit-export.jsonl"},
    )


# --- Graph / assistant / incidents ---


@router.get("/graph")
async def get_graph(request: Request, tenant_id: str | None = None, _=require_role("viewer")):
    await sync_from_fleet(state(request))
    return await graph_query(state(request).store, tenant_id)


@router.get("/pipelines/live")
async def pipelines_live(request: Request, _=require_role("viewer")):
    """Interactive dashboard visuals — execution wire, fleet, cascade, asset graph."""
    s = state(request)
    await sync_from_fleet(s)
    return await live_pipelines(s)


@router.get("/graph/blast-radius")
async def graph_blast(request: Request, asset_id: str, _=require_role("viewer")):
    return await blast_radius(state(request).store, asset_id)


@router.post("/assistant/ask")
async def assistant(body: AssistantBody, request: Request, principal=require_role("operator")):
    return await assistant_ask(
        state(request),
        body.question,
        principal.user,
        confirm=body.confirm,
        execute=body.execute,
    )


@router.get("/recommendations")
async def get_recommendations(request: Request, _=require_role("viewer")):
    return await recommendations(state(request))


@router.get("/policy/drift")
async def get_drift(request: Request, _=require_role("viewer")):
    return {"drifts": await policy_drift(state(request))}


@router.get("/incidents")
async def incidents_list(request: Request, tenant_id: str | None = None, _=require_role("viewer")):
    return {"incidents": await list_incidents(state(request).store, tenant_id)}


@router.get("/incidents/{incident_id}")
async def incidents_get(incident_id: str, request: Request, _=require_role("viewer")):
    row = await get_incident(state(request).store, incident_id)
    if not row:
        raise HTTPException(404)
    return row


@router.post("/incidents")
async def incidents_create(body: IncidentBody, request: Request, principal=require_role("operator")):
    s = state(request)
    _grace_block(s)
    inc = await create_incident(s.store, tenant_id=body.tenant_id, title=body.title, details=body.details)
    await s.audit.log_action(principal.user, "incident.create", body.tenant_id, inc)
    return inc


# --- Traces ---


@router.get("/traces/recent")
async def traces_recent(request: Request, tenant_id: str = "default", _=require_role("viewer")):
    s = state(request)
    traces = await list_traces(s.store, tenant_id)
    rows = await s.store.fetchall(
        "SELECT * FROM ledger_entries WHERE tenant_id=? ORDER BY id DESC LIMIT 100",
        (tenant_id,),
    )
    return {
        "traces": traces,
        "entries": [{**r, "payload": json.loads(r["payload_json"])} for r in rows],
        "wire": "guard -> ledger -> shine",
    }


@router.get("/traces/{run_id}")
async def traces_get(run_id: str, request: Request, _=require_role("viewer")):
    tr = await get_trace(state(request).store, run_id)
    if not tr:
        raise HTTPException(404)
    return tr


@router.get("/traces/{run_id}/ledger")
async def traces_ledger(run_id: str, request: Request, _=require_role("viewer")):
    return {"run_id": run_id, "ledger": await get_ledger(state(request).store, run_id)}


@router.post("/traces/{run_id}/replay")
async def traces_replay(
    run_id: str,
    request: Request,
    _=require_role("operator"),
    feat=require_feature("trace.replay"),
):
    try:
        out = await replay_trace(state(request).store, run_id)
    except KeyError as exc:
        raise HTTPException(404) from exc
    if feat.get("demo"):
        out = {**out, "demo": True}
    return out


@router.post("/traces/seed")
async def traces_seed(request: Request, principal=require_role("operator")):
    body = await request.json()
    run_id = await seed_demo_trace(state(request).store, body.get("tenant_id", "default"))
    await state(request).audit.log_action(principal.user, "trace.seed", "default", {"run_id": run_id})
    return {"run_id": run_id}


@router.websocket("/fleet/live")
async def fleet_live(websocket: WebSocket):
    await websocket.accept()
    app = websocket.app
    cc = getattr(app.state, "cc", None)
    if cc is None:
        await websocket.close()
        return
    cc.fleet_subscribers.append(websocket)
    try:
        nodes = await cc.fleet.list_nodes()
        await websocket.send_json(
            {
                "type": "snapshot",
                "nodes": [
                    {
                        "node_id": n["node_id"],
                        "role": n["role"],
                        "online": n["online"],
                        "zone": n["network_zone"],
                        "agent_ledger_dropped_total": (cc.node_stats.get(n["node_id"]) or {}).get(
                            "ledger_dropped_total", 0
                        ),
                    }
                    for n in nodes
                ],
                "invalidation_coverage": (sum(1 for n in nodes if n.get("online")) / (len(nodes) or 1)),
            }
        )
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        if websocket in cc.fleet_subscribers:
            cc.fleet_subscribers.remove(websocket)


@router.websocket("/traces/live")
async def traces_live(websocket: WebSocket):
    await websocket.accept()
    app = websocket.app
    cc = getattr(app.state, "cc", None)
    if cc is None:
        await websocket.close()
        return
    cc.trace_subscribers.append(websocket)
    try:
        await websocket.send_json({"type": "hello", "wire": "guard -> ledger -> shine"})
        while True:
            # keep alive; client may send ping
            await websocket.receive_text()
    except WebSocketDisconnect:
        pass
    finally:
        if websocket in cc.trace_subscribers:
            cc.trace_subscribers.remove(websocket)
