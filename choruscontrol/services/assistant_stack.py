"""Ops Assistant Prism wire: Guard -> ChorusGraph -> Shine (public APIs only).

Verified pins (see AI_IDE_PROMPTS / PrismGuard / PrismShine docs):
  chorusgraph==1.3.0
  prismguard[prism,guard-model]==0.1.10
  prismshine==0.2.2

No PrismAPI / PrismDriver here. Repo has no LLM client — answer body is the
grounded telemetry composer (not a provider call).
"""

from __future__ import annotations

import logging
import threading
from typing import Any, Callable

log = logging.getLogger("choruscontrol.assistant_stack")

_lock = threading.Lock()
_checker: Any | None = None
_gate: Any | None = None
_stack_status: dict[str, Any] | None = None


def probe_stack() -> dict[str, Any]:
    """Import-check sibling packages; cache status for UI / doctor."""
    global _stack_status
    if _stack_status is not None:
        return dict(_stack_status)
    status: dict[str, Any] = {
        "chorusgraph": False,
        "prismguard": False,
        "prismshine": False,
        "versions": {},
        "llm": "none",
        "note": (
            "No LLM client in this repo — Ops Assistant uses the grounded telemetry "
            "composer after Guard allow. Wire a provider if you want free-form LLM hops."
        ),
    }
    try:
        import chorusgraph

        status["chorusgraph"] = True
        status["versions"]["chorusgraph"] = getattr(chorusgraph, "__version__", "?")
    except Exception as exc:  # noqa: BLE001
        status["chorusgraph_error"] = str(exc)
    try:
        from prismguard.runtime.factory import create_checker_for_app  # noqa: F401

        status["prismguard"] = True
        import prismguard

        status["versions"]["prismguard"] = getattr(prismguard, "__version__", "?")
    except Exception as exc:  # noqa: BLE001
        status["prismguard_error"] = str(exc)
    try:
        import prismshine

        status["prismshine"] = True
        status["versions"]["prismshine"] = getattr(prismshine, "__version__", "?")
    except Exception as exc:  # noqa: BLE001
        status["prismshine_error"] = str(exc)
    status["ready"] = bool(
        status["chorusgraph"] and status["prismguard"] and status["prismshine"]
    )
    _stack_status = status
    return dict(status)


def _get_checker():
    global _checker
    with _lock:
        if _checker is None:
            from prismguard.runtime.factory import create_checker_for_app

            _checker = create_checker_for_app("web_chat")
        return _checker


def _get_gate():
    global _gate
    with _lock:
        if _gate is None:
            from prismshine import get_gate

            _gate = get_gate()
        return _gate


def preload_from_snapshot(snap: dict[str, Any]) -> list[dict[str, str]]:
    """Evidence texts for Shine — include live numbers so hard facts match."""
    score = snap.get("score") or {}
    dims = score.get("dimensions") or {}
    metrics = snap.get("metrics") or {}
    fleet = snap.get("fleet") or {}
    incidents = snap.get("incidents") or {}
    license_ = snap.get("license") or {}
    chunks: list[dict[str, str]] = []

    chunks.append(
        {
            "chunk_id": "ai_score",
            "text": (
                f"Overview AI Score is {score.get('overall')} out of 100, "
                f"a simple average of eight health dimensions. demo={score.get('demo')}."
            ),
            "source": "system",
        }
    )
    dim_bits = ", ".join(f"{k}={v}" for k, v in dims.items())
    chunks.append(
        {
            "chunk_id": "dimensions",
            "text": f"Overview dimension scores: {dim_bits}.",
            "source": "system",
        }
    )
    chunks.append(
        {
            "chunk_id": "metrics",
            "text": (
                f"Cache hit_rate={metrics.get('hit_rate')}, "
                f"cost_saved_usd={metrics.get('cost_saved_usd')}, "
                f"tokens_saved={metrics.get('tokens_saved')}, demo={metrics.get('demo')}."
            ),
            "source": "system",
        }
    )
    chunks.append(
        {
            "chunk_id": "fleet",
            "text": (
                f"Fleet agents online {fleet.get('online')}/{fleet.get('total')}. "
                + "; ".join(
                    f"{n.get('id')} role={n.get('role')} zone={n.get('zone')} "
                    f"tenant={n.get('tenant_id')} online={n.get('online')}"
                    for n in (fleet.get("nodes") or [])
                )
            ),
            "source": "system",
        }
    )
    latest = incidents.get("latest") or []
    titles = "; ".join(i.get("title") or "" for i in latest)
    chunks.append(
        {
            "chunk_id": "incidents",
            "text": (
                f"Open incidents count={incidents.get('open_count')}. Latest: {titles}. "
                f"Reliability uses 100 - (open_incidents x 5)."
            ),
            "source": "system",
        }
    )
    chunks.append(
        {
            "chunk_id": "license",
            "text": f"License state={license_.get('state')} tier={license_.get('tier')}.",
            "source": "system",
        }
    )
    for n in fleet.get("nodes") or []:
        chunks.append(
            {
                "chunk_id": f"agent_{(n.get('id') or 'node')}",
                "text": (
                    f"Agent {n.get('title') or n.get('id')}: {n.get('mission') or ''} "
                    f"role={n.get('role')} zone={n.get('zone')}."
                ),
                "source": "system",
            }
        )
    # Role glossary
    from choruscontrol.services.assistant_knowledge import PLATFORM_BRIEF, ROLE_PLAIN

    for rk, meta in ROLE_PLAIN.items():
        chunks.append(
            {
                "chunk_id": f"role_{rk}",
                "text": f"{meta['label']}: {meta['means']} {meta['does']}",
                "source": "system",
            }
        )
    chunks.append(
        {
            "chunk_id": "platform",
            "text": PLATFORM_BRIEF.replace("\n", " "),
            "source": "system",
        }
    )
    return chunks


def run_guard_graph_shine(
    *,
    question: str,
    tenant_id: str,
    compose_answer: Callable[[], str],
    snap: dict[str, Any],
) -> dict[str, Any]:
    """Public-API wire: create_checker_for_app(web_chat) -> Graph+ChorusStack -> Shine."""
    status = probe_stack()
    if not status.get("ready"):
        answer = compose_answer()
        return {
            "answer": answer,
            "blocked": False,
            "wire": {
                "mode": "fallback",
                "reason": "prism packages not installed",
                "stack": status,
                "guard": None,
                "graph": None,
                "shine": None,
                "llm": status.get("llm"),
            },
        }

    from chorusgraph import END, START, ChorusStack, Graph
    from chorusgraph.core.node import dict_node_adapter
    from prismshine import post_llm_check

    checker = _get_checker()
    guard_result = checker.check(question)
    guard_payload = {
        "decision": guard_result.decision,
        "resolution_gate": guard_result.resolution_gate,
        "fused_score": getattr(guard_result, "fused_score", None),
        "matched_category": getattr(guard_result, "matched_category", None),
        "profile": "web_chat",
    }
    log.info("guard decision=%s gate=%s", guard_result.decision, guard_result.resolution_gate)

    if str(guard_result.decision).lower() not in ("allow", "pass"):
        blocked = (
            f"**PrismGuard blocked this prompt** (profile `web_chat`).\n"
            f"- decision: **{guard_result.decision}**\n"
            f"- resolution_gate: {guard_result.resolution_gate}\n"
            f"- category: {getattr(guard_result, 'matched_category', None)}\n\n"
            f"Ops Assistant only answers after Guard ALLOW. Rephrase without injection patterns."
        )
        return {
            "answer": blocked,
            "blocked": True,
            "wire": {
                "mode": "live",
                "stack": status,
                "guard": guard_payload,
                "graph": None,
                "shine": None,
                "llm": status.get("llm"),
            },
        }

    answer = compose_answer()
    preload = preload_from_snapshot(snap)
    # Ensure answer hard facts appear in preload (Shine unmatched_number)
    preload.append(
        {
            "chunk_id": "composed_answer",
            "text": answer[:8000],
            "source": "system",
        }
    )

    stack = ChorusStack.defaults(tenant_id=tenant_id)

    def ops_handler(state: dict[str, Any]) -> dict[str, Any]:
        return {
            "question": state.get("question") or question,
            "answer": answer,
            "preload": preload,
            "guard_decision": "allow",
        }

    g = Graph(tenant_id=tenant_id, graph_id="ops_assistant")
    g.add_node("ops", dict_node_adapter(ops_handler, hop="ops"))
    g.add_edge(START, "ops")
    g.add_edge("ops", END)
    compiled = g.compile(stack=stack)
    graph_out = compiled.invoke({"question": question})
    graph_payload = {
        "graph_id": "ops_assistant",
        "tenant_id": tenant_id,
        "hops": [h.get("hop") for h in (graph_out.get("vector_hops") or [])],
        "latest_envelope_id": graph_out.get("latest_envelope_id"),
    }
    log.info("graph hops=%s", graph_payload["hops"])

    gate = _get_gate()
    shine_dec = post_llm_check(
        gate,
        {
            "question": question,
            "answer": graph_out.get("answer") or answer,
            "preload": preload,
        },
    )
    verdict = getattr(shine_dec, "verdict", None)
    shine_payload = {
        "action": getattr(shine_dec, "action", None),
        "decision": getattr(verdict, "decision", None) if verdict is not None else None,
        "resolution_gate": getattr(verdict, "resolution_gate", None) if verdict is not None else None,
        "fused_score": getattr(verdict, "fused_score", None) if verdict is not None else None,
        "confidence": getattr(verdict, "confidence", None) if verdict is not None else None,
        "advice": list(getattr(verdict, "advice", None) or [])[:5] if verdict is not None else [],
    }
    log.info(
        "shine action=%s decision=%s",
        shine_payload["action"],
        shine_payload["decision"],
    )

    final = graph_out.get("answer") or answer
    action = str(shine_payload.get("action") or "").lower()
    if action and action not in ("proceed", "pass", "allow", ""):
        final = (
            f"{final}\n\n---\n"
            f"*PrismShine action=`{shine_payload.get('action')}` "
            f"decision=`{shine_payload.get('decision')}` — not world-truth; "
            f"grounded only in preload/telemetry.*"
        )
    elif shine_payload.get("decision") and str(shine_payload["decision"]).lower() not in (
        "pass",
        "allow",
    ):
        final = (
            f"{final}\n\n---\n"
            f"*PrismShine {shine_payload.get('decision')} "
            f"({shine_payload.get('resolution_gate')}). "
            f"ALLOW/PASS != world-true.*"
        )

    return {
        "answer": final,
        "blocked": False,
        "wire": {
            "mode": "live",
            "stack": status,
            "guard": guard_payload,
            "graph": graph_payload,
            "shine": shine_payload,
            "llm": status.get("llm"),
            "note": status.get("note"),
        },
    }
