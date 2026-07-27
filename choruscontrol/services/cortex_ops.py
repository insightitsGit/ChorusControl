"""PrismCortex ops console — activity, graph chunks, digest/recall/sleep.

Uses public prismcortex APIs (Memory.digest / recall / sleep / conflicts /
explain / subgraph_at / on_event) with a deterministic stub extractor so the
dashboard works offline without Gemini.
"""

from __future__ import annotations

import logging
import re
import threading
import time
from typing import Any

log = logging.getLogger("choruscontrol.cortex_ops")

_lock = threading.RLock()
_memories: dict[str, Any] = {}
_activity: dict[str, list[dict[str, Any]]] = {}
_seeded: set[str] = set()


def prismcortex_available() -> bool:
    try:
        import prismcortex  # noqa: F401

        return True
    except Exception:  # noqa: BLE001
        return False


class _StubLLM:
    """Rule-based extractor/renderer — no external LLM required for ops console."""

    model_id = "choruscontrol-stub-v1"

    def extract(self, text: str, context) -> Any:
        from prismcortex.models import ExtractedEntity, ExtractedGist, ExtractedRelation

        raw = (text or "").strip()
        lower = raw.lower()
        is_corr = any(k in lower for k in ("correct", " now is ", "updated to", "changed to"))
        m = re.search(r"(.+?)\s+(?:is|are|=)\s+(.+?)[\.\!]?$", raw, re.I)
        if m:
            a, b = m.group(1).strip(), m.group(2).strip()
            return ExtractedGist(
                entities=[ExtractedEntity(label=a), ExtractedEntity(label=b)],
                relations=[ExtractedRelation(src=a, dst=b, relation="is")],
                is_correction=is_corr,
            )
        # keyword clinical seed style: "fact: value"
        m2 = re.search(r"^([^:]+):\s*(.+)$", raw)
        if m2:
            a, b = m2.group(1).strip(), m2.group(2).strip()
            return ExtractedGist(
                entities=[ExtractedEntity(label=a), ExtractedEntity(label=b)],
                relations=[ExtractedRelation(src=a, dst=b, relation="is")],
                is_correction=is_corr,
            )
        return ExtractedGist(entities=[ExtractedEntity(label=raw[:64] or "note")], relations=[])

    def render(self, query: str, subgraph) -> str:
        id_to_label = {n.id: n.label for n in subgraph.nodes}
        facts = []
        for e in subgraph.edges:
            if e.valid_to is None:
                facts.append(
                    f"{id_to_label.get(e.src, e.src)} {e.relation} {id_to_label.get(e.dst, e.dst)}"
                )
        return "; ".join(facts) or f"No consolidated facts for: {query}"


def _log(tenant_id: str, kind: str, **payload: Any) -> None:
    tid = tenant_id or "default"
    with _lock:
        bucket = _activity.setdefault(tid, [])
        bucket.insert(
            0,
            {
                "ts": time.time(),
                "kind": kind,
                "tenant_id": tid,
                **payload,
            },
        )
        del bucket[200:]


def _seed_texts(tenant_id: str) -> list[str]:
    if tenant_id.startswith("aurora") or tenant_id in ("aurora-health", "aurora-pharmacy"):
        return [
            "Medication recon policy is check allergies first.",
            "Discharge checklist is med recon plus follow-up tags.",
            "Insulin review is required during med recon for diabetic patients.",
            "Prior auth flag is surface high-cost meds during recon.",
            "Allergy cross-check is mandatory before discharge.",
        ]
    return [
        "Deploy budget is $55,000.",
        "Risk appetite is moderate.",
    ]


def get_memory(tenant_id: str) -> Any | None:
    if not prismcortex_available():
        return None
    tid = tenant_id or "default"
    with _lock:
        if tid in _memories:
            return _memories[tid]
        from prismcortex.adapters.reference import (
            DurableCache,
            HashingProjector,
            InMemoryGraphStore,
            InProcessMesh,
            InProcessResonance,
            ListStaging,
        )
        from prismcortex.engine import Memory

        stub = _StubLLM()
        mem = Memory(
            projector=HashingProjector(dim=128),
            extractor=stub,
            renderer=stub,
            store=InMemoryGraphStore(),
            resonance=InProcessResonance(),
            cache=DurableCache(),
            mesh=InProcessMesh(),
            staging=ListStaging(),
            tenant_id=tid,
            k=8,
        )

        def _on_event(ev) -> None:
            try:
                _log(
                    tid,
                    str(getattr(ev.kind, "value", ev.kind)),
                    subject=getattr(ev, "subject", None),
                    relation=getattr(ev, "relation", None),
                    old_value=getattr(ev, "old_value", None),
                    new_value=getattr(ev, "new_value", None),
                )
            except Exception:  # noqa: BLE001
                pass

        mem.on_event(_on_event)
        _memories[tid] = mem
        return mem


def ensure_seeded(tenant_id: str) -> dict[str, Any]:
    tid = tenant_id or "default"
    mem = get_memory(tid)
    if mem is None:
        return {"ok": False, "engine": "null", "seeded": False}
    with _lock:
        already = tid in _seeded
    if already:
        return {"ok": True, "engine": "prismcortex", "seeded": True}
    for text in _seed_texts(tid):
        result = mem.digest(text, source_id=f"seed:{tid}", agent_id="choruscontrol")
        _log(
            tid,
            "digest",
            text=text,
            outcome=str(getattr(result.outcome, "value", result.outcome)),
            version=getattr(result.version, "version", None),
            source="seed",
        )
    with _lock:
        _seeded.add(tid)
    log.info("cortex seeded tenant=%s", tid)
    return {"ok": True, "engine": "prismcortex", "seeded": True, "facts": len(_seed_texts(tid))}


def _serialize_node(n) -> dict[str, Any]:
    return {
        "id": n.id,
        "label": n.label,
        "kind": n.kind,
        "weight": n.weight,
        "confidence": n.confidence,
        "band": str(getattr(n.band, "value", n.band)),
        "embedding_dim": len(n.embedding or []),
        "chunk_ref": n.id,
        "chunk_text": n.label,
        "created_at": n.created_at.isoformat() if getattr(n, "created_at", None) else None,
    }


def _serialize_edge(e, id_to_label: dict[str, str]) -> dict[str, Any]:
    return {
        "id": e.id,
        "src": e.src,
        "dst": e.dst,
        "src_label": id_to_label.get(e.src, e.src),
        "dst_label": id_to_label.get(e.dst, e.dst),
        "relation": e.relation,
        "weight": e.weight,
        "confidence": e.confidence,
        "current": e.valid_to is None,
        "valid_from": e.valid_from.isoformat() if e.valid_from else None,
        "valid_to": e.valid_to.isoformat() if e.valid_to else None,
        "fact": f"{id_to_label.get(e.src, e.src)} {e.relation} {id_to_label.get(e.dst, e.dst)}",
    }


def snapshot(tenant_id: str) -> dict[str, Any]:
    """Full Cortex console payload: activity, chunks, facts, conflicts, version."""
    tid = tenant_id or "default"
    seed = ensure_seeded(tid)
    mem = get_memory(tid)
    if mem is None:
        return {
            "tenant_id": tid,
            "engine": "null",
            "demo": True,
            "seed": seed,
            "activity": [],
            "chunks": [],
            "edges": [],
            "facts": [],
            "conflicts": [],
            "version": None,
            "note": 'Install prismcortex>=0.3.0 for live Cortex activity. pip install "prismcortex==0.3.0"',
        }

    store = mem.store
    nodes = list(getattr(store, "_nodes", {}).values())
    edges = list(getattr(store, "_edges", {}).values())
    id_to_label = {n.id: n.label for n in nodes}
    current_edges = [e for e in edges if e.valid_to is None]
    facts = [_serialize_edge(e, id_to_label) for e in current_edges]
    superseded = [_serialize_edge(e, id_to_label) for e in edges if e.valid_to is not None]
    chunks = [_serialize_node(n) for n in nodes]
    conflicts = list(mem.conflicts() or [])
    version = getattr(store, "_version", None)
    with _lock:
        activity = list(_activity.get(tid, []))[:80]
    return {
        "tenant_id": tid,
        "engine": "prismcortex",
        "demo": False,
        "seed": seed,
        "activity": activity,
        "chunks": chunks,
        "edges": [_serialize_edge(e, id_to_label) for e in edges],
        "facts": facts,
        "superseded": superseded,
        "conflicts": conflicts,
        "version": version,
        "node_count": len(nodes),
        "edge_count": len(edges),
        "current_fact_count": len(facts),
    }


def digest(tenant_id: str, text: str, *, agent_id: str | None = None) -> dict[str, Any]:
    tid = tenant_id or "default"
    ensure_seeded(tid)
    mem = get_memory(tid)
    if mem is None:
        raise RuntimeError("prismcortex not installed")
    result = mem.digest(text, source_id=f"ui:{tid}", agent_id=agent_id or "ops-console")
    out = {
        "ok": True,
        "outcome": str(getattr(result.outcome, "value", result.outcome)),
        "band": str(getattr(result.band, "value", result.band)),
        "version": getattr(result.version, "version", None),
        "content_hash": getattr(result.version, "content_hash", None),
        "reason": result.reason,
        "ops": len(result.delta.ops) if result.delta else 0,
    }
    _log(tid, "digest", text=text[:500], **{k: out[k] for k in ("outcome", "band", "version")})
    return out


def recall(tenant_id: str, query: str) -> dict[str, Any]:
    tid = tenant_id or "default"
    ensure_seeded(tid)
    mem = get_memory(tid)
    if mem is None:
        raise RuntimeError("prismcortex not installed")
    result = mem.recall(query)
    out = {
        "ok": True,
        "answer": result.answer,
        "cache_hit": result.cache_hit,
        "version": result.version,
        "confidence": result.confidence,
        "provisional": result.provisional,
        "node_ids": list(result.node_ids or []),
        "edge_ids": list(result.edge_ids or []),
        "model_id": result.model_id,
    }
    _log(tid, "recall", query=query[:300], cache_hit=result.cache_hit, version=result.version)
    return out


def explain(tenant_id: str, query: str) -> dict[str, Any]:
    tid = tenant_id or "default"
    ensure_seeded(tid)
    mem = get_memory(tid)
    if mem is None:
        raise RuntimeError("prismcortex not installed")
    exp = mem.explain(query)
    evidence = []
    for ev in exp.evidence or []:
        evidence.append(
            {
                "fact": ev.fact,
                "source_id": ev.source_id,
                "confidence": ev.confidence,
                "confirmations": ev.confirmations,
                "supersedes_prior": getattr(ev, "supersedes_prior", False),
                "prior_value": getattr(ev, "prior_value", None),
            }
        )
    out = {
        "ok": True,
        "query": exp.query,
        "version": exp.version,
        "confidence": exp.confidence,
        "subgraph_hash": exp.subgraph_hash,
        "evidence": evidence,
    }
    _log(tid, "explain", query=query[:300], evidence_count=len(evidence))
    return out


def sleep_tenant(tenant_id: str) -> dict[str, Any]:
    tid = tenant_id or "default"
    ensure_seeded(tid)
    mem = get_memory(tid)
    if mem is None:
        raise RuntimeError("prismcortex not installed")
    n = mem.sleep()
    _log(tid, "sleep", consolidated=n)
    return {"ok": True, "consolidated": n, "tenant_id": tid}


def resolve_conflict(
    tenant_id: str, subject: str, relation: str, chosen_value: str
) -> dict[str, Any]:
    tid = tenant_id or "default"
    ensure_seeded(tid)
    mem = get_memory(tid)
    if mem is None:
        raise RuntimeError("prismcortex not installed")
    ver = mem.resolve_conflict(subject, relation, chosen_value)
    _log(
        tid,
        "conflict_resolved",
        subject=subject,
        relation=relation,
        new_value=chosen_value,
        version=getattr(ver, "version", None),
    )
    return {
        "ok": True,
        "version": getattr(ver, "version", None),
        "content_hash": getattr(ver, "content_hash", None),
    }


async def resolve_snapshot(state, tenant_id: str) -> dict[str, Any]:
    """R04 — prefer tenant memory_endpoint; proxy remote HTTP; else mother-local."""
    tid = tenant_id or "default"
    endpoint = await state.fleet.memory_endpoint_for_tenant(tid)
    if endpoint and endpoint.startswith(("http://", "https://")):
        try:
            import httpx

            async with httpx.AsyncClient(timeout=30.0) as client:
                r = await client.get(
                    f"{endpoint.rstrip('/')}/api/v1/cortex/snapshot",
                    params={"tenant_id": tid},
                    headers={"Authorization": f"Bearer {state.settings.admin_token}"},
                )
                if r.status_code < 400:
                    data = r.json()
                    data["memory_endpoint"] = endpoint
                    data["serving"] = "remote-proxy"
                    return data
                return {
                    "tenant_id": tid,
                    "engine": "proxy_error",
                    "demo": False,
                    "memory_endpoint": endpoint,
                    "serving": "remote-proxy",
                    "error": f"HTTP {r.status_code}",
                    "activity": [],
                    "chunks": [],
                    "facts": [],
                    "conflicts": [],
                }
        except Exception as exc:  # noqa: BLE001
            return {
                "tenant_id": tid,
                "engine": "proxy_error",
                "demo": False,
                "memory_endpoint": endpoint,
                "serving": "remote-proxy",
                "error": str(exc),
                "activity": [],
                "chunks": [],
                "facts": [],
                "conflicts": [],
            }
    local = snapshot(tid)
    local["memory_endpoint"] = endpoint
    local["serving"] = "mother-local" if not (endpoint or "").startswith("local://") else endpoint
    return local
