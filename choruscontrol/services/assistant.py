"""Ops Assistant - grounded in live dashboard telemetry with plain-English explanations."""

from __future__ import annotations

import json
import time
from typing import Any

from choruscontrol.services.assistant_glossary import (
    CASCADE_PLAIN,
    CORTEX_PLAIN,
    DOCTOR_PLAIN,
    GUARD_PLAIN,
    LOGS_PLAIN,
    PIPELINE_PLAIN,
    TAXONOMY_PLAIN,
    TRACE_PLAIN,
    explain_cascade,
    explain_cortex,
    explain_doctor,
    explain_guard,
    explain_logs,
    explain_performance_zero,
    explain_pipeline_decisions,
    explain_taxonomy,
    explain_trace,
)
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
    """Live numbers the Overview (and other tabs) show — single source for Assistant grounding."""
    from choruscontrol.adapters.pins import taxonomy_packs_ready
    from choruscontrol.services.caps import aggregate_caps, compute_ai_score, policy_drift
    from choruscontrol.services.doctor import doctor_mother
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

    # Prefer aurora tenant when present for Taxonomy/Cortex teachables
    tenant_hint = "default"
    for n in nodes:
        tid = n.get("tenant_id") or ""
        if tid in ("aurora-health", "aurora-pharmacy"):
            tenant_hint = "aurora-health" if tid == "aurora-health" else tid
            break

    # Taxonomy live fields
    taxonomy: dict[str, Any] = {
        "engine": "null",
        "demo": True,
        "partitions": [],
        "category_count": 0,
        "health": {},
        "tenant_id": tenant_hint,
    }
    try:
        from choruscontrol.services import taxonomy_rag as taxmod

        tree = taxmod.taxonomy_tree(tenant_hint)
        parts = taxmod.taxonomy_partitions(tenant_hint)
        health = taxmod.taxonomy_chunks_health(tenant_hint)
        eng = tree.get("engine") or parts.get("engine") or state.adapter_sources.get("rag") or "null"
        taxonomy = {
            "engine": eng,
            "demo": bool(tree.get("demo") or parts.get("demo") or eng == "null"),
            "partitions": parts.get("partitions") or [],
            "category_count": len(tree.get("categories") or []),
            "health": {
                "bleed_risk": health.get("bleed_risk"),
                "decay": health.get("decay") or [],
                "demo": health.get("demo"),
            },
            "tenant_id": tenant_hint,
        }
    except Exception:  # noqa: BLE001
        taxonomy["engine"] = state.adapter_sources.get("rag") or "null"

    tax_packs = taxonomy_packs_ready()

    # Guard policy + lexicon
    guard_row = await state.store.fetchone(
        "SELECT policy_json FROM guard_policies WHERE tenant_id=?", (tenant_hint,)
    )
    if not guard_row:
        guard_row = await state.store.fetchone(
            "SELECT policy_json FROM guard_policies WHERE tenant_id=?", ("default",)
        )
    pol: dict[str, Any] = {}
    if guard_row:
        try:
            pol = json.loads(guard_row["policy_json"] or "{}")
        except Exception:  # noqa: BLE001
            pol = {}
    lexicon_count = 0
    try:
        lex = await state.guard.get_lexicon(tenant_hint)
        lexicon_count = len(lex or [])
    except Exception:  # noqa: BLE001
        lexicon_count = 0
    guard_caps = caps.get("guard") or {}
    guard = {
        "ingress_profile": pol.get("ingress_profile"),
        "shadow_profile": pol.get("shadow_profile"),
        "shadow_enabled": pol.get("shadow_enabled"),
        "enforce_shadow": pol.get("enforce_shadow"),
        "recommended_preset": pol.get("recommended_preset"),
        "lexicon_count": lexicon_count,
        "caps_demo": bool(guard_caps.get("demo")),
        "caps": guard_caps,
    }

    # Cortex snapshot
    cortex: dict[str, Any] = {
        "engine": state.adapter_sources.get("cortex") or "null",
        "chunk_count": 0,
        "fact_count": 0,
        "conflict_count": 0,
        "activity_count": 0,
        "last_digest": None,
        "last_sleep_consolidated": None,
    }
    try:
        from choruscontrol.services.cortex_ops import snapshot as cortex_snapshot

        cx = cortex_snapshot(tenant_hint)
        cortex = {
            "engine": cx.get("engine") or state.adapter_sources.get("cortex") or "null",
            "chunk_count": len(cx.get("chunks") or []),
            "fact_count": len(cx.get("facts") or []),
            "conflict_count": len(cx.get("conflicts") or []),
            "activity_count": len(cx.get("activity") or []),
            "last_digest": next(
                (a.get("kind") for a in (cx.get("activity") or []) if "digest" in str(a.get("kind"))),
                None,
            ),
            "last_sleep_consolidated": next(
                (
                    a.get("consolidated") or a.get("count")
                    for a in (cx.get("activity") or [])
                    if "sleep" in str(a.get("kind"))
                ),
                None,
            ),
            "demo": bool(cx.get("demo")),
        }
    except Exception:  # noqa: BLE001
        pass

    # Doctor / pins
    try:
        doctor = await doctor_mother(state)
    except Exception:  # noqa: BLE001
        doctor = {
            "license": {"state": lic},
            "pins": getattr(state, "adapter_pins", {}) or {},
            "taxonomy_packs": tax_packs,
            "install_hint": tax_packs.get("install_hint"),
            "fleet_nodes": len(nodes),
            "adapters": {
                k: {"source": v, "demo": v == "null"} for k, v in state.adapter_sources.items()
            },
        }

    # Trace / ledger counts
    traces = await state.store.fetchall(
        "SELECT run_id, created_at FROM traces ORDER BY created_at DESC LIMIT 10"
    )
    stage_detail = []
    for s in (pipe.get("execution") or {}).get("stages") or []:
        stage_detail.append(
            {
                "label": s.get("label") or s.get("id"),
                "decision": s.get("decision"),
                "status": s.get("status"),
                "gate": s.get("gate"),
            }
        )

    # Ops logs summary
    logs_summary: dict[str, Any] = {"count": 0, "sources": [], "levels": []}
    if getattr(state, "ops_logs", None) is not None:
        try:
            entries = await state.ops_logs.search(limit=50)
            logs_summary = {
                "count": len(entries),
                "sources": sorted({e.get("source") for e in entries if e.get("source")}),
                "levels": sorted({e.get("level") for e in entries if e.get("level")}),
            }
        except Exception:  # noqa: BLE001
            pass

    # Driver latency (honest —)
    driver: dict[str, Any] = {"p50_ms": None}
    try:
        fn = getattr(state.graph, "driver_latency", None)
        if fn:
            driver = await fn()
    except Exception:  # noqa: BLE001
        pass

    cascade_id = (pipe.get("cascade") or {}).get("cascade_id")
    cascade_state = (pipe.get("cascade") or {}).get("state")

    return {
        "score": score,
        "metrics": {
            "hit_rate": metrics.get("hit_rate"),
            "cost_saved_usd": metrics.get("cost_saved_usd"),
            "tokens_saved": metrics.get("tokens_saved"),
            "demo": bool(metrics.get("demo")),
        },
        "token_tax": {
            "hit_rate": metrics.get("hit_rate"),
            "tokens_saved": metrics.get("tokens_saved"),
            "cost_saved_usd": metrics.get("cost_saved_usd"),
            "demo": bool(metrics.get("demo")),
            "driver_p50_ms": driver.get("p50_ms"),
        },
        "driver": driver,
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
            "stage_detail": stage_detail,
            "cascade_state": cascade_state,
            "cascade_id": cascade_id,
        },
        "taxonomy": taxonomy,
        "taxonomy_packs": tax_packs,
        "guard": guard,
        "cortex": cortex,
        "doctor": doctor,
        "trace": {
            "recent_count": len(traces or []),
            "latest_run_id": (traces[0]["run_id"] if traces else None),
        },
        "logs": logs_summary,
        "license": {
            "state": lic,
            "tier": state.license_status.claims.tier if state.license_status.claims else None,
        },
        "demo_mode": state.settings.demo_mode,
        "adapter_sources": dict(state.adapter_sources),
        "lowest_dimensions": [{"key": k, "value": v} for k, v in lowest],
        "highest_dimensions": [{"key": k, "value": v} for k, v in highest],
        "glossary": DIMENSION_PLAIN,
        "layers": LAYER_PLAIN,
        "roles": ROLE_PLAIN,
        "glossaries": {
            "taxonomy": TAXONOMY_PLAIN,
            "trace": TRACE_PLAIN,
            "guard": GUARD_PLAIN,
            "cortex": CORTEX_PLAIN,
            "doctor": DOCTOR_PLAIN,
            "logs": LOGS_PLAIN,
            "cascade": CASCADE_PLAIN,
            "pipeline": PIPELINE_PLAIN,
        },
        "platform_brief": PLATFORM_BRIEF.strip(),
        "tenant_hint": tenant_hint,
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
        "Ask about a number ('why is reliability 0?', 'why is performance 0?') or any tab value "
        "('what is partition version?', 'what do pin floors mean?', 'what is zero-token replay?')."
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
        if (
            "layer" in q
            or "health matrix" in q
            or "matrix" in q
            or any(f"l{i}" in q for i in range(6))
            or "prism pack" in q
        ):
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
        if "performance" in q or "hit rate" in q or (("cache" in q) and "invalidate" not in q):
            perf = float((snap["score"]["dimensions"] or {}).get("performance") or 0)
            hit = snap["metrics"].get("hit_rate")
            if (
                "why" in q
                and (perf <= 0 or hit in (0, 0.0, None) or "0" in q)
            ) or ("performance 0" in q or "performance is 0" in q):
                return explain_performance_zero(snap)
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
        # --- Tab glossaries (HO-009) ---
        if any(
            p in q
            for p in (
                "taxonomy_packs",
                "taxonomy packs",
                "packs ready",
                "prismrag-patch",
                "prismrag",
                "partition version",
                "what is a partition",
                "chunk staleness",
                "staleness",
                "bleed risk",
                "taxonomy engine",
                "what does taxonomy",
                "overwrite chunk",
                "embedding dim",
            )
        ) or (
            "taxonomy" in q
            and any(w in q for w in ("what", "explain", "mean", "engine", "version", "why"))
        ):
            focus = None
            if "pack" in q:
                focus = "taxonomy_packs"
            elif "version" in q or "partition" in q:
                focus = "partition_version"
            elif "stale" in q:
                focus = "staleness"
            elif "bleed" in q:
                focus = "bleed_risk"
            elif "overwrite" in q or "embed" in q:
                focus = "overwrite"
            elif "engine" in q or "prismrag" in q:
                focus = "engine"
            return explain_taxonomy(snap, focus=focus)
        if any(
            p in q
            for p in (
                "zero-token",
                "zero token",
                "replay",
                "what is a run",
                "run_id",
                "ledger",
                "wire stage",
            )
        ) or (
            ("trace" in q or "wire" in q)
            and any(w in q for w in ("what", "explain", "mean", "replay"))
        ):
            focus = "replay" if "replay" in q or "zero" in q else ("ledger" if "ledger" in q else "wire_stages")
            if "run" in q:
                focus = "run_id"
            return explain_trace(snap, focus=focus)
        if any(
            p in q
            for p in (
                "shadow compare",
                "shadow_profile",
                "ingress_profile",
                "enforce_shadow",
                "lexicon",
                "guard profile",
                "what is guard",
            )
        ) or (
            "guard" in q and any(w in q for w in ("what", "explain", "mean", "shadow", "ingress"))
        ):
            focus = "shadow_compare"
            if "ingress" in q:
                focus = "ingress_profile"
            elif "lexicon" in q:
                focus = "lexicon"
            elif "shadow" in q and "compare" not in q:
                focus = "shadow_profile"
            elif "caps" in q or "demo" in q:
                focus = "caps_demo"
            return explain_guard(snap, focus=focus)
        if any(
            p in q
            for p in (
                "cortex digest",
                "digest committed",
                "what does cortex",
                "memory chunk",
                "sleep consolidated",
                "prismcortex",
                "recall answer",
            )
        ) or (
            "cortex" in q and any(w in q for w in ("what", "explain", "mean", "digest", "sleep", "recall"))
        ):
            focus = "engine"
            if "digest" in q:
                focus = "digest"
            elif "sleep" in q:
                focus = "sleep"
            elif "recall" in q:
                focus = "recall"
            elif "activity" in q:
                focus = "activity"
            return explain_cortex(snap, focus=focus)
        if any(
            p in q
            for p in (
                "pin floor",
                "pin floors",
                "core vs optional",
                "optional pin",
                "missing core",
                "install_hint",
                "install hint",
                "soc2",
                "join token",
                "compliance finding",
                "adapter source",
                "what do pin",
            )
        ) or (
            ("doctor" in q or "admin" in q or "pin" in q)
            and any(w in q for w in ("what", "explain", "mean", "why", "missing"))
        ):
            focus = "pin_floors"
            if "optional" in q or "core" in q:
                focus = "core_vs_optional"
            elif "taxonomy_packs" in q or "packs" in q:
                focus = "taxonomy_packs"
            elif "license" in q:
                focus = "license"
            elif "soc2" in q:
                focus = "soc2_export"
            elif "join" in q:
                focus = "join_token"
            elif "compliance" in q or "finding" in q:
                focus = "compliance"
            elif "adapter" in q:
                focus = "adapters"
            elif "install" in q:
                focus = "install_hint"
            return explain_doctor(snap, focus=focus)
        if any(
            p in q
            for p in (
                "ops log",
                "ops logs",
                "log source",
                "logs tab",
                "node filter",
                "what does logs",
            )
        ) or ("log" in q and any(w in q for w in ("what", "explain", "mean", "filter", "level", "source"))):
            focus = "source_filter" if "source" in q or "filter" in q or "node" in q else "ops_logs"
            if "level" in q:
                focus = "level"
            return explain_logs(snap, focus=focus)
        if "cascade" in q and any(w in q for w in ("what", "mean", "explain", "completed", "idle", "failed", "why")):
            return explain_cascade(snap)
        if any(
            p in q
            for p in ("pipeline decision", "guard allow", "shine pass", "shine verdict", "wire decision")
        ):
            return explain_pipeline_decisions(snap)
        if "stale" in q or (
            "knowledge" in q and any(w in q for w in ("why", "score", "dimension", "low"))
        ):
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
                + "\n\n"
                + explain_taxonomy(snap, focus="staleness")
            )
        if "policy" in q or "drift" in q:
            return (
                f"Policy drift on **{snap['policy_drift_count']}** node(s). "
                f"Drift means a worker's Guard profile hint disagrees with Policy Studio intent "
                f"(e.g. hub clinical_chat vs heavy/law). Fix in Guard tab, then re-check Overview."
            )
        if "architecture" in q or "blast" in q or (
            "asset graph" in q
        ):
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
                f"Fleet online: {snap['fleet']['online']}/{snap['fleet']['total']}.\n\n"
                + explain_pipeline_decisions(snap)
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
                explain_cascade(snap)
                + "\n\nConfirm to run a new cascade (gated)."
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
            f"Ask about **any number on the dashboard** — scores, Taxonomy engine, pin floors, "
            f"cascade state, Guard shadow, Cortex digest, Logs filters, or Trace replay.\n\n"
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
