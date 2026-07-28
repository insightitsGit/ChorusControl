"""Plain-English glossaries for every primary mother dashboard value (HO-009)."""

from __future__ import annotations

from typing import Any

TAXONOMY_PLAIN: dict[str, dict[str, str]] = {
    "engine": {
        "means": "Which RAG backend Taxonomy is talking to right now.",
        "how": "`prismrag-patch` (or live PrismRAG) means real retrieval; `null` means honest DEMO NullRAG.",
        "good": "live engine when DEMO_MODE=0 and [prism] packs installed",
        "bad": "null/DEMO when you expected production Taxonomy — install prismrag-patch + prismguard",
        "tab": "/taxonomy",
        "action": "Admin → Doctor → check taxonomy_packs / install_hint",
    },
    "partition_version": {
        "means": "How many times this knowledge partition was warmed or reindexed.",
        "how": "Warm partition / reindex jobs bump the version integer (e.g. v3).",
        "good": "Version rises after intentional warm/reindex",
        "bad": "Stuck at v0/v1 while content is stale — run Warm partition",
        "tab": "/taxonomy",
        "action": "Taxonomy → Warm partition or Reindex",
    },
    "category_tree": {
        "means": "Slugs that map clinical/domain folders into PrismRAG categories.",
        "how": "Tree comes from PrismRAG mapping (or DEMO seed categories).",
        "good": "Categories match your tenant’s knowledge layout",
        "bad": "Empty tree — packs missing or tenant not seeded",
        "tab": "/taxonomy",
    },
    "staleness": {
        "means": "How old/decayed a category’s chunks look (0 = fresh, higher = staler).",
        "how": "Chunk health uses PrismRAG decay signals; UI marks >0.3 as stale.",
        "good": "Near 0 / labeled fresh",
        "bad": "High staleness — warm or reindex that category",
        "tab": "/taxonomy",
        "action": "Taxonomy → Warm partition",
    },
    "bleed_risk": {
        "means": "Cross-tenant / cross-category contamination risk signal from chunk health.",
        "how": "Reported by PrismRAG health when available; may be n/a in DEMO.",
        "good": "Low or n/a with honest label",
        "bad": "Elevated bleed risk — review partitions and tenant isolation",
        "tab": "/taxonomy",
    },
    "search_score": {
        "means": "How strongly an embed/community retrieval hit matches your query.",
        "how": "Not keyword magic alone — PrismRAG ranks by embedding similarity (related chips from communities).",
        "good": "Top hits contain your term or a clear semantic neighbor",
        "bad": "Empty results — warm packs or try a shorter term",
        "tab": "/taxonomy",
    },
    "overwrite": {
        "means": "Admin online rewrite of a chunk via PrismRAG append_chunks (upsert by ref).",
        "how": "Edit shows quality_score and embedding_dim after save.",
        "good": "Overwrite returns quality + non-zero embedding dim",
        "bad": "Fails when packs missing or license grace blocks mutations",
        "tab": "/taxonomy",
        "action": "Taxonomy → Search → Edit → Save overwrite",
    },
    "taxonomy_packs": {
        "means": "Whether PrismRAG + PrismGuard are ready so Taxonomy is not forced to DEMO.",
        "how": "`taxonomy_packs.ready=true` when both packs meet pin floors; otherwise install_hint.",
        "good": "ready=true outside DEMO",
        "bad": "ready=false with DEMO_MODE=0 → Taxonomy API returns 503",
        "tab": "/admin",
        "action": "pip install choruscontrol[server,prism]",
    },
}

TRACE_PLAIN: dict[str, dict[str, str]] = {
    "run_id": {
        "means": "One stitched Guard → Ledger → Shine execution identity.",
        "how": "Seeded or shipped via agent ledger-batch; Overview/Trace wire uses the latest run.",
        "good": "You can open a run and see stages",
        "bad": "No runs — seed a demo trace or enroll agents that export ledger",
        "tab": "/trace",
    },
    "wire_stages": {
        "means": "Ordered evidence: Guard decision → Graph/ledger hops → Shine verdict.",
        "how": "Each stage is policy/graph/grounding evidence — not world-truth PASS.",
        "good": "allow/pass with coherent hops",
        "bad": "block/flag/error — inspect that stage detail",
        "tab": "/trace",
    },
    "ledger": {
        "means": "Append-only sampled stage evidence from workers (async, never on hot path).",
        "how": "Agents POST /fleet/ledger-batch; mother stores and streams Trace.",
        "good": "Batches kept with important guard/shine rows",
        "bad": "High agent_ledger_dropped_total — mother slow or queue full",
        "tab": "/trace",
    },
    "replay": {
        "means": "Zero-token replay: restitch from cache/ledger without calling an LLM.",
        "how": "POST /traces/{id}/replay asserts no provider/call_llm on the path.",
        "good": "Replay returns stages from store only",
        "bad": "Missing run_id or feature trace.replay gated off",
        "tab": "/trace",
        "action": "Trace → select run → Replay",
    },
}

GUARD_PLAIN: dict[str, dict[str, str]] = {
    "ingress_profile": {
        "means": "Which Guard profile checks user prompts on ingress (e.g. web_chat, clinical_chat).",
        "how": "Hub profiles stay light; heavy/law profiles are for stricter lanes — Policy Studio sets this.",
        "good": "Profile matches the product lane",
        "bad": "Hub forced onto law ONNX — avoid that; use recommended presets",
        "tab": "/guard",
    },
    "shadow_profile": {
        "means": "Side-car profile compared to ingress without enforcing by default.",
        "how": "shadow_enabled runs compare; enforce_shadow would apply the shadow decision.",
        "good": "Shadow compare empty/high agree = profiles aligned",
        "bad": "Large divergences — review before promote",
        "tab": "/guard",
        "action": "Guard → Shadow compare",
    },
    "shadow_compare": {
        "means": "Diff between ingress vs shadow decisions on sample prompts.",
        "how": "Agree rate + divergence list; empty diff means profiles agree on samples.",
        "good": "High agree_rate",
        "bad": "Many divergences — do not promote blindly",
        "tab": "/guard",
    },
    "lexicon": {
        "means": "Tenant term list Guard uses for sensitive/PHI-style tokens.",
        "how": "Policy Studio lexicon is tenant-scoped; updates are audited.",
        "good": "Terms match your domain vocabulary",
        "bad": "Empty lexicon when domain needs term hits",
        "tab": "/guard",
    },
    "caps_demo": {
        "means": "Whether Guard caps are live prismguard or honest NullGuard DEMO.",
        "how": "Caps tab/Overview Security dimension follow this.",
        "good": "live source outside DEMO",
        "bad": "demo=true while DEMO_MODE=0 and you expected live — install prismguard",
        "tab": "/guard",
    },
}

CORTEX_PLAIN: dict[str, dict[str, str]] = {
    "engine": {
        "means": "Memory backend for digest/recall/sleep — prismcortex live vs null DEMO.",
        "how": "Cortex tab shows engine + chunk/fact counts from snapshot.",
        "good": "prismcortex when packs installed",
        "bad": "null — DEMO memory only",
        "tab": "/cortex",
    },
    "digest": {
        "means": "Ingest a fact into bitemporal memory (committed) or skip if duplicate/conflict.",
        "how": "Digest returns committed/skipped; conflicts appear for resolve.",
        "good": "committed for new facts",
        "bad": "skipped unexpectedly — check conflicts panel",
        "tab": "/cortex",
        "action": "Cortex → Digest",
    },
    "recall": {
        "means": "Answer from the memory subgraph for this tenant — not a web LLM search.",
        "how": "Recall/explain use Cortex graph; confidence/version come from graph versioning.",
        "good": "Answer cites tenant memory",
        "bad": "Empty recall — digest first or wrong tenant",
        "tab": "/cortex",
    },
    "sleep": {
        "means": "Compaction pass that consolidates memories (count of consolidated items).",
        "how": "Sleep job/button runs cortex.sleep for the tenant.",
        "good": "Consolidated count rises when overdue",
        "bad": "Always 0 with huge graph — schedule sleep",
        "tab": "/cortex",
        "action": "Cortex → Sleep",
    },
    "activity": {
        "means": "Recent digest / sleep / conflict events in plain feed form.",
        "how": "Activity kinds are operational breadcrumbs, not Shine world-truth.",
        "good": "Feed reflects your recent actions",
        "bad": "Empty after actions — refresh snapshot",
        "tab": "/cortex",
    },
}

DOCTOR_PLAIN: dict[str, dict[str, str]] = {
    "license": {
        "means": "Offline Ed25519 verify of the Side 1 JWT: valid, grace, or invalid/missing.",
        "how": "Grace is read-only mutations; invalid blocks APIs. Optional ~14d online revoke check.",
        "good": "valid",
        "bad": "grace/invalid — renew via portal / Admin → License",
        "tab": "/admin",
        "action": "Admin → License",
    },
    "pin_floors": {
        "means": "Minimum sibling package versions; core vs optional tiers.",
        "how": "Core pins ship with [prism]; optional (fabric/mesh/lang) can be missing without failing Taxonomy readiness.",
        "good": "core ok; optional missing is OK if unused",
        "bad": "core missing — Taxonomy/live adapters will not activate",
        "tab": "/admin",
        "action": "Follow install_hint from Doctor",
    },
    "core_vs_optional": {
        "means": "Core = required Prism stack; optional = fabric/mesh/lang extras.",
        "how": "Missing optional pin ≠ broken mother; missing core pin blocks live Taxonomy/Guard/etc.",
        "good": "Understand optional gaps as intentional",
        "bad": "Treating optional missing like a production outage",
        "tab": "/admin",
    },
    "adapters": {
        "means": "Per-adapter source: live:… vs null (DEMO NullAdapter).",
        "how": "Doctor adapters map cache/guard/shine/cortex/graph/rag/fabric.",
        "good": "live:* in production",
        "bad": "null with DEMO_MODE=0 when you expected packs",
        "tab": "/admin",
    },
    "install_hint": {
        "means": "Exact pip extra Doctor recommends when pins/taxonomy packs are short.",
        "how": "Copied from pin/taxonomy readiness — usually choruscontrol[server,prism].",
        "good": "Follow hint then restart mother",
        "bad": "Ignoring hint while Taxonomy 503s",
        "tab": "/admin",
    },
    "join_token": {
        "means": "One-time enrollment secret so a worker agent can join this mother.",
        "how": "Admin creates token; agent uses CHORUSCONTROL_JOIN_TOKEN; max_nodes from license.",
        "good": "Workers appear online on Overview",
        "bad": "Join fails — expired token or max_nodes",
        "tab": "/admin",
        "action": "Admin → Create join token",
    },
    "compliance": {
        "means": "Automated posture findings (e.g. auto.adapters.null) — not a SOC2 certification.",
        "how": "Compliance scan writes findings; SOC2 export is an evidence zip for auditors.",
        "good": "Findings understood and remediated",
        "bad": "Calling the zip a certification",
        "tab": "/admin",
    },
    "soc2_export": {
        "means": "Downloadable evidence pack (audit JSONL + pubkey + doctor snapshot) — not an attestation.",
        "how": "Admin → SOC2 export; verify with choruscontrol audit-verify.",
        "good": "Zip verifies with public key",
        "bad": "Treating export as ‘we are SOC2 certified’",
        "tab": "/admin",
    },
    "client_ai_chats": {
        "means": "History of end-user / client AI sessions (apps & agents) — not the Ops Assistant drawer on this console.",
        "how": "Admin → Client AI chats lists sessions; Compact digests a summary into PrismCortex and prunes raw message bodies to shrink SQLite. Ops Assistant can list/open/compact via gated actions.",
        "good": "Sessions visible; compacted rows show cortex_digest_ref; raw/dirty count stays low",
        "bad": "Confusing Ops Assistant with customer chat history; leaving raw forever (disk grows)",
        "tab": "/admin",
        "action": "Ask Ops Assistant to list or compact, or Admin → Client AI chats",
    },
    "chat_compact": {
        "means": "Digest one session summary into PrismCortex, then prune raw message bodies in SQLite.",
        "how": "POST /chats/sessions/{id}/compact or Assistant action chats.compact (confirm).",
        "good": "compact_status=compacted; bytes shrink; cortex_digest_ref set when PrismCortex installed",
        "bad": "Compacting before you reviewed a session you still need verbatim",
        "tab": "/admin",
        "action": "Confirm chats.compact",
    },
    "chat_compact_tenant": {
        "means": "Batch-compact raw/dirty end-user sessions for a tenant.",
        "how": "POST /chats/compact-tenant or Assistant action chats.compact_tenant.",
        "good": "raw+dirty drop after confirm",
        "bad": "Wrong tenant_id",
        "tab": "/admin",
        "action": "Confirm chats.compact_tenant",
    },
}

LOGS_PLAIN: dict[str, dict[str, str]] = {
    "ops_logs": {
        "means": "Mother ops log bus: audit, fleet, ledger, cascade, agent push — searchable + live WS.",
        "how": "Filter by source/level/node; click a line for fields. Not Docker stdout scrape.",
        "good": "You can isolate one node_id",
        "bad": "Expecting full container journals without agent logs-batch",
        "tab": "/logs",
    },
    "source_filter": {
        "means": "Where the line came from (audit/fleet/ledger/cascade/agent/system/…).",
        "how": "Use Logs tab source dropdown or node filter for multi-agent fleets.",
        "good": "agent + node_id isolates a worker",
        "bad": "Mixing mother audit noise with worker lines without filters",
        "tab": "/logs",
    },
    "level": {
        "means": "Severity: debug/info/warn/error on the ops bus.",
        "how": "Warn/error often from ledger block/flag or agent push.",
        "good": "Filter error during incidents",
        "bad": "Ignoring warn during cascade failures",
        "tab": "/logs",
    },
}

CASCADE_PLAIN: dict[str, dict[str, str]] = {
    "cascade_state": {
        "means": "Correction cascade lifecycle: idle → running → completed/failed.",
        "how": "Cascade invalidates cache tags, mark_revalidate on graph, broadcasts to fleet.",
        "good": "completed after a deliberate correction",
        "bad": "failed — check job error / ACKs",
        "tab": "/overview",
        "action": "Overview cascade viz or Cortex conflict resolve",
    },
}

PIPELINE_PLAIN: dict[str, dict[str, str]] = {
    "guard_stage": {
        "means": "Ingress decision for the stitched run (allow / flag / block).",
        "how": "From Guard on the wire — DEMO NullGuard is labeled honestly.",
        "good": "allow when expected",
        "bad": "block/flag — open Trace stage detail",
        "tab": "/trace",
    },
    "shine_stage": {
        "means": "Grounding verdict on the answer side (pass/fail style) — preload-grounded, not world-true.",
        "how": "Shine PASS ≠ truth about the world; it means grounded in preload.",
        "good": "pass with preload context",
        "bad": "fail — inspect Shine detail on Trace",
        "tab": "/trace",
    },
    "token_tax": {
        "means": "Cache hit_rate / tokens_saved / cost_saved shown on Overview Token tax.",
        "how": "Feeds Performance and Cost efficiency dimensions; demo metrics labeled DEMO.",
        "good": "Hit rate high with real traffic",
        "bad": "0 / — when no samples yet — Performance can read 0",
        "tab": "/overview",
    },
    "driver_p50": {
        "means": "PrismDriver latency p50 when ChorusGraph exposes driver stats.",
        "how": "Shows milliseconds or — when unavailable.",
        "good": "Stable p50 under load",
        "bad": "— with live graph expected — adapter may not expose driver_latency",
        "tab": "/overview",
    },
}


def _entry_block(title: str, entry: dict[str, str], live: str = "") -> str:
    lines = [
        f"**{title}**",
        f"- Means: {entry.get('means', '')}",
        f"- How: {entry.get('how', '')}",
        f"- Healthy: {entry.get('good', '')}",
        f"- Unhealthy: {entry.get('bad', '')}",
    ]
    if live:
        lines.insert(1, f"- **Live now:** {live}")
    if entry.get("tab"):
        lines.append(f"- Where: `{entry['tab']}`")
    if entry.get("action"):
        lines.append(f"- Next: {entry['action']}")
    return "\n".join(lines)


def explain_performance_zero(snap: dict[str, Any]) -> str:
    dims = (snap.get("score") or {}).get("dimensions") or {}
    perf = float(dims.get("performance") or 0)
    m = snap.get("metrics") or {}
    hit = m.get("hit_rate")
    demo = m.get("demo")
    tax = snap.get("token_tax") or {}
    return (
        f"Your **Performance is {perf:.0f}** right now.\n\n"
        f"Performance is cache effectiveness: `hit_rate × 100`. "
        f"Live hit_rate=**{hit}** (demo={demo}). "
        f"Token tax panel: tokens_saved={m.get('tokens_saved')}, "
        f"cost_saved_usd=${m.get('cost_saved_usd')}, "
        f"driver p50={((snap.get('driver') or {}).get('p50_ms')) if snap.get('driver') else tax.get('driver_p50_ms') or '—'} ms.\n\n"
        f"{PIPELINE_PLAIN['token_tax']['bad']}\n"
        f"Open **Overview → Token tax & driver**. "
        f"If hit_rate is 0 / missing samples, Performance correctly reads near **0** — "
        f"not a broken AI Score formula."
    )


def explain_taxonomy(snap: dict[str, Any], focus: str | None = None) -> str:
    tax = snap.get("taxonomy") or {}
    engine = tax.get("engine") or "unknown"
    parts = tax.get("partitions") or []
    ver_bits = ", ".join(
        f"{p.get('partition')} v{p.get('version')}" for p in parts[:5]
    ) or "none"
    health = tax.get("health") or {}
    packs = snap.get("taxonomy_packs") or tax.get("taxonomy_packs") or {}
    lines = [
        "Taxonomy in plain English (live grounding):",
        f"- Engine: **{engine}**"
        + (" (DEMO NullRAG)" if tax.get("demo") or engine == "null" else " (live retrieval)"),
        f"- taxonomy_packs.ready: **{packs.get('ready')}**"
        + (f" — {packs.get('install_hint')}" if packs.get("install_hint") and not packs.get("ready") else ""),
        f"- Partitions: {ver_bits}",
        f"- Bleed risk: **{health.get('bleed_risk', 'n/a')}**",
        f"- Categories: **{tax.get('category_count', 0)}**",
        "",
    ]
    key = focus or "engine"
    if key in TAXONOMY_PLAIN:
        live = {
            "engine": f"engine={engine}",
            "partition_version": ver_bits,
            "staleness": f"decay rows={len(health.get('decay') or [])}",
            "bleed_risk": str(health.get("bleed_risk", "n/a")),
            "taxonomy_packs": f"ready={packs.get('ready')}",
            "search_score": "use Taxonomy Search results table",
            "overwrite": "admin Edit on a search hit",
            "category_tree": f"{tax.get('category_count', 0)} categories",
        }.get(key, "")
        lines.append(_entry_block(key.replace("_", " ").title(), TAXONOMY_PLAIN[key], live))
    elif focus is None:
        for k in ("engine", "partition_version", "staleness", "taxonomy_packs"):
            lines.append(_entry_block(k.replace("_", " ").title(), TAXONOMY_PLAIN[k]))
            lines.append("")
    return "\n".join(lines)


def explain_trace(snap: dict[str, Any], focus: str | None = None) -> str:
    tr = snap.get("trace") or {}
    pipe = snap.get("pipeline") or {}
    stages = " → ".join(pipe.get("stages") or []) or "Guard → Ledger → Shine"
    live = (
        f"run_id={pipe.get('run_id') or tr.get('latest_run_id') or 'none'}; "
        f"recent_runs={tr.get('recent_count', 0)}; stages={stages}"
    )
    key = focus or "wire_stages"
    entry = TRACE_PLAIN.get(key) or TRACE_PLAIN["wire_stages"]
    return (
        f"Trace / live wire right now: {live}.\n\n"
        + _entry_block(key.replace("_", " ").title(), entry, live)
        + "\n\n"
        + _entry_block("Zero-token replay", TRACE_PLAIN["replay"])
    )


def explain_guard(snap: dict[str, Any], focus: str | None = None) -> str:
    g = snap.get("guard") or {}
    live = (
        f"ingress_profile={g.get('ingress_profile')}; shadow_profile={g.get('shadow_profile')}; "
        f"shadow_enabled={g.get('shadow_enabled')}; enforce_shadow={g.get('enforce_shadow')}; "
        f"caps_demo={g.get('caps_demo')}; lexicon_terms={g.get('lexicon_count', 0)}"
    )
    key = focus or "ingress_profile"
    entry = GUARD_PLAIN.get(key) or GUARD_PLAIN["ingress_profile"]
    extra = ""
    if key == "shadow_compare" or focus is None:
        extra = "\n\n" + _entry_block("Shadow compare", GUARD_PLAIN["shadow_compare"], live)
    return f"Guard Policy Studio live: {live}.\n\n" + _entry_block(
        key.replace("_", " ").title(), entry, live
    ) + extra


def explain_cortex(snap: dict[str, Any], focus: str | None = None) -> str:
    c = snap.get("cortex") or {}
    live = (
        f"engine={c.get('engine')}; chunks={c.get('chunk_count')}; facts={c.get('fact_count')}; "
        f"conflicts={c.get('conflict_count')}; activity={c.get('activity_count')}; "
        f"last_digest={c.get('last_digest') or 'n/a'}; last_sleep_consolidated={c.get('last_sleep_consolidated')}"
    )
    key = focus or "engine"
    entry = CORTEX_PLAIN.get(key) or CORTEX_PLAIN["engine"]
    return f"Cortex live: {live}.\n\n" + _entry_block(key.replace("_", " ").title(), entry, live)


def explain_client_chats(snap: dict[str, Any], focus: str | None = None) -> str:
    """Teach Admin Client AI chats (end-user) — distinct from this Ops Assistant."""
    ch = snap.get("chats") or {}
    sessions = ch.get("sessions") or []
    live = (
        f"sessions={ch.get('count', 0)}; raw={ch.get('raw', 0)}; dirty={ch.get('dirty', 0)}; "
        f"compacted={ch.get('compacted', 0)}; tenant_hint={ch.get('tenant_hint') or snap.get('tenant_hint') or 'default'}"
    )
    lines = [
        f"Client AI chats live: {live}.",
        "",
        _entry_block("Client AI chats", DOCTOR_PLAIN["client_ai_chats"], live),
    ]
    if focus in ("chat_compact", "compact"):
        lines.append("")
        lines.append(_entry_block("Compact one session", DOCTOR_PLAIN["chat_compact"], live))
    if focus in ("chat_compact_tenant", "compact_tenant", "batch"):
        lines.append("")
        lines.append(_entry_block("Compact tenant", DOCTOR_PLAIN["chat_compact_tenant"], live))

    lines.append("")
    lines.append("**What to do**")
    lines.append(
        "1. Open Admin → Client AI chats (or ask me to **list client chats**). "
        "2. Open a session to read turns. "
        "3. **Compact** when you no longer need full verbatim text — PrismCortex keeps a dense summary; SQLite bodies prune. "
        "4. New turns after compact mark the session **dirty** until you compact again."
    )
    lines.append("")
    lines.append(
        "**Not this chat:** Ops Assistant is for mother ops literacy + gated actions. "
        "Client AI chats are end-user conversations ingested from apps/agents."
    )
    if sessions:
        lines.append("")
        lines.append("Recent sessions:")
        for s in sessions[:8]:
            lines.append(
                f"- `{s.get('session_id')}` · {s.get('title') or 'untitled'} · "
                f"tenant={s.get('tenant_id')} · msgs={s.get('message_count')} · "
                f"**{s.get('compact_status')}**"
            )
    else:
        lines.append("")
        lines.append(
            "No sessions yet. Agents POST `/api/v1/fleet/chat-batch` or operators "
            "`POST /api/v1/chats/ingest` — then they appear here."
        )
    raw_n = int(ch.get("raw") or 0) + int(ch.get("dirty") or 0)
    if raw_n:
        lines.append("")
        lines.append(
            f"**{raw_n}** session(s) are raw/dirty — confirm **chats.compact_tenant** to shrink storage via PrismCortex."
        )
    return "\n".join(lines)


def explain_doctor(snap: dict[str, Any], focus: str | None = None) -> str:
    d = snap.get("doctor") or {}
    pins = d.get("pins") or {}
    packages = pins.get("packages") or pins.get("checks") or {}
    # normalize pin summary
    core_missing = list(pins.get("missing_core") or [])
    optional_missing = []
    pin_rows = pins.get("pins") or pins.get("results") or []
    if isinstance(packages, dict):
        for name, info in packages.items():
            if not isinstance(info, dict):
                continue
            ok = info.get("ok", info.get("installed"))
            tier = info.get("tier") or "core"
            if ok is False or info.get("status") == "missing":
                (optional_missing if tier == "optional" else core_missing).append(name)
    if isinstance(pin_rows, list):
        for row in pin_rows:
            if row.get("ok"):
                continue
            tier = row.get("tier") or "core"
            name = row.get("package") or row.get("name") or "?"
            if tier == "optional":
                optional_missing.append(name)
            elif name not in core_missing:
                core_missing.append(name)

    packs = d.get("taxonomy_packs") or snap.get("taxonomy_packs") or {}
    live = (
        f"license={((d.get('license') or snap.get('license') or {}).get('state'))}; "
        f"fleet_nodes={d.get('fleet_nodes', snap.get('fleet', {}).get('total'))}; "
        f"taxonomy_packs.ready={packs.get('ready')}; "
        f"install_hint={d.get('install_hint') or packs.get('install_hint') or 'n/a'}; "
        f"core_missing={core_missing or 'none'}; optional_missing={optional_missing or 'none'}"
    )
    if focus in ("core_vs_optional", "pin_floors", "pins", "pin floor", "pin floors"):
        return (
            f"Pin floors live: {live}.\n\n"
            + _entry_block("Pin floors", DOCTOR_PLAIN["pin_floors"], live)
            + "\n\n"
            + _entry_block("Core vs optional", DOCTOR_PLAIN["core_vs_optional"], live)
            + "\n\n"
            "**Missing optional** (fabric/mesh/lang) is OK if you do not use those extras. "
            "**Missing core** (graph/guard/rag/shine/cortex) blocks live Taxonomy/Guard paths."
        )
    if focus in ("taxonomy_packs", "taxonomy packs", "packs ready"):
        packs = d.get("taxonomy_packs") or snap.get("taxonomy_packs") or {}
        return _entry_block(
            "taxonomy_packs.ready",
            TAXONOMY_PLAIN["taxonomy_packs"],
            f"ready={packs.get('ready')}; hint={packs.get('install_hint') or d.get('install_hint')}",
        )
    if focus in (
        "client_ai_chats",
        "client chats",
        "client chat",
        "end user chats",
        "end-user chats",
        "chat_compact",
        "chat_compact_tenant",
        "compact",
        "compact_tenant",
        "batch",
    ):
        return explain_client_chats(snap, focus=focus)
    key = focus or "license"
    # map aliases
    alias = {
        "soc2": "soc2_export",
        "pin": "pin_floors",
        "pins": "pin_floors",
        "adapter": "adapters",
        "join": "join_token",
        "finding": "compliance",
        "client_ai_chats": "client_ai_chats",
        "client chats": "client_ai_chats",
        "client chat": "client_ai_chats",
        "end user chats": "client_ai_chats",
        "end-user chats": "client_ai_chats",
    }.get(key, key)
    entry = DOCTOR_PLAIN.get(alias) or DOCTOR_PLAIN["license"]
    return f"Admin / Doctor live: {live}.\n\n" + _entry_block(
        alias.replace("_", " ").title(), entry, live
    )


def explain_logs(snap: dict[str, Any], focus: str | None = None) -> str:
    lg = snap.get("logs") or {}
    live = (
        f"recent={lg.get('count', 0)}; sources={lg.get('sources') or []}; "
        f"levels={lg.get('levels') or []}"
    )
    key = focus or "ops_logs"
    entry = LOGS_PLAIN.get(key) or LOGS_PLAIN["ops_logs"]
    return f"Ops Logs live: {live}.\n\n" + _entry_block(
        key.replace("_", " ").title(), entry, live
    )


def explain_cascade(snap: dict[str, Any]) -> str:
    st = (snap.get("pipeline") or {}).get("cascade_state") or "idle"
    cid = (snap.get("pipeline") or {}).get("cascade_id")
    live = f"state=**{st}**" + (f"; cascade_id={cid}" if cid else "")
    return (
        f"Cascade on Overview right now: {live}.\n\n"
        + _entry_block("Cascade state", CASCADE_PLAIN["cascade_state"], live)
        + "\n\n`completed` means invalidate + mark_revalidate + broadcast finished for that run — "
        "not that every agent ACK arrived (check fleet ACKs if require_ack)."
    )


def explain_pipeline_decisions(snap: dict[str, Any]) -> str:
    pipe = snap.get("pipeline") or {}
    stage_detail = pipe.get("stage_detail") or []
    bits = []
    for s in stage_detail:
        bits.append(
            f"- {s.get('label')}: decision={s.get('decision') or '—'} status={s.get('status') or '—'}"
        )
    body = "\n".join(bits) or "- no stage detail yet (seed a trace)"
    return (
        f"Live wire stages:\n{body}\n\n"
        + _entry_block("Guard stage", PIPELINE_PLAIN["guard_stage"])
        + "\n\n"
        + _entry_block("Shine stage", PIPELINE_PLAIN["shine_stage"])
        + "\n\nShine PASS / Guard ALLOW are **not** world-truth."
    )
