from __future__ import annotations

import json
import time
import uuid
from typing import Any


async def upsert_asset(store, *, kind: str, tenant_id: str, name: str, meta: dict[str, Any]) -> str:
    asset_id = f"{kind}:{tenant_id}:{name}"
    await store.execute(
        "INSERT INTO assets(asset_id, kind, tenant_id, name, meta_json, updated_at) VALUES(?,?,?,?,?,?) "
        "ON CONFLICT(asset_id) DO UPDATE SET meta_json=excluded.meta_json, updated_at=excluded.updated_at",
        (asset_id, kind, tenant_id, name, json.dumps(meta), time.time()),
    )
    return asset_id


async def add_edge(store, src: str, dst: str, rel: str) -> None:
    await store.execute(
        "INSERT OR IGNORE INTO asset_edges(src, dst, rel) VALUES(?,?,?)",
        (src, dst, rel),
    )


async def sync_from_fleet(state) -> dict[str, Any]:
    """Asset Graph v1 — nodes/edges from fleet inventory + policies + partitions."""
    org = await upsert_asset(
        state.store,
        kind="organization",
        tenant_id="*",
        name=state.license_status.claims.sub if state.license_status.claims else "unknown",
        meta={"tier": state.license_status.claims.tier if state.license_status.claims else None},
    )
    nodes = await state.fleet.list_nodes()
    created = 0
    for n in nodes:
        agent_id = await upsert_asset(
            state.store,
            kind="agent",
            tenant_id=n["tenant_id"],
            name=n["node_id"],
            meta={"role": n["role"], "zone": n["network_zone"], "products": n["products"]},
        )
        await add_edge(state.store, org, agent_id, "contains")
        for prod, ver in (n["products"] or {}).items():
            pid = await upsert_asset(
                state.store,
                kind="product",
                tenant_id=n["tenant_id"],
                name=f"{n['node_id']}/{prod}",
                meta={"version": ver},
            )
            await add_edge(state.store, agent_id, pid, "runs")
            created += 1
        pol = state.intended_policies.get(n["tenant_id"]) or state.intended_policies.get("default")
        if pol:
            policy_id = await upsert_asset(
                state.store,
                kind="policy",
                tenant_id=n["tenant_id"],
                name="guard",
                meta=pol,
            )
            await add_edge(state.store, agent_id, policy_id, "governed_by")
        try:
            parts = await state.rag.partitions(n["tenant_id"])
            for p in parts:
                kid = await upsert_asset(
                    state.store,
                    kind="knowledge_base",
                    tenant_id=n["tenant_id"],
                    name=p.get("partition", "kb"),
                    meta=p,
                )
                await add_edge(state.store, agent_id, kid, "uses")
                await add_edge(state.store, kid, agent_id, "depends_on")
        except Exception:  # noqa: BLE001
            pass
    return {"organization": org, "agents": len(nodes), "product_assets": created}


async def graph_query(store, tenant_id: str | None = None) -> dict[str, Any]:
    if tenant_id:
        assets = await store.fetchall(
            "SELECT * FROM assets WHERE tenant_id=? OR tenant_id='*'", (tenant_id,)
        )
    else:
        assets = await store.fetchall("SELECT * FROM assets")
    edges = await store.fetchall("SELECT * FROM asset_edges")
    return {
        "assets": [{**a, "meta": json.loads(a["meta_json"])} for a in assets],
        "edges": edges,
    }


async def blast_radius(store, asset_id: str) -> dict[str, Any]:
    """What depends on this asset / what it impacts."""
    outbound = await store.fetchall(
        "SELECT * FROM asset_edges WHERE src=?", (asset_id,)
    )
    inbound = await store.fetchall(
        "SELECT * FROM asset_edges WHERE dst=?", (asset_id,)
    )
    related_ids = {asset_id}
    for e in outbound + inbound:
        related_ids.add(e["src"])
        related_ids.add(e["dst"])
    assets = []
    for aid in related_ids:
        row = await store.fetchone("SELECT * FROM assets WHERE asset_id=?", (aid,))
        if row:
            assets.append({**row, "meta": json.loads(row["meta_json"])})
    return {
        "asset_id": asset_id,
        "depends_on": [e for e in outbound if e["rel"] in ("depends_on", "uses", "runs")],
        "impacted_by": inbound,
        "impacts": outbound,
        "assets": assets,
    }


async def assistant_ask(
    state,
    question: str,
    principal_user: str,
    *,
    confirm: bool = False,
    execute: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Ops Assistant — grounded answers; gated execute via same APIs + audit."""
    q = question.lower()
    graph = await graph_query(state.store)
    nodes = await state.fleet.list_nodes()
    from choruscontrol.services.caps import aggregate_caps, policy_drift

    caps = await aggregate_caps(state)
    answer = "I can help with fleet, policies, incidents, cost, cascades, and blast radius."
    actions: list[dict[str, Any]] = []
    execution: dict[str, Any] | None = None

    if "fail" in q or "incident" in q:
        incidents = await state.store.fetchall(
            "SELECT * FROM incidents ORDER BY created_at DESC LIMIT 5"
        )
        answer = f"Found {len(incidents)} recent incidents. Latest: " + (
            incidents[0]["title"] if incidents else "none"
        )
    elif "cost" in q:
        metrics = await state.cache.get_metrics()
        answer = f"Estimated cache savings ${metrics.get('cost_saved_usd', 0)} (demo={metrics.get('demo')})."
    elif "stale" in q or "knowledge" in q:
        answer = "Check Taxonomy partitions and PrismRAG chunk health; warm_partition if versions lag."
        actions.append(
            {
                "type": "job",
                "command": "taxonomy.warm_partition",
                "requires_confirmation": True,
                "params": {"tenant_id": "default", "partition": "kb_markdown"},
            }
        )
    elif "policy" in q:
        drifts = await policy_drift(state)
        drifted = [d for d in drifts if d["drift"]]
        answer = f"Policy drift on {len(drifted)} / {len(drifts)} nodes."
    elif "architecture" in q or "graph" in q or "blast" in q:
        answer = (
            f"Asset graph has {len(graph['assets'])} assets and {len(graph['edges'])} edges; "
            f"{len(nodes)} agents. Open Overview to explore the interactive Asset Graph map."
        )
    elif "pipeline" in q or "trace" in q or "wire" in q or "flow" in q:
        from choruscontrol.services.pipelines import live_pipelines

        pipe = await live_pipelines(state)
        stages = pipe.get("execution", {}).get("stages") or []
        labels = " → ".join(s.get("label", "?") for s in stages) or "Guard → Ledger → Shine"
        answer = (
            f"Live execution pipeline: {labels}. "
            f"Run {pipe.get('execution', {}).get('run_id') or 'none yet'}. "
            f"Fleet nodes in topology: {len(pipe.get('fleet') or [])}."
        )
    elif "score" in q or "health" in q:
        metrics = await state.cache.get_metrics()
        from choruscontrol.services.caps import compute_ai_score

        score = compute_ai_score(caps, metrics, 0)
        answer = (
            f"AI Score is {score['overall']} "
            f"({'demo inputs' if score.get('demo') else 'live formula'}). "
            f"Top dimension peek: performance={score['dimensions'].get('performance')}."
        )
    elif "fleet" in q or "agent" in q or "node" in q:
        online = sum(1 for n in nodes if n.get("online"))
        answer = f"Fleet has {len(nodes)} enrolled node(s), {online} online. Colors: GREEN/BLUE workers, ORANGE when stale."
    elif "upgrade" in q or "reindex" in q:
        answer = "Reindex/model upgrades are gated. Confirm with operator role."
        actions.append(
            {
                "type": "job",
                "command": "taxonomy.reindex",
                "requires_confirmation": True,
                "params": {"tenant_id": "default"},
            }
        )
    elif "cascade" in q:
        answer = "Correction cascade invalidates tags across the fleet. Confirm to run."
        actions.append(
            {
                "type": "cascade",
                "requires_confirmation": True,
                "params": {"tenant_id": "default", "tags": ["assistant:manual"], "reason": "assistant"},
            }
        )

    if execute:
        if not confirm:
            execution = {"status": "needs_confirmation", "execute": execute}
        else:
            # Feature gate
            feats = set(state.license_status.claims.features) if state.license_status.claims else set()
            if "assistant.ops" not in feats and not state.settings.demo_mode:
                execution = {"status": "denied", "reason": "feature assistant.ops required"}
            elif state.license_status.state == "grace":
                execution = {"status": "denied", "reason": "license grace: mutations blocked"}
            else:
                etype = execute.get("type") or execute.get("command")
                if etype in ("taxonomy.reindex", "job") and (
                    execute.get("command") == "taxonomy.reindex" or etype == "taxonomy.reindex"
                ):
                    job = await state.jobs.trigger_reindex(execute.get("params", {}).get("tenant_id", "default"))
                    execution = {"status": "ok", "job": job.__dict__}
                elif execute.get("command") == "taxonomy.warm_partition" or etype == "taxonomy.warm_partition":
                    params = execute.get("params") or {}
                    job = await state.jobs.trigger_warm(
                        params.get("tenant_id", "default"), params.get("partition")
                    )
                    execution = {"status": "ok", "job": job.__dict__}
                elif etype == "cascade" or execute.get("type") == "cascade":
                    params = execute.get("params") or {}
                    result = await state.cascade.run(
                        params.get("tenant_id", "default"),
                        params.get("tags") or ["assistant"],
                        reason=params.get("reason", "assistant"),
                    )
                    execution = {"status": "ok", "cascade": result}
                else:
                    execution = {"status": "nack", "reason": f"unsupported execute {execute}"}
                await state.audit.log_action(
                    principal_user, "assistant.execute", "default", {"execute": execute, "result": execution}
                )

    await state.audit.log_action(
        principal_user, "assistant.ask", "default", {"question": question, "answer": answer}
    )
    return {
        "answer": answer,
        "grounding": {
            "assets": len(graph["assets"]),
            "nodes": len(nodes),
            "caps_tier": caps.get("license"),
        },
        "actions": actions,
        "execution": execution,
        "disclaimer": "Assistant uses platform telemetry only; PASS/ALLOW ≠ world-true.",
    }


async def recommendations(state) -> dict[str, Any]:
    """Predictive + RCA recommendations from retained metric samples."""
    from choruscontrol.services.metrics import predictive_recommendations

    return await predictive_recommendations(state)
