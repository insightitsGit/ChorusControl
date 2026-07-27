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


def compute_ai_score(caps: dict[str, Any], metrics: dict[str, Any], incidents: int) -> dict[str, Any]:
    """Transparent formula — no black box. Returns DEMO when inputs are synthetic."""
    security = 90.0 if caps.get("guard", {}).get("profile") else 50.0
    if caps.get("guard", {}).get("profile") == "web_chat":
        security = 75.0
    governance = 85.0 if caps.get("license", {}).get("state") in ("valid", "grace") else 20.0
    reliability = max(0.0, 100.0 - incidents * 5)
    performance = min(100.0, float(metrics.get("hit_rate", 0) or 0) * 100)
    cost = min(100.0, float(metrics.get("cost_saved_usd", 0) or 0) * 2)
    knowledge = 70.0
    if caps.get("graph", {}).get("dogfood", {}).get("ok"):
        knowledge = 78.0
    compliance = 80.0 if caps.get("license", {}).get("state") == "valid" else 40.0
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
    demo = bool(
        metrics.get("demo")
        or caps.get("guard", {}).get("demo")
        or (caps.get("sources") or {}).get("cache") == "null"
    )
    return {
        "overall": round(overall, 1),
        "dimensions": {k: round(v, 1) for k, v in dims.items()},
        "formula": "equal_weight_mean(dimensions)",
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
