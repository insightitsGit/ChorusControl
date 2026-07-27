from __future__ import annotations

from typing import Any


async def aggregate_caps(state) -> dict[str, Any]:
    guard_caps = await state.guard.caps(
        state.intended_policies.get("default", {}).get("ingress_profile", "web_chat")
    )
    shine_caps = await state.shine.capabilities()
    peers = await state.fabric.peer_count()
    nodes = await state.fleet.list_nodes()
    dogfood = await state.graph.dogfood()

    # Knowledge health from RAG partitions when available
    knowledge_meta: dict[str, Any] = {"source": "unavailable"}
    try:
        parts = await state.rag.partitions("default")
        if parts:
            decays = []
            for p in parts:
                if isinstance(p, dict):
                    for k in ("staleness", "decay", "health"):
                        if k in p and p[k] is not None:
                            try:
                                decays.append(float(p[k]))
                            except (TypeError, ValueError):
                                pass
            knowledge_meta = {
                "source": "rag.partitions",
                "partition_count": len(parts),
                "mean_staleness": (sum(decays) / len(decays)) if decays else None,
                "demo": state.adapter_sources.get("rag") == "null",
            }
    except Exception:  # noqa: BLE001
        knowledge_meta = {"source": "error"}

    return {
        "guard": guard_caps,
        "shine": shine_caps,
        "cortex": {
            "ann": False,
            "prism_plus": True,
            "demo": state.adapter_sources.get("cortex") == "null",
            "source": state.adapter_sources.get("cortex"),
        },
        "graph": {
            "version": "1.3.0",
            "dogfood": dogfood,
            "source": state.adapter_sources.get("graph"),
        },
        "cache": {
            "backend": "prism",
            "metrics_available": True,
            "source": state.adapter_sources.get("cache"),
        },
        "rag": knowledge_meta,
        "fabric": {
            "peers": peers,
            "connected": True,
            "transport_primary": state.settings.transport_primary,
            "source": state.adapter_sources.get("fabric"),
        },
        "license": {
            "state": state.license_status.state,
            "tier": state.license_status.claims.tier if state.license_status.claims else None,
            "features": sorted(state.license_status.claims.features)
            if state.license_status.claims
            else [],
        },
        "fleet_nodes": len(nodes),
        "honesty": {
            "pass_means": shine_caps.get("pass_means"),
            "no_scorecard_on_web_chat": guard_caps.get("profile") == "web_chat",
        },
        "sources": state.adapter_sources,
    }


def compute_ai_score(
    caps: dict[str, Any],
    metrics: dict[str, Any],
    incidents: int,
    *,
    guard_block_rate: float | None = None,
    mean_staleness: float | None = None,
) -> dict[str, Any]:
    """Transparent formula — no black box. DEMO when inputs are synthetic/Null."""
    security = 90.0 if caps.get("guard", {}).get("profile") else 50.0
    if caps.get("guard", {}).get("profile") == "web_chat":
        security = 75.0
    if guard_block_rate is not None:
        # Higher block rate on clearly bad traffic is not always bad; use mild penalty for noisy blocks
        security = max(40.0, min(95.0, 90.0 - guard_block_rate * 40.0))

    governance = 85.0 if caps.get("license", {}).get("state") in ("valid", "grace") else 20.0
    reliability = max(0.0, 100.0 - incidents * 5)
    performance = min(100.0, float(metrics.get("hit_rate", 0) or 0) * 100)
    cost = min(100.0, float(metrics.get("cost_saved_usd", 0) or 0) * 2)

    # Knowledge from real staleness when present (0=fresh → 100; 1=stale → 0)
    knowledge = 70.0
    rag = caps.get("rag") or {}
    staleness = mean_staleness
    if staleness is None and rag.get("mean_staleness") is not None:
        staleness = float(rag["mean_staleness"])
    if staleness is not None:
        # Accept either 0-1 or 0-100 scales
        s = float(staleness)
        if s > 1.0:
            s = s / 100.0
        knowledge = max(0.0, min(100.0, (1.0 - s) * 100.0))
    elif caps.get("graph", {}).get("dogfood", {}).get("ok"):
        knowledge = 78.0

    compliance = 80.0 if caps.get("license", {}).get("state") == "valid" else 40.0
    if caps.get("license", {}).get("state") == "grace":
        compliance = 55.0
    ops = min(100.0, 60.0 + float(caps.get("fleet_nodes", 0)) * 5)
    dims = {
        "security": security,
        "governance": governance,
        "reliability": reliability,
        "performance": performance,
        "cost_efficiency": cost,
        "knowledge_quality": knowledge,
        "compliance": compliance,
        "operational_health": ops,
    }
    overall = sum(dims.values()) / len(dims)
    sources = caps.get("sources") or {}
    demo = bool(
        metrics.get("demo")
        or caps.get("guard", {}).get("demo")
        or sources.get("cache") == "null"
        or sources.get("rag") == "null"
        or rag.get("demo")
    )
    return {
        "overall": round(overall, 1),
        "dimensions": {k: round(v, 1) for k, v in dims.items()},
        "formula": "equal_weight_mean(dimensions)",
        "inputs": {
            "incidents": incidents,
            "guard_block_rate": guard_block_rate,
            "mean_staleness": staleness,
            "hit_rate": metrics.get("hit_rate"),
            "rag_source": rag.get("source"),
        },
        "demo": demo,
    }


async def policy_drift(state) -> list[dict[str, Any]]:
    """I01 — intended Policy Studio vs actual node caps digest/profile hints."""
    nodes = await state.fleet.list_nodes()
    intended = state.intended_policies.get("default", {})
    drifts = []
    for n in nodes:
        actual_profile = (n.get("products") or {}).get("guard_profile_hint")
        drift = False
        reason = None
        if intended.get("ingress_profile") == "web_chat" and actual_profile in ("heavy", "law_pilot"):
            drift = True
            reason = "intended web_chat but node reports heavy/law"
        drifts.append(
            {
                "node_id": n["node_id"],
                "intended_ingress": intended.get("ingress_profile"),
                "actual_hint": actual_profile,
                "drift": drift,
                "reason": reason,
                "caps_digest": n.get("caps_digest"),
            }
        )
    return drifts


def fleet_role_color(role: str, online: bool) -> str:
    """GREEN / BLUE / ORANGE topology strip."""
    if not online:
        return "ORANGE"
    r = (role or "").upper()
    if r in ("GREEN", "BLUE", "ORANGE"):
        return r
    if r in ("WORKER", "GRAPH"):
        return "GREEN"
    if r in ("MEMORY", "CORTEX"):
        return "BLUE"
    return "GREEN"
