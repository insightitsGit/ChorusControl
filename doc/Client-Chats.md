# Client AI chat history (Admin) — requirements

End-user / client AI conversations — **not** the Ops Assistant rail.

**Canonical design:** [ChorusControl-COMPLETE-DESIGN.md](./ChorusControl-COMPLETE-DESIGN.md) §3.7.4a · Ops literacy/execute: [Ops-Assistant.md](./Ops-Assistant.md).

## Requirements

1. **Separate from Ops Assistant** — store and show chats that end users have with customer apps/agents; never mix mother Ops Assistant turns into this history.
2. **Session grouping** — every turn belongs to a `session_id`; Admin lists sessions (tenant, user_ref, node, status, message count).
3. **Ingest paths** — operators `POST /api/v1/chats/ingest`; fleet agents `POST /api/v1/fleet/chat-batch` (node session auth).
4. **Browse** — `GET /chats/sessions`, `GET /chats/sessions/{id}`; Admin UI section **Client AI chats**.
5. **Compact for size** — digest a session summary into **PrismCortex**; prune raw SQLite bodies; keep session index + summary + `cortex_digest_ref`.
6. **Batch compact** — `POST /chats/compact-tenant` for raw/dirty sessions.
7. **Honest without PrismCortex** — still summarize + prune in SQLite; cortex outcome labeled skip/demo.
8. **Ops Assistant aware** — teach meanings (raw/dirty/compacted, what Compact does) from live snapshot counts; gated execute `chats.list|get|compact|compact_tenant` after Confirm (audit).
9. **Zero hot-path tax** — ingest/compact are control-plane only; never on agent invoke path.
10. **RBAC + audit** — viewer list/get; operator ingest/compact; mutations grace-blocked; audit actions `chats.*` / `assistant.execute`.

## Model

| Layer | Role |
|-------|------|
| SQLite `client_chat_sessions` | Session index (tenant, node, user_ref, compact_status, summary, cortex digest ref) |
| SQLite `client_chat_messages` | Bounded raw turns until compacted (`pruned=1` after compact) |
| PrismCortex | Compact memory via `digest()` of a session summary — smaller long-term footprint |

## Flow

1. App or agent pushes turns → ingest / chat-batch.
2. Admin → **Client AI chats** (or Ops Assistant list action).
3. **Open** shows transcript (or pruned placeholders).
4. **Compact** summarizes → PrismCortex when installed → `compact_status=compacted` → bodies `[pruned]`.
5. New turns after compact → status `dirty` until compacted again.

## Status values

- `raw` — full messages on disk  
- `dirty` — compacted earlier, new turns arrived  
- `compacted` — summary + cortex ref; bodies pruned  

## Ops Assistant

Ask on Admin (or any tab):

- “What are Client AI chats on Admin?” — live raw/dirty/compacted counts + what to do
- “List client chats” / “Compact raw client chat sessions” — gated actions after Confirm

## Implementation anchors

| Piece | Path |
|-------|------|
| Schema | `choruscontrol/persistence/__init__.py` |
| Service | `choruscontrol/services/client_chats.py` |
| API | `choruscontrol/api/routes.py` (`/chats/*`, `/fleet/chat-batch`) |
| Admin UI | `choruscontrol/ui/static/app.js` → `renderAdmin` |
| Assistant | `assistant.py` / `assistant_glossary.py` (`explain_client_chats`, execute `chats.*`) |
| Tests | `tests/test_client_chats.py`, `tests/test_assistant_client_chats.py` |
