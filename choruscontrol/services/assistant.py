"""Ops Assistant - grounded in live dashboard telemetry with plain-English explanations."""

from __future__ import annotations

import json
import time
from typing import Any

from choruscontrol.services.assistant_knowledge import (
    AGENT_CATALOG,
    PLATFORM_BRIEF,
    ROLE_PLAIN,
    enrich_node,
    explain_agent,
    explain_fleet,
    explain_role,
    find_live_node,
    match_catalog_from_question,
)

# Human glossary for every Overview number the UI shows.
DIMENSION_PLAIN = {
    "security": {
        "label": "Security",
        "means": "How strong Guard ingress protection looks for the active profile.",
        "how": "Higher when Guard reports a real profile. Hub profiles like clinical_chat/web_chat score ~75 (light ingress, not a full law/heavy scorecard).",
        "good": "70+",
        "bad": "Below 50 usually means Guard caps are missing.",
    },
    "governance": {
        "label": "Governance",
        "means": "Whether the platform is running under a valid (or grace) license with enforceable policy.",
        "how": "About 85 when license is valid/grace; collapses near 20 if license is missing/invalid.",
        "good": "80+",
        "bad": "Low means renew or install a license (Admin -> License).",
    },
    "reliability": {
        "label": "Reliability",
        "means": "Stability signal from open incidents - each open incident knocks 5 points off 100.",
        "how": "100 - (open_incidents x 5), floored at 0. Two open incidents -> 90; twenty -> 0.",
        "good": "90+ (few or no open incidents)",
        "bad": "0 means many open incidents (common in the Aurora Health DEMO after med-recon seeding).",
    },
    "performance": {
        "label": "Performance",
        "means": "Cache effectiveness - how often PrismCache (or the demo NullAdapter) hits.",
        "how": "hit_rate x 100. A 0.92 hit rate -> 92.",
        "good": "80+",
        "bad": "Low hit rate -> more cold path / LLM spend; check invalidation storms and warm jobs.",
    },
    "cost_efficiency": {
        "label": "Cost efficiency",
        "means": "Estimated dollars saved by cache hits (token-tax avoidance).",
        "how": "min(100, cost_saved_usd x 2). Demo NullAdapters often show a modest savings number.",
        "good": "50+",
        "bad": "Low savings with high traffic -> cache not helping; review partitions and TTL.",
    },
    "knowledge_quality": {
        "label": "Knowledge quality",
        "means": "Whether taxonomy / graph dogfood checks look healthy.",
        "how": "About 78 when ChorusGraph dogfood reports ok; otherwise ~70.",
        "good": "75+",
        "bad": "Dogfood failing -> partitions or graph wiring need attention (Taxonomy tab).",
    },
    "compliance": {
        "label": "Compliance",
        "means": "License posture for auditability - valid license supports compliance exports.",
        "how": "80 when license state is valid; ~40 otherwise.",
        "good": "80",
        "bad": "Grace/invalid license weakens audit.export / SOC2 confidence.",
    },
    "operational_health": {
        "label": "Operational health",
        "means": "Fleet enrollment depth - more healthy workers raises the score.",
        "how": "min(100, 60 + fleet_nodes x 5). Three agents -> 75.",
        "good": "70+ with workers online",
        "bad": "Near 60 with zero workers - enroll agents from Admin.",
    },
}

LAYER_PLAIN = {
    "L0": "Process - mother process is up.",
    "L1": "License - offline verify result (valid / grace / invalid).",
    "L2": "Storage - SQLite always; Postgres audit sink when DATABASE_URL is set.",
    "L3": "Control transport - HTTP primary (Fabric optional).",
    "L4": "Workers - enrolled fleet agents and dogfood.",
    "L5": "Prism pack - live sibling adapters vs honest DEMO NullAdapters.",
}


def _band(value: float) -> str:
    if value >= 80:
        return "strong"
    if value >= 60:
        return "okay"
    if value >= 40:
        return "weak"
    return "critical"


def _fmt_dim(key: str, value: float) -> str:
    meta = DIMENSION_PLAIN.get(key) or {"label": key, "means": ""}
    return f"**{meta['label']} {value:.0f}** ({_band(value)}) - {meta['means']}"


async def dashboard_snapshot(state) -> dict[str, Any]:
    """Live numbers the Overview shows - single source for Assistant grounding."""
    from choruscontrol.services.caps import aggregate_caps, compute_ai_score, policy_drift
    from choruscontrol.services.pipelines import live_pipelines

    caps = await aggregate_caps(state)
    metrics = await state.cache.get_metrics()
    incidents = await state.store.fetchall("SELECT * FROM incidents ORDER BY created_at DESC LIMIT 20")
    nodes = await state.fleet.list_nodes()
    score = compute_ai_score(caps, metrics, len(incidents))
    drifts = await policy_drift(state)
    drifted = [d for d in drifts if d["drift"]]
    pipe = await live_pipelines(state)

    # Health matrix (same shape as /health/matrix)
    lic = state.license_status.state
    dogfood = await state.graph.dogfood()
    live_any = any(str(v).startswith("live") for v in state.adapter_sources.values())
    pg_ok = True
    if state.settings.database_url and state.postgres is not None:
        pg_ok = await state.postgres.ping()
    elif state.settings.database_url:
        pg_ok = False
    matrix = {
        "L0": {"name": "process", "ok": True},
        "L1": {"name": "license", "ok": lic in ("valid", "grace"), "state": lic},
        "L2": {
            "name": "sqlite_or_postgres",
            "ok": pg_ok,
            "postgres": bool(state.settings.database_url),
        },
        "L3": {"name": "fabric_or_http", "ok": True, "primary": state.settings.transport_primary},
        "L4": {
            "name": "workers",
            "ok": bool(dogfood.get("ok", True)),
            "count": len(nodes),
        },
        "L5": {
            "name": "prism_pack",
            "ok": True,
            "demo": not live_any or state.settings.demo_mode,
        },
    }

    online = [n for n in nodes if n.get("online")]
    lowest = sorted(score["dimensions"].items(), key=lambda kv: kv[1])[:3]
    highest = sorted(score["dimensions"].items(), key=lambda kv: kv[1], reverse=True)[:3]
    enriched = [
        enrich_node(
            {
                "id": n["node_id"],
                "role": n.get("role"),
                "zone": n.get("network_zone"),
                "online": bool(n.get("online")),
                "tenant_id": n.get("tenant_id"),
                "products": n.get("products") or {},
            }
        )
        for n in nodes
    ]

    return {
        "score": score,
        "metrics": {
            "hit_rate": metrics.get("hit_rate"),
            "cost_saved_usd": metrics.get("cost_saved_usd"),
            "tokens_saved": metrics.get("tokens_saved"),
            "demo": bool(metrics.get("demo")),
        },
        "incidents": {
            "open_count": len(incidents),
            "latest": [
                {"title": i.get("title"), "tenant_id": i.get("tenant_id"), "state": i.get("state")}
                for i in incidents[:5]
            ],
        },
        "fleet": {
            "total": len(nodes),
            "online": len(online),
            "nodes": enriched,
            "catalog": {
                k: {"title": v["title"], "mission": v["mission"], "role": v["role"], "tenant": v["tenant"]}
                for k, v in AGENT_CATALOG.items()
            },
        },
        "policy_drift_count": len(drifted),
        "matrix": matrix,
        "pipeline": {
            "run_id": (pipe.get("execution") or {}).get("run_id"),
            "stages": [
                s.get("label") for s in ((pipe.get("execution") or {}).get("stages") or [])
            ],
            "cascade_state": (pipe.get("cascade") or {}).get("state"),
        },
        "license": {
            "state": lic,
            "tier": state.license_status.claims.tier if state.license_status.claims else None,
        },
        "demo_mode": state.settings.demo_mode,
        "lowest_dimensions": [{"key": k, "value": v} for k, v in lowest],
        "highest_dimensions": [{"key": k, "value": v} for k, v in highest],
        "glossary": DIMENSION_PLAIN,
        "layers": LAYER_PLAIN,
        "roles": ROLE_PLAIN,
        "platform_brief": PLATFORM_BRIEF.strip(),
    }


def explain_score(snap: dict[str, Any], focus: str | None = None) -> str:
    score = snap["score"]
    dims = score["dimensions"]
    demo = "DEMO inputs (NullAdapters) - labeled honestly" if score.get("demo") else "live adapter inputs"
    lines = [
        f"Overall AI Score is **{score['overall']}** out of 100 "
        f"(simple average of eight dimensions; {demo}).",
        "",
        "What each Overview bar means right now:",
    ]
    order = [
        "security",
        "governance",
        "reliability",
        "performance",
        "cost_efficiency",
        "knowledge_quality",
        "compliance",
        "operational_health",
    ]
    for key in order:
        if focus and focus not in key and focus not in (DIMENSION_PLAIN.get(key) or {}).get("label", "").lower():
            continue
        val = float(dims.get(key, 0))
        meta = DIMENSION_PLAIN[key]
        lines.append(
            f"- {meta['label']}: **{val:.0f}** ({_band(val)}). {meta['means']} "
            f"Calculated as: {meta['how']} Healthy range: {meta['good']}."
        )

    # Plain diagnosis
    low = snap["lowest_dimensions"][0]
    low_meta = DIMENSION_PLAIN.get(low["key"], {})
    lines.append("")
    lines.append(
        f"Biggest drag today: **{low_meta.get('label', low['key'])} at {low['value']:.0f}**. "
        f"{low_meta.get('bad', '')}"
    )
    if snap["incidents"]["open_count"]:
        lines.append(
            f"Open incidents: **{snap['incidents']['open_count']}** "
            f"(this is why Reliability is {dims.get('reliability', 0):.0f}). "
            f"Latest: {snap['incidents']['latest'][0]['title'] if snap['incidents']['latest'] else 'n/a'}."
        )
    lines.append(
        f"Fleet: **{snap['fleet']['online']}/{snap['fleet']['total']}** agents online -> "
        f"Operational health {dims.get('operational_health', 0):.0f}."
    )
    lines.append(
        "Remember: Shine PASS / Guard ALLOW are not world-truth - only grounded in preload/policy."
    )
    return "\n".join(lines)


def explain_matrix(snap: dict[str, Any]) -> str:
    lines = ["Layer health (L0-L5) in plain English:"]
    for key in ("L0", "L1", "L2", "L3", "L4", "L5"):
        cell = snap["matrix"].get(key) or {}
        ok = "healthy" if cell.get("ok") else "degraded"
        extra = ""
        if key == "L1":
            extra = f" state={cell.get('state')}"
        if key == "L2":
            extra = " (Postgres audit on)" if cell.get("postgres") else " (SQLite only)"
        if key == "L3":
            extra = f" primary={cell.get('primary')}"
        if key == "L4":
            extra = f" workers={cell.get('count')}"
        if key == "L5":
            extra = " DEMO NullAdapters" if cell.get("demo") else " live Prism packs"
        lines.append(f"- {key}: {ok}{extra}. {LAYER_PLAIN[key]}")
    return "\n".join(lines)


def explain_overview(snap: dict[str, Any]) -> str:
    score = snap["score"]
    return (
        f"Here's the Overview in plain English.\n\n"
        f"AI Score **{score['overall']}** is the average of eight health dimensions "
        f"({'demo' if score.get('demo') else 'live'} data).\n"
        f"- Cache hit rate: {snap['metrics'].get('hit_rate')} -> Performance "
        f"{score['dimensions'].get('performance')}.\n"
        f"- Est. cache savings: ${snap['metrics'].get('cost_saved_usd')} -> Cost efficiency "
        f"{score['dimensions'].get('cost_efficiency')}.\n"
        f"- Open incidents: {snap['incidents']['open_count']} -> Reliability "
        f"{score['dimensions'].get('reliability')}.\n"
        f"- Agents online: {snap['fleet']['online']}/{snap['fleet']['total']} -> Operational health "
        f"{score['dimensions'].get('operational_health')}.\n"
        f"- License: {snap['license'].get('state')} ({snap['license'].get('tier')}) -> "
        f"Governance/Compliance.\n"
        f"- Policy drift nodes: {snap['policy_drift_count']}.\n"
        f"- Live wire: {' -> '.join(snap['pipeline'].get('stages') or []) or 'Guard -> Ledger -> Shine'}.\n\n"
        f"Agents: "
        + (
            "; ".join(
                f"{n.get('title') or n['id']} ({n.get('role')}, "
                f"{'online' if n.get('online') else 'stale'})"
                for n in snap["fleet"]["nodes"]
            )
            or "none enrolled yet"
        )
        + ".\n\n"
        f"Ask about a number ('why is reliability 0?') or an agent "
        f"('what does the clinical agent do?', 'explain GREEN vs ORANGE')."
    )


async def assistant_ask(
    state,
    question: str,
    principal_user: str,
    *,
    confirm: bool = False,
    execute: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Ops Assistant - grounded answers; gated execute via same APIs + audit."""
    from choruscontrol.services.graph import graph_query

    q = (question or "").lower().strip()
    snap = await dashboard_snapshot(state)
    graph = await graph_query(state.store)
    nodes = snap["fleet"]["nodes"]
    actions: list[dict[str, Any]] = []
    execution: dict[str, Any] | None = None
    wire: dict[str, Any] | None = None

    def _compose_ops_answer() -> str:
        nonlocal actions
        # --- Intent routing (prefer agent literacy, then dashboard literacy) ---
        catalog_hit = match_catalog_from_question(q)
        live_hit = find_live_node(nodes, catalog_hit[0] if catalog_hit else None, q)
        role_ask = None
        for rk in ("GREEN", "BLUE", "ORANGE", "WORKER"):
            if rk.lower() in q and any(
                w in q
                for w in ("what is", "what's", "explain", "mean", "vs", "versus", "role", "color")
            ):
                role_ask = rk
                break
        if "green vs" in q or "vs orange" in q or "green versus" in q or "blue vs" in q:
            role_ask = role_ask or "GREEN"

        dim_keys = list(DIMENSION_PLAIN.keys())
        dim_hit = next(
            (
                k
                for k in dim_keys
                if k.replace("_", " ") in q
                or DIMENSION_PLAIN[k]["label"].lower() in q
                or k.split("_")[0] in q.split()
            ),
            None,
        )
        if dim_hit in ("cost_efficiency",) and "cost" in q:
            dim_hit = "cost_efficiency"

        agent_intent = bool(catalog_hit or live_hit) and any(
            w in q
            for w in (
                "what does",
                "what's",
                "whats",
                "who is",
                "who's",
                "explain",
                "tell me about",
                "about",
                "do?",
                "does",
                "role",
                "mission",
                "job",
                "purpose",
                "responsible",
            )
        )
        if catalog_hit and (
            "agent" in q
            or catalog_hit[0].replace("-", " ") in q
            or any(a in q for a in (catalog_hit[1].get("aliases") or []))
        ):
            agent_intent = True

        if agent_intent and (catalog_hit or live_hit):
            cid = catalog_hit[0] if catalog_hit else (live_hit or {}).get("catalog_id")
            cat = catalog_hit[1] if catalog_hit else None
            return explain_agent(live_hit, catalog_id=cid, catalog=cat)
        if role_ask or any(
            p in q
            for p in (
                "what is green",
                "what is blue",
                "what is orange",
                "green vs orange",
                "green versus orange",
                "topology color",
                "fleet color",
                "what does green",
                "what does blue",
                "what does orange",
            )
        ):
            if "vs" in q or "versus" in q:
                fleet_lines = (
                    "\n".join(
                        f"- {n.get('title') or n['id']}: {n.get('role')} "
                        f"({'online' if n.get('online') else 'stale'})"
                        for n in nodes
                    )
                    or "- none enrolled"
                )
                return (
                    f"{explain_role('GREEN')}\n\n{explain_role('BLUE')}\n\n{explain_role('ORANGE')}\n\n"
                    f"Live fleet:\n{fleet_lines}"
                )
            rk = role_ask or next(
                (r for r in ("GREEN", "BLUE", "ORANGE") if r.lower() in q), "GREEN"
            )
            return explain_role(rk)
        if any(
            p in q
            for p in (
                "who are the agents",
                "what do the agents",
                "what does each agent",
                "list agents",
                "list the agents",
                "fleet health",
                "how is fleet",
                "mother vs agent",
                "mother versus agent",
                "what is an agent",
                "what is the agent",
                "platform brief",
                "how does the fleet",
            )
        ) or (
            ("fleet" in q or "agents" in q)
            and any(w in q for w in ("who", "what", "explain", "how", "list"))
        ):
            return explain_fleet(
                nodes, online=snap["fleet"]["online"], total=snap["fleet"]["total"]
            )
        if any(
            p in q
            for p in (
                "what do these numbers",
                "what do the numbers",
                "explain the dashboard",
                "explain overview",
                "plain english",
                "what does the score",
                "dashboard mean",
                "numbers mean",
                "help me understand",
            )
        ) or q in ("help", "?", "hi", "hello"):
            return explain_overview(snap)
        if "layer" in q or "l0" in q or "l1" in q or "matrix" in q or "health matrix" in q:
            return explain_matrix(snap)
        if dim_hit and any(
            w in q
            for w in ("why", "what", "explain", "mean", "score", "dimension", "bar", "low", "high")
        ):
            return explain_score(snap, focus=dim_hit.replace("_", " "))
        if (
            "score" in q
            or ("dimension" in q)
            or ("ai score" in q)
            or ("why is" in q and any(k.split("_")[0] in q for k in dim_keys))
        ):
            focus = None
            for k, meta in DIMENSION_PLAIN.items():
                if meta["label"].lower() in q or k.replace("_", " ") in q:
                    focus = meta["label"].lower()
                    break
            return explain_score(snap, focus=focus)
        if "reliability" in q:
            return explain_score(snap, focus="reliability")
        if "performance" in q or "hit rate" in q or "cache" in q:
            return (
                explain_score(snap, focus="performance")
                + f"\n\nLive hit_rate={snap['metrics'].get('hit_rate')}, "
                f"tokens_saved={snap['metrics'].get('tokens_saved')}."
            )
        if "cost" in q or "saving" in q or "token-tax" in q or "token tax" in q:
            return (
                explain_score(snap, focus="cost")
                + f"\n\nLive cost_saved_usd=${snap['metrics'].get('cost_saved_usd')} "
                f"(demo={snap['metrics'].get('demo')})."
            )
        if "fail" in q or "incident" in q:
            latest = snap["incidents"]["latest"]
            titles = "; ".join(i["title"] for i in latest) or "none"
            return (
                f"There are **{snap['incidents']['open_count']}** recent incidents. "
                f"Reliability on the Overview is **{snap['score']['dimensions'].get('reliability')}** "
                f"because each open incident subtracts 5 from 100. Latest: {titles}."
            )
        if "stale" in q or "knowledge" in q or "taxonomy" in q or "partition" in q:
            actions.append(
                {
                    "type": "job",
                    "command": "taxonomy.warm_partition",
                    "requires_confirmation": True,
                    "params": {
                        "tenant_id": "aurora-health",
                        "partition": "kb_clinical_guidelines",
                    },
                }
            )
            return (
                explain_score(snap, focus="knowledge")
                + "\n\nCheck Taxonomy partitions and warm_partition if versions lag."
            )
        if "policy" in q or "drift" in q:
            return (
                f"Policy drift on **{snap['policy_drift_count']}** node(s). "
                f"Drift means a worker's Guard profile hint disagrees with Policy Studio intent "
                f"(e.g. hub clinical_chat vs heavy/law). Fix in Guard tab, then re-check Overview."
            )
        if "architecture" in q or "graph" in q or "blast" in q:
            return (
                f"Asset graph has **{len(graph['assets'])}** assets and **{len(graph['edges'])}** edges; "
                f"**{snap['fleet']['total']}** agents. Use Overview -> Asset graph map for blast radius.\n\n"
                f"{PLATFORM_BRIEF.strip()}"
            )
        if "pipeline" in q or "trace" in q or "wire" in q or "flow" in q:
            labels = " -> ".join(snap["pipeline"].get("stages") or []) or "Guard -> Ledger -> Shine"
            return (
                f"Live execution pipeline: **{labels}**. "
                f"Run `{snap['pipeline'].get('run_id') or 'none yet'}`. "
                f"Cascade state: {snap['pipeline'].get('cascade_state') or 'idle'}. "
                f"Fleet online: {snap['fleet']['online']}/{snap['fleet']['total']}."
            )
        if "fleet" in q or "agent" in q or "node" in q or "worker" in q:
            return explain_fleet(
                nodes, online=snap["fleet"]["online"], total=snap["fleet"]["total"]
            )
        if "upgrade" in q or "reindex" in q:
            actions.append(
                {
                    "type": "job",
                    "command": "taxonomy.reindex",
                    "requires_confirmation": True,
                    "params": {"tenant_id": "aurora-health"},
                }
            )
            return "Reindex/model upgrades are gated. Confirm with operator role."
        if "cascade" in q:
            actions.append(
                {
                    "type": "cascade",
                    "requires_confirmation": True,
                    "params": {
                        "tenant_id": "aurora-health",
                        "tags": ["assistant:manual"],
                        "reason": "assistant",
                    },
                }
            )
            return (
                f"Correction cascade invalidates tags across the fleet. "
                f"Current cascade state on Overview: **{snap['pipeline'].get('cascade_state') or 'idle'}**. "
                f"Confirm to run a new cascade."
            )
        if "demo" in q or "nulladapter" in q or "null adapter" in q:
            return (
                "Demo mode uses **NullAdapters** - synthetic Guard/Cache/Shine/Cortex responses "
                "labeled DEMO so you never mistake them for live Prism packs. "
                f"AI Score demo flag={snap['score'].get('demo')}. "
                "Install sibling packages at pin floors (Admin -> Doctor) to go live."
            )
        return (
            f"I see Overview AI Score **{snap['score']['overall']}** "
            f"(Reliability {snap['score']['dimensions'].get('reliability')}, "
            f"Performance {snap['score']['dimensions'].get('performance')}, "
            f"Cost {snap['score']['dimensions'].get('cost_efficiency')}; "
            f"{snap['fleet']['online']}/{snap['fleet']['total']} agents online; "
            f"{snap['incidents']['open_count']} incidents). "
            f"Ask 'explain the dashboard', 'what does the clinical agent do?', or 'who are the agents?'.\n\n"
            f"{explain_overview(snap)}"
        )

    from choruscontrol.services.assistant_stack import run_guard_graph_shine

    tenant_id = "aurora-health" if any(
        (n.get("tenant_id") or "") in ("aurora-health", "aurora-pharmacy") for n in nodes
    ) else "default"
    wired = run_guard_graph_shine(
        question=question,
        tenant_id=tenant_id,
        compose_answer=_compose_ops_answer,
        snap=snap,
    )
    answer = wired["answer"]
    wire = wired.get("wire")
    if wired.get("blocked"):
        actions = []

    if execute:
        if not confirm:
            execution = {"status": "needs_confirmation", "execute": execute}
        else:
            feats = set(state.license_status.claims.features) if state.license_status.claims else set()
            if "assistant.ops" not in feats and not state.settings.demo_mode:
                execution = {"status": "denied", "reason": "feature assistant.ops required"}
            elif state.license_status.state == "grace":
                execution = {"status": "denied", "reason": "license grace: mutations blocked"}
            else:
                etype = execute.get("type") or execute.get("command")
                params = execute.get("params") or {}
                from choruscontrol.services.enterprise_policy import check_allowed

                gate_domain = None
                if etype in ("taxonomy.reindex", "taxonomy.warm_partition") or execute.get(
                    "command"
                ) in ("taxonomy.reindex", "taxonomy.warm_partition"):
                    gate_domain = "memory.write"
                elif etype in ("cascade", "guard.policy.put") or execute.get("type") == "cascade":
                    gate_domain = "deployment.approval"

                gate = {"allowed": True}
                if gate_domain:
                    gate = await check_allowed(
                        state.store,
                        domain=gate_domain,
                        tenant_id=params.get("tenant_id", "default"),
                        action=str(etype),
                        context={"role": "operator", "approved": bool(confirm)},
                    )

                if not gate.get("allowed"):
                    execution = {"status": "denied", "reason": gate}
                elif etype in ("taxonomy.reindex", "job") and (
                    execute.get("command") == "taxonomy.reindex" or etype == "taxonomy.reindex"
                ):
                    job = await state.jobs.trigger_reindex(
                        params.get("tenant_id", "default")
                    )
                    execution = {"status": "ok", "job": job.__dict__}
                elif (
                    execute.get("command") == "taxonomy.warm_partition"
                    or etype == "taxonomy.warm_partition"
                ):
                    job = await state.jobs.trigger_warm(
                        params.get("tenant_id", "default"), params.get("partition")
                    )
                    execution = {"status": "ok", "job": job.__dict__}
                elif etype == "cascade" or execute.get("type") == "cascade":
                    result = await state.cascade.run(
                        params.get("tenant_id", "default"),
                        params.get("tags") or ["assistant"],
                        reason=params.get("reason", "assistant"),
                    )
                    execution = {"status": "ok", "cascade": result}
                elif etype == "incident.create":
                    from choruscontrol.services.incidents import create_incident

                    inc = await create_incident(
                        state.store,
                        tenant_id=params.get("tenant_id", "default"),
                        title=params.get("title") or "Assistant-opened incident",
                        details=params.get("details") or {"source": "assistant"},
                    )
                    execution = {"status": "ok", "incident": inc}
                elif etype == "guard.policy.put":
                    from choruscontrol.services.policy import validate_guard_policy

                    pol = params.get("policy") or {}
                    validate_guard_policy(pol)
                    await state.store.execute(
                        "INSERT INTO guard_policies(tenant_id, policy_json, updated_at) VALUES(?,?,?) "
                        "ON CONFLICT(tenant_id) DO UPDATE SET policy_json=excluded.policy_json, "
                        "updated_at=excluded.updated_at",
                        (
                            params.get("tenant_id", "default"),
                            json.dumps(pol),
                            time.time(),
                        ),
                    )
                    state.intended_policies[params.get("tenant_id", "default")] = pol
                    execution = {"status": "ok", "policy": pol}
                elif etype == "traces.replay":
                    from choruscontrol.services.traces import replay_trace

                    run_id = params.get("run_id")
                    if not run_id:
                        execution = {"status": "nack", "reason": "run_id required"}
                    else:
                        out = await replay_trace(state.store, run_id)
                        execution = {"status": "ok", "replay": out}
                elif etype == "compliance.scan":
                    from choruscontrol.services.compliance import run_compliance_scan

                    out = await run_compliance_scan(state)
                    execution = {"status": "ok", "compliance": out}
                else:
                    execution = {"status": "nack", "reason": f"unsupported execute {execute}"}
                await state.audit.log_action(
                    principal_user,
                    "assistant.execute",
                    "default",
                    {"execute": execute, "result": execution},
                )

    await state.audit.log_action(
        principal_user, "assistant.ask", "default", {"question": question, "answer": answer[:2000]}
    )
    return {
        "answer": answer,
        "grounding": {
            "assets": len(graph["assets"]),
            "nodes": snap["fleet"]["total"],
            "online": snap["fleet"]["online"],
            "ai_score": snap["score"]["overall"],
            "dimensions": snap["score"]["dimensions"],
            "incidents": snap["incidents"]["open_count"],
            "metrics": snap["metrics"],
            "matrix": {k: v.get("ok") for k, v in snap["matrix"].items()},
            "caps_tier": snap["license"],
            "demo": snap["score"].get("demo"),
            "agents": [
                {
                    "id": n["id"],
                    "title": n.get("title"),
                    "role": n.get("role"),
                    "online": n.get("online"),
                    "tenant_id": n.get("tenant_id"),
                    "zone": n.get("zone"),
                }
                for n in nodes
            ],
        },
        "wire": wire,
        "actions": actions,
        "execution": execution,
        "disclaimer": "Assistant uses platform telemetry only; PASS/ALLOW != world-true.",
    }
