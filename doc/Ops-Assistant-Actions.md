# Ops Assistant — actionable catalog (agent KB)

**Code source of truth:** `choruscontrol/services/assistant_actions.py` → `ACTION_CATALOG`, `match_actions()`, `format_actions_kb()`.

## How agents / Ops Assistant use this

1. User asks a **run prompt** (table below).
2. `POST /api/v1/assistant/ask` returns `actions[]` with `{type, label, params, requires_confirmation}`.
3. UI shows Confirm → second ask with `confirm=true` + `execute`.
4. Mother runs the **same service** as the tab button; audits `assistant.execute`.

Ask **“What can you do on {tab}?”** for a short teach list (`actions_for_tab_teach`).

Feature gate: `assistant.ops` (demo may label). Mutations respect license grace + enterprise policy domains.

---

## Overview

| Action `type` | Example prompts | Mutating |
|---------------|-----------------|----------|
| `cascade` | Run correction cascade · Trigger cascade · Start cascade | yes |
| `incident.create` | Open an incident · Create incident | yes |
| `graph.blast_radius` | Blast radius · Show blast radius | no |
| `compliance.scan` | Run compliance scan · Scan compliance | yes |

## Trace

| Action `type` | Example prompts | Mutating |
|---------------|-----------------|----------|
| `traces.seed` | Seed demo trace · Seed a trace | yes |
| `traces.replay` | Replay the trace · Replay run · Zero-token replay | no |

## Taxonomy

| Action `type` | Example prompts | Mutating |
|---------------|-----------------|----------|
| `taxonomy.reindex` | Reindex taxonomy · Run reindex · Rebuild indexes | yes |
| `taxonomy.warm_partition` | Warm partition · Warm taxonomy · Warm kb | yes |
| `taxonomy.search` | Search taxonomy · Search kb for … | no |

## Cortex

| Action `type` | Example prompts | Mutating |
|---------------|-----------------|----------|
| `cortex.digest` | Run cortex digest · Digest into cortex | yes |
| `cortex.recall` | Run cortex recall · Recall from cortex | no |
| `cortex.explain` | Cortex explain · Run cortex explain | no |
| `cortex.sleep` | Run cortex sleep · Consolidate memory | yes |
| `cortex.conflict_resolve` | Resolve cortex conflict · Keep new cortex | yes |

## Guard

| Action `type` | Example prompts | Mutating |
|---------------|-----------------|----------|
| `guard.shadow_compare` | Run shadow compare · Guard shadow compare | no |
| `guard.policy.put` | Save guard policy · Update guard policy | yes |

## Logs

| Action `type` | Example prompts | Mutating |
|---------------|-----------------|----------|
| `logs.search` | Search ops logs · Show fleet logs · Filter logs | no |

## Admin

| Action `type` | Example prompts | Mutating |
|---------------|-----------------|----------|
| `fleet.join_token` | Create join token · Issue join token | yes |
| `compliance.scan` | Run compliance scan | yes |
| `admin.license_online_check` | License online check · Side 1 online check | no |
| `admin.doctor` | Run doctor · Doctor snapshot | no |
| `chats.list` | List client chats · Show client chats | no |
| `chats.get` | Open chat session · Show session sess-… | no |
| `chats.compact` | Compact this session · Compact client session | yes |
| `chats.compact_tenant` | Compact raw client chat sessions · Compact all client chats | yes |

---

## Execute payload shape

```json
{
  "question": "Execute confirmed action",
  "confirm": true,
  "execute": {
    "type": "taxonomy.reindex",
    "params": { "tenant_id": "default" }
  }
}
```

## Not via Assistant (UI-only / sensitive)

- Paste/install license JWT (Admin textarea — avoid putting secrets in chat).
- SOC2 zip browser download (use Admin → SOC2 export).
- Fleet agent join itself (needs join token + agent process).

## Design cross-refs

- COMPLETE-DESIGN §11.6 · §3.7.4a
- [Ops-Assistant.md](./Ops-Assistant.md)
- [Client-Chats.md](./Client-Chats.md)
