"""End-user (client) AI chat sessions — index in SQLite, compact via PrismCortex.

Not the Ops Assistant drawer. Agents/apps ingest end-user turns; Admin browses
sessions; compact digests a session summary into PrismCortex and prunes raw
message bodies to shrink storage.
"""

from __future__ import annotations

import json
import time
import uuid
from typing import Any


def _now() -> float:
    return time.time()


def _summarize_turns(messages: list[dict[str, Any]], *, max_chars: int = 1800) -> str:
    lines: list[str] = []
    for m in messages:
        role = (m.get("role") or "user").strip().lower()
        content = (m.get("content") or "").strip().replace("\n", " ")
        if not content:
            continue
        prefix = "User" if role in ("user", "human", "client") else ("Assistant" if role in ("assistant", "bot", "ai") else role.title())
        lines.append(f"{prefix}: {content[:400]}")
    blob = " | ".join(lines)
    if len(blob) > max_chars:
        return blob[: max_chars - 3] + "..."
    return blob or "(empty session)"


async def ingest_messages(
    store,
    *,
    session_id: str | None,
    tenant_id: str,
    messages: list[dict[str, Any]],
    node_id: str | None = None,
    user_ref: str | None = None,
    channel: str = "end_user",
    title: str | None = None,
    meta: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Append end-user chat turns; create session row if needed."""
    if not messages:
        return {"accepted": 0, "session_id": session_id, "note": "no messages"}
    sid = (session_id or "").strip() or str(uuid.uuid4())
    tid = (tenant_id or "default").strip() or "default"
    now = _now()
    existing = await store.fetchone(
        "SELECT * FROM client_chat_sessions WHERE session_id=?", (sid,)
    )
    accepted = 0
    first_user = None
    for raw in messages[:200]:
        if not isinstance(raw, dict):
            continue
        content = str(raw.get("content") or raw.get("text") or "").strip()
        if not content:
            continue
        role = str(raw.get("role") or "user").strip().lower()[:32]
        mid = str(raw.get("message_id") or raw.get("id") or uuid.uuid4())
        ts = float(raw.get("ts") or now)
        if first_user is None and role in ("user", "human", "client"):
            first_user = content[:120]
        try:
            await store.execute(
                "INSERT INTO client_chat_messages(message_id, session_id, role, content, ts, pruned, meta_json) "
                "VALUES(?,?,?,?,?,?,?)",
                (
                    mid,
                    sid,
                    role,
                    content[:8000],
                    ts,
                    0,
                    json.dumps(raw.get("meta") or {}, default=str),
                ),
            )
            accepted += 1
        except Exception:  # noqa: BLE001
            # duplicate message_id — skip
            continue

    if accepted == 0 and existing:
        return {"accepted": 0, "session_id": sid, "duplicate": True}

    count_row = await store.fetchone(
        "SELECT COUNT(*) AS c FROM client_chat_messages WHERE session_id=? AND pruned=0",
        (sid,),
    )
    msg_count = int((count_row or {}).get("c") or 0)
    session_title = title or (existing or {}).get("title") or first_user or f"Session {sid[:8]}"
    meta_json = json.dumps({**(json.loads((existing or {}).get("meta_json") or "{}") if existing else {}), **(meta or {})}, default=str)

    if existing:
        await store.execute(
            "UPDATE client_chat_sessions SET tenant_id=?, node_id=COALESCE(?, node_id), "
            "user_ref=COALESCE(?, user_ref), title=?, message_count=?, last_at=?, "
            "compact_status=CASE WHEN compact_status='compacted' THEN 'dirty' ELSE compact_status END, "
            "meta_json=? WHERE session_id=?",
            (
                tid,
                node_id,
                user_ref,
                session_title[:200],
                msg_count,
                now,
                meta_json,
                sid,
            ),
        )
    else:
        await store.execute(
            "INSERT INTO client_chat_sessions(session_id, tenant_id, node_id, user_ref, channel, title, "
            "message_count, started_at, last_at, compact_status, summary, cortex_digest_ref, meta_json) "
            "VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                sid,
                tid,
                node_id,
                user_ref,
                (channel or "end_user")[:64],
                session_title[:200],
                msg_count,
                now,
                now,
                "raw",
                None,
                None,
                meta_json,
            ),
        )
    return {
        "accepted": accepted,
        "session_id": sid,
        "message_count": msg_count,
        "tenant_id": tid,
    }


async def list_sessions(
    store,
    *,
    tenant_id: str | None = None,
    limit: int = 50,
    compact_status: str | None = None,
) -> list[dict[str, Any]]:
    clauses: list[str] = []
    params: list[Any] = []
    if tenant_id:
        clauses.append("tenant_id=?")
        params.append(tenant_id)
    if compact_status:
        clauses.append("compact_status=?")
        params.append(compact_status)
    where = (" WHERE " + " AND ".join(clauses)) if clauses else ""
    lim = max(1, min(int(limit or 50), 200))
    rows = await store.fetchall(
        f"SELECT * FROM client_chat_sessions{where} ORDER BY last_at DESC LIMIT ?",
        tuple(params + [lim]),
    )
    out = []
    for r in rows:
        meta = {}
        try:
            meta = json.loads(r.get("meta_json") or "{}")
        except Exception:  # noqa: BLE001
            meta = {}
        out.append(
            {
                "session_id": r["session_id"],
                "tenant_id": r["tenant_id"],
                "node_id": r.get("node_id"),
                "user_ref": r.get("user_ref"),
                "channel": r.get("channel"),
                "title": r.get("title"),
                "message_count": r.get("message_count") or 0,
                "started_at": r.get("started_at"),
                "last_at": r.get("last_at"),
                "compact_status": r.get("compact_status"),
                "summary": r.get("summary"),
                "cortex_digest_ref": r.get("cortex_digest_ref"),
                "meta": meta,
            }
        )
    return out


async def get_session(store, session_id: str, *, include_pruned: bool = False) -> dict[str, Any] | None:
    row = await store.fetchone(
        "SELECT * FROM client_chat_sessions WHERE session_id=?", (session_id,)
    )
    if not row:
        return None
    if include_pruned:
        msgs = await store.fetchall(
            "SELECT * FROM client_chat_messages WHERE session_id=? ORDER BY ts ASC",
            (session_id,),
        )
    else:
        msgs = await store.fetchall(
            "SELECT * FROM client_chat_messages WHERE session_id=? AND pruned=0 ORDER BY ts ASC",
            (session_id,),
        )
    messages = []
    for m in msgs:
        messages.append(
            {
                "message_id": m["message_id"],
                "role": m["role"],
                "content": m["content"] if not m.get("pruned") else "[pruned — see Cortex summary]",
                "ts": m["ts"],
                "pruned": bool(m.get("pruned")),
            }
        )
    meta = {}
    try:
        meta = json.loads(row.get("meta_json") or "{}")
    except Exception:  # noqa: BLE001
        meta = {}
    return {
        "session_id": row["session_id"],
        "tenant_id": row["tenant_id"],
        "node_id": row.get("node_id"),
        "user_ref": row.get("user_ref"),
        "channel": row.get("channel"),
        "title": row.get("title"),
        "message_count": row.get("message_count") or 0,
        "started_at": row.get("started_at"),
        "last_at": row.get("last_at"),
        "compact_status": row.get("compact_status"),
        "summary": row.get("summary"),
        "cortex_digest_ref": row.get("cortex_digest_ref"),
        "meta": meta,
        "messages": messages,
    }


async def compact_session(store, session_id: str, *, prune: bool = True) -> dict[str, Any]:
    """Digest session into PrismCortex (compact memory) and optionally prune raw bodies."""
    from choruscontrol.services.cortex_ops import digest, prismcortex_available

    detail = await get_session(store, session_id, include_pruned=False)
    if not detail:
        raise KeyError("session not found")
    # Prefer unpruned content; if empty, fall back to existing summary
    msgs = [m for m in detail["messages"] if not m.get("pruned")]
    if not msgs and detail.get("summary"):
        summary = detail["summary"]
    else:
        # Load full content even if we need include_pruned=False already has content
        raw_rows = await store.fetchall(
            "SELECT role, content, ts FROM client_chat_messages WHERE session_id=? AND pruned=0 ORDER BY ts ASC",
            (session_id,),
        )
        summary = _summarize_turns(
            [{"role": r["role"], "content": r["content"]} for r in raw_rows]
        )

    digest_text = (
        f"End-user chat session {session_id} for tenant {detail['tenant_id']}. "
        f"User ref {detail.get('user_ref') or 'anonymous'}. "
        f"Title: {detail.get('title') or 'n/a'}. "
        f"Transcript compact: {summary}"
    )
    cortex_out: dict[str, Any] | None = None
    digest_ref = f"chat-session:{session_id}"
    if prismcortex_available():
        try:
            cortex_out = digest(
                detail["tenant_id"],
                digest_text,
                agent_id=f"chat-compact:{detail.get('node_id') or 'mother'}",
            )
            digest_ref = f"chat-session:{session_id}:v{cortex_out.get('version') or '1'}"
        except Exception as exc:  # noqa: BLE001
            cortex_out = {
                "ok": False,
                "outcome": "error",
                "reason": str(exc),
                "demo": True,
            }
    else:
        cortex_out = {
            "ok": False,
            "outcome": "skipped",
            "reason": "prismcortex not installed — summary stored in SQLite only",
            "demo": True,
        }

    bytes_before = 0
    rows = await store.fetchall(
        "SELECT content FROM client_chat_messages WHERE session_id=? AND pruned=0",
        (session_id,),
    )
    for r in rows:
        bytes_before += len((r.get("content") or "").encode("utf-8"))

    pruned_count = 0
    if prune and rows:
        await store.execute(
            "UPDATE client_chat_messages SET content='[pruned]', pruned=1 WHERE session_id=? AND pruned=0",
            (session_id,),
        )
        pruned_count = len(rows)

    await store.execute(
        "UPDATE client_chat_sessions SET compact_status=?, summary=?, cortex_digest_ref=?, last_at=? "
        "WHERE session_id=?",
        ("compacted", summary[:4000], digest_ref, _now(), session_id),
    )
    return {
        "session_id": session_id,
        "compact_status": "compacted",
        "summary": summary[:500],
        "cortex_digest_ref": digest_ref,
        "cortex": cortex_out,
        "pruned_messages": pruned_count,
        "bytes_before": bytes_before,
        "bytes_after_estimate": len(summary.encode("utf-8")),
    }


async def compact_tenant(store, tenant_id: str, *, limit: int = 20) -> dict[str, Any]:
    rows = await store.fetchall(
        "SELECT session_id FROM client_chat_sessions WHERE tenant_id=? AND compact_status IN ('raw','dirty') "
        "ORDER BY last_at ASC LIMIT ?",
        (tenant_id, max(1, min(int(limit or 20), 100))),
    )
    results = []
    for r in rows:
        try:
            results.append(await compact_session(store, r["session_id"], prune=True))
        except Exception as exc:  # noqa: BLE001
            results.append({"session_id": r["session_id"], "error": str(exc)})
    return {"tenant_id": tenant_id, "compacted": len([x for x in results if not x.get("error")]), "results": results}
