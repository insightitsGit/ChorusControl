"""Ops Assistant actionable catalog — per-tab gated executes (agent KB).

Each entry is executable via POST /assistant/ask with confirm=true + execute={type,params}.
Teach prompts explain; run prompts propose Confirm buttons.
"""

from __future__ import annotations

import re
from typing import Any, Callable

ParamFn = Callable[[dict[str, Any], str], dict[str, Any]]


def _tenant(snap: dict[str, Any], q: str = "") -> str:
    if "aurora" in (q or ""):
        return "aurora-health"
    return (
        (snap.get("chats") or {}).get("tenant_hint")
        or snap.get("tenant_hint")
        or (snap.get("taxonomy") or {}).get("tenant_id")
        or "default"
    )


def _latest_run(snap: dict[str, Any]) -> str | None:
    return (snap.get("trace") or {}).get("latest_run_id") or (snap.get("pipeline") or {}).get("run_id")


def _partition(snap: dict[str, Any]) -> str:
    parts = (snap.get("taxonomy") or {}).get("partitions") or []
    if parts and isinstance(parts[0], dict):
        return str(parts[0].get("partition") or "kb_clinical_guidelines")
    return "kb_clinical_guidelines"


def _first_asset(snap: dict[str, Any], graph: dict[str, Any] | None = None) -> str | None:
    # graph may be passed separately; snap may not include assets
    return None


# --- Catalog (source of truth for agent + design docs) ---

ACTION_CATALOG: list[dict[str, Any]] = [
    # Overview
    {
        "id": "cascade.run",
        "tab": "overview",
        "type": "cascade",
        "label": "Run correction cascade",
        "mutating": True,
        "teaches": "Invalidates cache/graph/shine after memory corrections.",
        "prompts": [
            "run cascade",
            "trigger cascade",
            "start cascade",
            "run correction cascade",
            "execute cascade",
        ],
        "params": lambda snap, q: {
            "tenant_id": _tenant(snap, q),
            "tags": ["assistant:manual"],
            "reason": "assistant",
        },
    },
    {
        "id": "incident.create",
        "tab": "overview",
        "type": "incident.create",
        "label": "Open incident",
        "mutating": True,
        "teaches": "Creates an incident row linked for intelligence / Overview.",
        "prompts": [
            "open an incident",
            "create incident",
            "open incident",
            "file an incident",
        ],
        "params": lambda snap, q: {
            "tenant_id": _tenant(snap, q),
            "title": "Assistant-opened incident",
            "details": {"source": "assistant"},
        },
    },
    {
        "id": "graph.blast_radius",
        "tab": "overview",
        "type": "graph.blast_radius",
        "label": "Blast radius",
        "mutating": False,
        "teaches": "Shows Asset Graph neighbors for an asset_id.",
        "prompts": [
            "blast radius",
            "show blast radius",
            "run blast radius",
        ],
        "params": lambda snap, q: {"asset_id": _extract_token(q, prefix="asset") or "fleet:mother"},
    },
    {
        "id": "compliance.scan",
        "tab": "overview",
        "type": "compliance.scan",
        "label": "Compliance scan",
        "mutating": True,
        "teaches": "Writes automated posture findings (not a SOC2 attestation).",
        "prompts": [
            "run compliance scan",
            "compliance scan",
            "scan compliance",
        ],
        "params": lambda snap, q: {},
    },
    # Trace
    {
        "id": "traces.seed",
        "tab": "trace",
        "type": "traces.seed",
        "label": "Seed demo trace",
        "mutating": True,
        "teaches": "Seeds a Guard→Ledger→Shine demo run for the tenant.",
        "prompts": [
            "seed demo trace",
            "seed a trace",
            "seed trace",
            "create demo trace",
        ],
        "params": lambda snap, q: {"tenant_id": _tenant(snap, q)},
    },
    {
        "id": "traces.replay",
        "tab": "trace",
        "type": "traces.replay",
        "label": "Replay trace",
        "mutating": False,
        "teaches": "Zero-token replay of a stored run_id (feature trace.replay).",
        "prompts": [
            "replay the trace",
            "replay selected",
            "replay run",
            "zero-token replay",
            "run replay",
            "replay trace",
        ],
        "params": lambda snap, q: {
            "run_id": _extract_run_id(q) or _latest_run(snap),
        },
    },
    # Taxonomy
    {
        "id": "taxonomy.reindex",
        "tab": "taxonomy",
        "type": "taxonomy.reindex",
        "command": "taxonomy.reindex",
        "label": "Reindex taxonomy",
        "mutating": True,
        "teaches": "Queues taxonomy.reindex job for the tenant.",
        "prompts": [
            "reindex taxonomy",
            "run reindex",
            "taxonomy reindex",
            "reindex the knowledge",
            "rebuild indexes",
        ],
        "params": lambda snap, q: {"tenant_id": _tenant(snap, q)},
    },
    {
        "id": "taxonomy.warm_partition",
        "tab": "taxonomy",
        "type": "taxonomy.warm_partition",
        "command": "taxonomy.warm_partition",
        "label": "Warm partition",
        "mutating": True,
        "teaches": "Queues warm_partition for a KB partition (reduces staleness).",
        "prompts": [
            "warm partition",
            "warm the partition",
            "run warm",
            "warm taxonomy",
            "warm kb",
        ],
        "params": lambda snap, q: {
            "tenant_id": _tenant(snap, q),
            "partition": _extract_partition(q) or _partition(snap),
        },
    },
    {
        "id": "taxonomy.search",
        "tab": "taxonomy",
        "type": "taxonomy.search",
        "label": "Taxonomy search",
        "mutating": False,
        "teaches": "Runs PrismRAG / NullRAG search for a query string.",
        "prompts": [
            "search taxonomy",
            "taxonomy search",
            "search the knowledge base",
            "search kb for",
        ],
        "params": lambda snap, q: {
            "tenant_id": _tenant(snap, q),
            "query": _extract_after(q, ("for", ":", "search")) or "clinical guidelines",
        },
    },
    # Cortex
    {
        "id": "cortex.digest",
        "tab": "cortex",
        "type": "cortex.digest",
        "label": "Cortex digest",
        "mutating": True,
        "teaches": "Digests text into PrismCortex tenant memory.",
        "prompts": [
            "run cortex digest",
            "cortex digest",
            "digest into cortex",
            "digest this",
        ],
        "params": lambda snap, q: {
            "tenant_id": _tenant(snap, q),
            "text": _extract_after(q, (":", "digest"))
            or "Ops note: admin requested Cortex digest from Ops Assistant.",
        },
    },
    {
        "id": "cortex.recall",
        "tab": "cortex",
        "type": "cortex.recall",
        "label": "Cortex recall",
        "mutating": False,
        "teaches": "Recalls from PrismCortex for a query.",
        "prompts": [
            "run cortex recall",
            "cortex recall",
            "recall from cortex",
            "recall memory",
        ],
        "params": lambda snap, q: {
            "tenant_id": _tenant(snap, q),
            "query": _extract_after(q, (":", "recall")) or "recent facts",
        },
    },
    {
        "id": "cortex.explain",
        "tab": "cortex",
        "type": "cortex.explain",
        "label": "Cortex explain",
        "mutating": False,
        "teaches": "Explains recall grounding for a query.",
        "prompts": [
            "cortex explain",
            "explain cortex recall",
            "run cortex explain",
        ],
        "params": lambda snap, q: {
            "tenant_id": _tenant(snap, q),
            "query": _extract_after(q, (":", "explain")) or "recent facts",
        },
    },
    {
        "id": "cortex.sleep",
        "tab": "cortex",
        "type": "cortex.sleep",
        "label": "Cortex sleep",
        "mutating": True,
        "teaches": "Consolidates memory + enqueues cortex.sleep job for fleet.",
        "prompts": [
            "run cortex sleep",
            "cortex sleep",
            "sleep cortex",
            "run sleep for this tenant",
            "consolidate memory",
        ],
        "params": lambda snap, q: {"tenant_id": _tenant(snap, q)},
    },
    {
        "id": "cortex.conflict_resolve",
        "tab": "cortex",
        "type": "cortex.conflict_resolve",
        "label": "Resolve Cortex conflict",
        "mutating": True,
        "teaches": "Resolves a conflict and runs correction cascade.",
        "prompts": [
            "resolve cortex conflict",
            "keep new cortex",
            "resolve memory conflict",
            "resolve conflict",
        ],
        "params": lambda snap, q: {
            "tenant_id": _tenant(snap, q),
            "conflict_id": _extract_token(q, prefix="conflict") or "",
            "resolution": "keep_new",
            "subject": _extract_after(q, ("subject", ":")) or "",
        },
    },
    # Guard
    {
        "id": "guard.shadow_compare",
        "tab": "guard",
        "type": "guard.shadow_compare",
        "label": "Shadow compare",
        "mutating": False,
        "teaches": "Compares ingress vs shadow Guard profiles.",
        "prompts": [
            "shadow compare",
            "run shadow compare",
            "compare guard shadow",
            "guard shadow compare",
        ],
        "params": lambda snap, q: {"tenant_id": _tenant(snap, q)},
    },
    {
        "id": "guard.policy_put",
        "tab": "guard",
        "type": "guard.policy.put",
        "label": "Save Guard policy",
        "mutating": True,
        "teaches": "Writes Policy Studio document for the tenant (needs policy JSON in params).",
        "prompts": [
            "save guard policy",
            "update guard policy",
            "put guard policy",
        ],
        "params": lambda snap, q: {
            "tenant_id": _tenant(snap, q),
            "policy": (snap.get("guard") or {}),
        },
    },
    # Logs
    {
        "id": "logs.search",
        "tab": "logs",
        "type": "logs.search",
        "label": "Search ops logs",
        "mutating": False,
        "teaches": "Searches the mother ops log bus (same as Logs tab).",
        "prompts": [
            "search ops logs",
            "search logs",
            "find logs for",
            "show fleet logs",
            "filter logs",
        ],
        "params": lambda snap, q: {
            "q": _extract_after(q, ("for", ":", "logs", "search")) or "",
            "source": _extract_log_source(q),
            "limit": 50,
        },
    },
    # Admin
    {
        "id": "fleet.join_token",
        "tab": "admin",
        "type": "fleet.join_token",
        "label": "Create join token",
        "mutating": True,
        "teaches": "Issues a fleet join token for agent enrollment.",
        "prompts": [
            "create join token",
            "make join token",
            "issue join token",
            "new join token",
        ],
        "params": lambda snap, q: {"max_uses": 10, "ttl_seconds": 3600},
    },
    {
        "id": "compliance.scan.admin",
        "tab": "admin",
        "type": "compliance.scan",
        "label": "Compliance scan",
        "mutating": True,
        "teaches": "Same compliance scan as Admin → Compliance scan.",
        "prompts": [
            "run compliance scan",
            "admin compliance scan",
        ],
        "params": lambda snap, q: {},
    },
    {
        "id": "admin.license_online_check",
        "tab": "admin",
        "type": "admin.license_online_check",
        "label": "License online check",
        "mutating": False,
        "teaches": "Optional Side 1 online revoke check (disabled in air-gap).",
        "prompts": [
            "license online check",
            "run online check",
            "check license online",
            "side 1 online check",
        ],
        "params": lambda snap, q: {},
    },
    {
        "id": "admin.doctor",
        "tab": "admin",
        "type": "admin.doctor",
        "label": "Doctor snapshot",
        "mutating": False,
        "teaches": "Returns mother doctor JSON (pins, adapters, license).",
        "prompts": [
            "run doctor",
            "show doctor",
            "doctor snapshot",
            "check doctor",
        ],
        "params": lambda snap, q: {},
    },
    {
        "id": "chats.list",
        "tab": "admin",
        "type": "chats.list",
        "label": "List client chats",
        "mutating": False,
        "teaches": "Lists end-user AI sessions (not Ops Assistant).",
        "prompts": [
            "list client chats",
            "list client sessions",
            "show client chats",
            "list end-user chats",
        ],
        "params": lambda snap, q: {"tenant_id": _tenant(snap, q), "limit": 50},
    },
    {
        "id": "chats.get",
        "tab": "admin",
        "type": "chats.get",
        "label": "Open client chat session",
        "mutating": False,
        "teaches": "Opens one end-user session transcript.",
        "prompts": [
            "open client chat",
            "open chat session",
            "show session",
            "get chat session",
        ],
        "params": lambda snap, q: {
            "session_id": _extract_session_id(q, snap),
        },
    },
    {
        "id": "chats.compact",
        "tab": "admin",
        "type": "chats.compact",
        "label": "Compact client chat session",
        "mutating": True,
        "teaches": "PrismCortex digest + prune raw bodies for one session.",
        "prompts": [
            "compact this session",
            "compact chat session",
            "compact client session",
        ],
        "params": lambda snap, q: {
            "session_id": _extract_session_id(q, snap),
            "prune": True,
        },
    },
    {
        "id": "chats.compact_tenant",
        "tab": "admin",
        "type": "chats.compact_tenant",
        "label": "Compact raw client chats",
        "mutating": True,
        "teaches": "Batch-compacts raw/dirty end-user sessions for a tenant.",
        "prompts": [
            "compact raw client chat sessions",
            "compact client chats",
            "compact all client chats",
            "compact end-user chats",
            "prune client chats",
        ],
        "params": lambda snap, q: {"tenant_id": _tenant(snap, q), "limit": 20},
    },
]


def _extract_after(q: str, markers: tuple[str, ...]) -> str:
    lower = q.lower()
    for m in markers:
        idx = lower.find(m)
        if idx >= 0:
            rest = q[idx + len(m) :].strip(" :\"'")
            if rest:
                return rest[:500]
    return ""


def _extract_run_id(q: str) -> str | None:
    m = re.search(r"\brun[_-]?([a-zA-Z0-9-]{4,})\b", q, re.I)
    if m:
        return m.group(0) if m.group(0).startswith("run") else f"run-{m.group(1)}"
    m = re.search(r"\b(run-[a-zA-Z0-9-]+)\b", q)
    return m.group(1) if m else None


def _extract_partition(q: str) -> str | None:
    m = re.search(r"\b(kb_[a-z0-9_]+)\b", q, re.I)
    return m.group(1) if m else None


def _extract_token(q: str, prefix: str) -> str | None:
    m = re.search(rf"\b{prefix}[_:-]?([a-zA-Z0-9.:_-]+)\b", q, re.I)
    if m:
        return m.group(0) if ":" in m.group(0) or m.group(0).startswith(prefix) else f"{prefix}:{m.group(1)}"
    return None


def _extract_log_source(q: str) -> str | None:
    for src in ("audit", "fleet", "ledger", "cascade", "system", "agent"):
        if src in q.lower():
            return src
    return None


def _extract_session_id(q: str, snap: dict[str, Any]) -> str | None:
    m = re.search(r"\b(sess-[a-zA-Z0-9-]+)\b", q)
    if m:
        return m.group(1)
    sessions = (snap.get("chats") or {}).get("sessions") or []
    if sessions:
        return sessions[0].get("session_id")
    return None


def catalog_by_tab() -> dict[str, list[dict[str, Any]]]:
    out: dict[str, list[dict[str, Any]]] = {}
    for a in ACTION_CATALOG:
        out.setdefault(a["tab"], []).append(a)
    return out


def format_actions_kb(tab: str | None = None) -> str:
    """Markdown-ish plain text for Assistant / design docs."""
    lines = ["# Ops Assistant actionable catalog", ""]
    by = catalog_by_tab()
    tabs = [tab] if tab else list(by.keys())
    for t in tabs:
        lines.append(f"## Tab: {t}")
        lines.append("")
        for a in by.get(t) or []:
            lines.append(f"### {a['label']} (`{a['type']}`)")
            lines.append(f"- Mutating: {a.get('mutating')}")
            lines.append(f"- Means: {a.get('teaches')}")
            lines.append("- Example prompts:")
            for p in a.get("prompts") or []:
                lines.append(f"  - “{p}”")
            lines.append("")
    return "\n".join(lines)


def match_actions(question: str, snap: dict[str, Any], *, limit: int = 6) -> list[dict[str, Any]]:
    """Return gated execute payloads for prompts that ask to run a catalog action."""
    q = (question or "").strip().lower()
    if not q:
        return []
    # Pure literacy questions — still allow if they contain an exact action phrase
    wants_list = any(
        p in q
        for p in (
            "what can you do",
            "what actions",
            "list actions",
            "available actions",
            "what can i run",
        )
    )
    if wants_list:
        return []  # caller uses format_actions_kb

    scored: list[tuple[int, dict[str, Any]]] = []
    for entry in ACTION_CATALOG:
        prompts = [p.lower() for p in (entry.get("prompts") or [])]
        hit = None
        best = 0
        for p in prompts:
            if p in q:
                score = len(p)
                if score > best:
                    best = score
                    hit = p
        if not hit:
            # soft: type/command tokens
            typ = (entry.get("type") or "").lower().replace(".", " ")
            if typ and typ in q and any(w in q for w in ("run", "do", "execute", "trigger", "start", "please")):
                best = 5
                hit = typ
        if not hit:
            continue
        params_fn = entry.get("params")
        params = params_fn(snap, question) if callable(params_fn) else {}
        # Skip incomplete required ids
        if entry["type"] == "traces.replay" and not params.get("run_id"):
            continue
        if entry["type"] in ("chats.get", "chats.compact") and not params.get("session_id"):
            continue
        if entry["type"] == "cortex.conflict_resolve" and not params.get("conflict_id") and "conflict" in q:
            # still propose — execute will nack if empty
            pass
        action = {
            "type": entry["type"],
            "command": entry.get("command") or entry["type"],
            "label": entry["label"],
            "requires_confirmation": True,
            "mutating": bool(entry.get("mutating")),
            "tab": entry["tab"],
            "id": entry["id"],
            "params": params,
        }
        scored.append((best, action))

    scored.sort(key=lambda x: -x[0])
    # de-dupe by type
    seen: set[str] = set()
    out: list[dict[str, Any]] = []
    for _, a in scored:
        key = a["type"]
        if key in seen:
            continue
        seen.add(key)
        out.append(a)
        if len(out) >= limit:
            break
    return out


def actions_for_tab_teach(tab: str) -> str:
    """Short teach block listing runnable prompts for a tab."""
    rows = catalog_by_tab().get(tab) or []
    if not rows:
        return f"No gated actions registered for tab `{tab}`."
    lines = [f"On **{tab}**, I can gated-execute (Confirm required):"]
    for a in rows:
        sample = (a.get("prompts") or ["…"])[0]
        lines.append(f"- **{a['label']}** — say “{sample}” → `{a['type']}`")
    return "\n".join(lines)
