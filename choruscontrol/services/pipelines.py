"""Pipeline snapshots for interactive dashboard visuals — grounded in live store/adapters."""

from __future__ import annotations

import json
import time
from typing import Any

from choruscontrol.services.traces import get_trace, list_traces


async def live_pipelines(state) -> dict[str, Any]:
    """Aggregate execution wire, fleet topology, cascade, and asset graph for SVG viz."""
    nodes = await state.fleet.list_nodes()
    fleet = [
        {
            "id": n["node_id"],
            "label": n["node_id"],
            "role": n["role"],
            "color": n.get("color")
            or ("ORANGE" if not n.get("online") else ("BLUE" if "BLUE" in (n.get("role") or "").upper() else "GREEN")),
            "online": bool(n.get("online")),
            "zone": n.get("network_zone"),
            "products": list((n.get("products") or {}).keys())[:6],
        }
        for n in nodes
    ]

    # Execution pipeline from latest trace
    traces = await list_traces(state.store, "default", limit=5)
    execution = {"run_id": None, "stages": _default_stages(), "active_index": 0}
    if traces:
        run_id = traces[0]["run_id"]
        tr = await get_trace(state.store, run_id)
        if tr and tr.get("wire", {}).get("stages"):
            stages = []
            for i, s in enumerate(tr["wire"]["stages"]):
                stages.append(
                    {
                        "id": s.get("stage") or f"step-{i}",
                        "label": (s.get("stage") or "step").title(),
                        "decision": s.get("decision") or s.get("hop") or s.get("kind"),
                        "gate": s.get("resolution_gate"),
                        "status": _stage_status(s),
                    }
                )
            execution = {
                "run_id": run_id,
                "stages": stages,
                "active_index": len(stages) - 1,
            }

    # Recent cascade pipeline
    cascades = await state.store.fetchall(
        "SELECT * FROM cascades ORDER BY created_at DESC LIMIT 1"
    )
    cascade_flow = None
    if cascades:
        c = cascades[0]
        details = json.loads(c["details_json"])
        steps = details.get("steps") or []
        cascade_flow = {
            "cascade_id": c["cascade_id"],
            "state": c["state"],
            "steps": [
                {
                    "id": st.get("step", f"s{i}"),
                    "label": (st.get("step") or "step").replace("_", " "),
                    "detail": st,
                    "status": "ok" if st.get("ok") or st.get("evicted") is not None else "done",
                }
                for i, st in enumerate(steps)
            ],
        }

    # Asset graph for interactive map (cap nodes for UI)
    assets = await state.store.fetchall(
        "SELECT asset_id, kind, name, tenant_id FROM assets ORDER BY updated_at DESC LIMIT 40"
    )
    edges = await state.store.fetchall("SELECT src, dst, rel FROM asset_edges LIMIT 80")
    asset_ids = {a["asset_id"] for a in assets}
    graph = {
        "nodes": [
            {
                "id": a["asset_id"],
                "label": a["name"],
                "kind": a["kind"],
                "tenant_id": a["tenant_id"],
            }
            for a in assets
        ],
        "edges": [
            {"source": e["src"], "target": e["dst"], "rel": e["rel"]}
            for e in edges
            if e["src"] in asset_ids and e["dst"] in asset_ids
        ],
    }

    metrics = await state.cache.get_metrics()
    score_dims = None
    try:
        from choruscontrol.services.caps import aggregate_caps, compute_ai_score

        caps = await aggregate_caps(state)
        incidents = await state.store.fetchall("SELECT incident_id FROM incidents")
        score_dims = compute_ai_score(caps, metrics, len(incidents))
    except Exception:  # noqa: BLE001
        score_dims = None

    return {
        "generated_at": time.time(),
        "execution": execution,
        "fleet": fleet,
        "cascade": cascade_flow,
        "graph": graph,
        "score": score_dims,
        "cache": {
            "hit_rate": metrics.get("hit_rate"),
            "tokens_saved": metrics.get("tokens_saved"),
            "cost_saved_usd": metrics.get("cost_saved_usd"),
            "demo": metrics.get("demo"),
        },
    }


def _default_stages() -> list[dict[str, Any]]:
    return [
        {"id": "guard", "label": "Guard", "decision": "awaiting", "gate": None, "status": "idle"},
        {"id": "graph", "label": "Ledger", "decision": "awaiting", "gate": None, "status": "idle"},
        {"id": "shine", "label": "Shine", "decision": "awaiting", "gate": None, "status": "idle"},
    ]


def _stage_status(stage: dict[str, Any]) -> str:
    d = (stage.get("decision") or "").lower()
    if d in ("block", "error", "flag"):
        return "bad"
    if d in ("allow", "pass", "ok") or stage.get("hop") or stage.get("kind"):
        return "ok"
    return "active"
