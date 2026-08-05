# ChorusControl

[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![License: Apache-2.0](https://img.shields.io/badge/License-Apache_2.0-green.svg)](LICENSE)
[![Version](https://img.shields.io/badge/version-0.1.4-informational)](https://github.com/insightitsGit/ChorusControl)
[![CI](https://img.shields.io/badge/tests-51%20passing-brightgreen)](https://github.com/insightitsGit/ChorusControl)

**AI Operations Platform for the Prism / Chorus stack — mother control plane + lightweight fleet agents.**  
Govern, observe, and correct production AI fleets without putting Side 1 (billing) or phone-home inside the customer VPC.

```bash
# After v0.1.4 is on PyPI:
pip install "choruscontrol[server,postgres,prism]==0.1.4"

# Until then (or for tip-of-main):
# pip install "choruscontrol[server,agent] @ git+https://github.com/insightitsGit/ChorusControl.git@main"

set CHORUSCONTROL_DEMO_MODE=1
set CHORUSCONTROL_ADMIN_TOKEN=healthcare-demo-token
choruscontrol serve --host 127.0.0.1 --port 8443
```

Open **http://127.0.0.1:8443/overview** · API auth: `Authorization: Bearer healthcare-demo-token`

> **DEMO ≠ production truth.** With `CHORUSCONTROL_DEMO_MODE=1`, missing Prism packs become **NullAdapters** and metrics/scores are labeled `demo`. Live pins report honest caps — we never fake Guard PASS, Shine PASS, or AI Score as world-true.

---

## What is ChorusControl?

ChorusControl is the **self-hosted ops layer** above ChorusGraph, PrismGuard, PrismShine, PrismCortex, PrismRAG, and related products:

| Layer | Role |
|-------|------|
| **Mother** | FastAPI AI Ops UI + control APIs (Overview, Trace, Taxonomy, Cortex, Guard, **Logs**, Admin incl. **Client AI chats**) · **Ops Assistant** (teach + gated execute) |
| **Fleet agent** | Background-only join / heartbeat / commands / optional log+ledger export — **zero hot-path latency** on invoke/digest/recall |
| **Correction cascade** | Cortex conflict → cache invalidate → Graph `mark_revalidate` → Shine consistency — one audited action |
| **License** | Offline Ed25519 verify (Side 1 JWT) + optional ~14-day online revoke check |

It is **not** an agent runtime (that’s [ChorusGraph](https://pypi.org/project/chorusgraph/)), not an injection firewall ([PrismGuard](https://pypi.org/project/prismguard/)), and not an answer verifier ([PrismShine](https://pypi.org/project/prismshine/)). It **operates** those products across a fleet.

### When NOT to use ChorusControl

- You only need a single-process agent graph → use ChorusGraph alone.  
- You only need jailbreak / WAF on ingress → use PrismGuard.  
- You only need answer grounding → use PrismShine.  
- You need Stripe / license **issuance** → that’s Side 1 ([www.insightits.com](https://www.insightits.com)), not this repo.  
- You need active-active multi-region mothers on day one → deferred; see [doc/ChorusControl-Future-Mother-HA.md](doc/ChorusControl-Future-Mother-HA.md).

---

## Why ChorusControl?

| Pain | ChorusControl answer |
|------|----------------------|
| Many Prism nodes, no single ops surface | Seven-tab mother (incl. **Logs**) + Ops Assistant that **teaches and gated-executes** every tab |
| End-user AI chat sprawl on disk | Admin **Client AI chats** + PrismCortex compact / prune |
| One mother, many ChorusGraph workers | Fleet registry + per-`node_id` ledger / ops logs (filter in Logs tab) |
| Fact correction doesn’t flush caches | **Correction cascade** (invalidate + revalidate + audit) |
| Dashboards that lie about capabilities | **Honest caps** + DEMO labels when NullAdapters are in use |
| Control plane on the request path | Agent is **background-only**; hot path stays local |
| Air-gapped customers can’t phone home | Offline license verify; online check is optional |
| “Who is serving Cortex for tenant X?” | Fleet `memory_endpoint` + `/cortex` console |

### Customer path (after pip)

1. Buy **Enterprise** (CONTROL) → paste `CHORUSCONTROL_LICENSE_KEY`.  
2. **Production:** `pip install "choruscontrol[server,postgres,prism]==0.1.4"`  
   **Demo only:** `pip install "choruscontrol[server]==0.1.4"` + `DEMO_MODE=1`  
3. `choruscontrol serve` → **mother = dashboard + API** at `/overview` (you host it; we do not).  
4. Optional: `choruscontrol-agent` on workers with a join token from Admin.

See [doc/INSTALL-MOTHER.md](doc/INSTALL-MOTHER.md) for profiles, pin tiers, and reference Docker.

### ChorusGraph Pack vs LangGraph Pack vs AWS Bedrock Pack (Race E)

ChorusControl governs the **ChorusGraph / Prism Pack**. Job-by-job proof lives here:

- **Index:** [doc/benchmarks/prism-pack/](doc/benchmarks/prism-pack/)  
- **Research note:** [ChorusGraph Pack vs LangGraph Pack vs AWS Bedrock Pack](doc/benchmarks/prism-pack/race-e/RESEARCH-NOTE-pack-vs-langgraph-vs-aws-bedrock.md)  
- **Machine report:** [`COMPARISON_REPORT.md`](doc/benchmarks/prism-pack/race-e/COMPARISON_REPORT.md) · run `general_v1_pcl2a_20260725` · seed 42  

Measured lanes = **ChorusGraph Pack (PC/PN) / LangGraph Pack (L2) / Bedrock AgentCore Pack (A1)** — not the ChorusControl UI. Site: [prism-pack.html](https://www.insightits.com/products/prism-pack.html). Soft CTA: **CONTROL** (this product) · **GRADE** / [Scorecard](https://github.com/insightitsGit/PrismGuard/blob/main/docs/scorecard.md) for PI.

---

## How enterprise licensing works

ChorusControl is **self-hosted software**. Insight IT Solutions sells the **commercial license**; you run the mother + agents in **your** VPC. Billing never lives inside the customer container.

```
  ┌─────────────────────────────┐         ┌──────────────────────────────────┐
  │  Side 1 — insightits.com    │         │  Side 2 — your VPC               │
  │  Account · Stripe · support │  JWT    │  Mother + fleet agents           │
  │  Issues signed license key  │ ──────► │  Verifies offline (Ed25519)      │
  │  Optional /validate (~14d)  │ ◄─opt─  │  Paste key in Admin → License    │
  └─────────────────────────────┘         └──────────────────────────────────┘
```

### What you buy from us

The commercial product is **ChorusControl Enterprise** only (soft CTA **CONTROL** on [insightits.com](https://www.insightits.com/products/choruscontrol.html)). There is **no Starter SKU** on the public catalog today.

1. Request access via **CONTROL** / sign in at **[www.insightits.com](https://www.insightits.com)**.  
2. Complete Enterprise purchase / access (portal when Stripe checkout is live; sales / admin issue until then).  
3. Copy or download the **license JWT** from the portal (or email delivery).  
4. Install ChorusControl in your environment (`DEMO_MODE=0`).  
5. Paste the key into **Admin → License** or set `CHORUSCONTROL_LICENSE_KEY`.  
6. Mother verifies the signature **offline** — air-gap friendly. Connected installs may optionally call Side 1 about every **14 days** only to pick up **revocation** (not required to boot).

**You do not** put Stripe keys, private signing keys, or the company website inside your ChorusControl image.

### Pricing (commercial)

| Product | List price | How to buy |
|---------|------------|------------|
| **ChorusControl Enterprise** | **$24,000 / year** | Soft CTA **CONTROL** · [pricing](https://www.insightits.com/pricing.html) · portal `/dashboard.html#choruscontrol` |

Issued Enterprise JWTs typically carry entitlements such as `max_nodes` / `max_tenants` and features `trace.replay`, `guard.shadow`, `audit.export` (exact claims come from Side 1 at issue time).

- License JWT `exp` is typically **~90 days** (or through the Stripe / contract period); renewals re-issue a new key.  
- After `exp`, Side 2 enters **14-day read-only grace** (observe OK; mutations blocked), then fail-closed.  
- Air-gap / custom SLA deals are still **Enterprise** commercially — issued by sales / Agile Super Admin as needed (JWT may use a higher entitlement profile; not a separate public “Starter” plan).  
- Quotes and discounts are commercial — portal or sales.

Portal / support: [www.insightits.com](https://www.insightits.com) · support deep-link configurable via `INSIGHTITS_SUPPORT_URL`.  
Contract detail: [doc/Side1-insightits-com-Handoff.md](doc/Side1-insightits-com-Handoff.md).

### Demo vs paid

| Mode | Who | What you get |
|------|-----|--------------|
| **`DEMO_MODE=1`** | Local eval / healthcare compose | Auto demo JWT, NullAdapters OK, labeled `demo` |
| **`DEMO_MODE=0` + company JWT** | Paying / pilot customer | Enforced tier, nodes, tenants, features; fail-closed without a valid key |

Open-source install without a key is for **evaluation with demo mode** only — production enterprise use requires a license from Insight ITS.

---

## Quick start (30 seconds)

### 1) Install

```bash
pip install "choruscontrol[server,agent]==0.1.1"

# Tip of main (pre-release / hotfix):
# pip install "choruscontrol[server,agent] @ git+https://github.com/insightitsGit/ChorusControl.git@main"

# Live Prism packs (public pins when available):
# pip install "choruscontrol[server,agent,prism]"
```

Editable clone:

```bash
git clone https://github.com/insightitsGit/ChorusControl.git
cd ChorusControl
pip install -e ".[server,agent,dev]"
```

### 2) Run mother (demo)

```bash
# Windows
set CHORUSCONTROL_DEMO_MODE=1
set CHORUSCONTROL_ADMIN_TOKEN=healthcare-demo-token
choruscontrol serve --host 127.0.0.1 --port 8443

# Linux / macOS
export CHORUSCONTROL_DEMO_MODE=1
export CHORUSCONTROL_ADMIN_TOKEN=healthcare-demo-token
choruscontrol serve --host 127.0.0.1 --port 8443
```

```bash
choruscontrol doctor --mode mother
```

### 3) Healthcare full-stack demo (recommended)

```bash
docker compose -f docker-compose.healthcare.yml up --build
```

Aurora Health scenario: mother + Postgres audit + clinical / pharmacy / edge agents + seeded traces/cascade.  
UI: http://127.0.0.1:8443/overview · Bearer `healthcare-demo-token`  
Details: [doc/Healthcare-Demo.md](doc/Healthcare-Demo.md).

### 4) Lightweight fleet agent

```bash
pip install "choruscontrol[agent] @ git+https://github.com/insightitsGit/ChorusControl.git@main"

set CHORUSCONTROL_MOTHER_URL=http://127.0.0.1:8443
set CHORUSCONTROL_JOIN_TOKEN=<from Admin → join token>
set CHORUSCONTROL_NODE_ID=worker-1
set CHORUSCONTROL_NODE_ROLE=GREEN
choruscontrol-agent
```

Or from app code (background only — never await on the hot path):

```python
from choruscontrol.agent import attach_agent

# Schedules join/heartbeat/commands off the request path
attach_agent()
```

---

## Features

| Feature | Description |
|---------|-------------|
| **Overview** | Fleet topology, health matrix, transparent AI Score, live pipeline viz, **Ops logs** live strip |
| **Trace** | Guard → Ledger → Shine wire; multi-node Route Ledger; zero-token replay |
| **Taxonomy** | Partition warm / reindex jobs; PrismRAG when pinned |
| **Cortex** | PrismCortex activity, chunks, digest / recall / sleep / conflict resolve |
| **Guard studio** | Ingress profiles, shadow compare (feature-gated) |
| **Logs** | Searchable ops log bus (audit, fleet, ledger, cascade, agent push) + realtime `WS /api/v1/logs/live` |
| **Admin** | License, doctor, tenants, stack licenses, SOC2 export, compliance scan, **Client AI chats** (end-user sessions + PrismCortex compact) |
| **Ops Assistant** | Teach every tab value in plain English; **gated execute** for the same actions as tab buttons (reindex, cascade, cortex sleep, compact chats, join token, …) — [doc/Ops-Assistant.md](doc/Ops-Assistant.md) · prompt map [doc/Ops-Assistant-Actions.md](doc/Ops-Assistant-Actions.md) |
| **Cascade** | Conflict resolve → invalidate → `mark_revalidate` → fleet ACKs |
| **Multi-agent fleet** | One mother · many agents (`max_nodes`); filter Logs / Trace by `node_id`; optional `fleet/chat-batch` + `logs-batch` |
| **License** | Offline Ed25519 + 14-day grace; optional Side 1 `/validate` |
| **Exec / Eng modes** | Overview lenses for business vs engineering |

### Client AI chats (Admin)

End-user / app conversations (not Ops Assistant history): sessions in SQLite → **Compact** digests into PrismCortex and prunes raw bodies. Agents push via `POST /api/v1/fleet/chat-batch`; operators via `/api/v1/chats/ingest`. Design: [doc/Client-Chats.md](doc/Client-Chats.md) · COMPLETE-DESIGN §3.7.4a.

### Ops Assistant actionable catalog

Ask **“What can you do on taxonomy?”** (or any tab). Run prompts (e.g. “Reindex taxonomy”, “Create join token”, “Compact raw client chat sessions”) propose Confirm buttons that call the same mother APIs as the UI. Agent KB: [doc/Ops-Assistant-Actions.md](doc/Ops-Assistant-Actions.md).

### Ops Logs (mother)

Mother ships a unified **ops log bus** (SQLite-backed) for platform events — not a replacement for container stdout scrapers, and **not** ChorusFabric (Fabric remains optional mesh; the dashboard uses HTTP WebSockets).

| Surface | Path |
|---------|------|
| Logs tab | `/logs` — search by query / source / level / tenant / **node** |
| Overview section | Live tail + link to Logs tab |
| REST search | `GET /api/v1/logs` |
| Realtime | `WS /api/v1/logs/live?token=…` (viewer+) |
| Agent push (optional) | `POST /api/v1/fleet/logs-batch` (session auth, same pattern as ledger-batch) |

Captured sources include mother **audit**, **fleet** join/heartbeat/ack, **ledger** batches, **cascade**, and boot **system** lines. Multi-worker ChorusGraph **execution** truth still flows primarily through **Trace** via async `LEDGER_BATCH` (`/api/v1/fleet/ledger-batch`) per §3.19.6b.

> **Install note:** `0.1.4` includes HO-010 fixes (Assistant Confirm encoding, grace read executes, taxonomy slug, Memory→Cortex docs) on top of Client chats + Ops Assistant catalog from `0.1.3`.

---

## Architecture

```
                    Customer VPC (Side 2)
┌──────────────────────────────────────────────────────────┐
│  Mother  :8443                                           │
│  UI tabs (… Logs … Admin Client chats …) · /api/v1 · jobs · cascade · audit · ops_logs · client_chats · SQLite/PG │
└─────────────┬────────────────────────────────────────────┘
              │ HTTP join / heartbeat / commands / ledger-batch / logs-batch / chat-batch (primary)
              │ Fabric optional (invalidation mesh — not browser Logs WS)
     ┌────────┼────────┬────────────┐
     ▼        ▼        ▼            ▼
  GREEN     BLUE    ORANGE      MEMORY/CORTEX
  worker    worker   edge         memory_endpoint
     │        │        │            │
     └────────┴────────┴────────────┘
        Prism packs local (Guard / Graph / Shine / RAG / Cortex)
        Agent = background only — no mother RTT on invoke
        Each node may export ledger (+ optional ops lines) tagged with node_id
```

License **issuance** stays on Side 1. Mother verifies offline (and may optionally re-check revoke status ~every 14 days).

---

## Install & extras

| Extra | Purpose |
|-------|---------|
| *(none)* | Core libs |
| `[server]` | Mother UI/API (FastAPI, Jinja, SQLite) |
| `[agent]` | Fleet agent CLI |
| `[postgres]` | Audit / control-plane dual-write (`asyncpg`) |
| `[prism]` | Live pins: ChorusGraph, Guard, Shine, RAG, Cortex |
| `[fabric]` | Optional CHORUS Fabric transport |
| `[all]` | server + agent + postgres + prism |
| `[dev]` | pytest, ruff |

Packaging detail: [doc/PACKAGING.md](doc/PACKAGING.md).

---

## Production checklist

1. **`CHORUSCONTROL_DEMO_MODE=0`** — never ship demo NullAdapters unlabeled.  
2. **Strong `CHORUSCONTROL_ADMIN_TOKEN`** (≥16 chars; `serve` refuses weak defaults).  
3. **Side 1 JWT** in `CHORUSCONTROL_LICENSE_KEY`.  
4. **Trust anchor** — packaged `side1_public.hex` is the **prod ceremony public** (2026-07-27). Override with `CHORUSCONTROL_LICENSE_PUBLIC_KEY_HEX` only for key rotation.  
5. Optional: `DATABASE_URL` for Postgres durability; `CHORUSCONTROL_LICENSE_ONLINE_CHECK=1` for revoke polling.  

Full env list: [doc/Azure-Mother-Env.md](doc/Azure-Mother-Env.md).

---

## CLI

```bash
choruscontrol serve [--host 0.0.0.0] [--port 8443]
choruscontrol doctor --mode mother|agent|auto
choruscontrol audit-verify audit.jsonl --pubkey audit_public_key.pem
choruscontrol-agent
choruscontrol-keygen   # local/dev issuance helpers only — production keys are Side 1
```

---

## Design decisions

| Item | Choice |
|------|--------|
| Control transport | **HTTP primary**; Fabric optional |
| Mother persistence | **SQLite** default (+ WAL); Postgres via `DATABASE_URL` |
| License | Offline verify + **14-day grace**; optional online validate |
| Auth | Admin bearer **+ optional OIDC** |
| Observability | Coexists with OTel — OTel watches; ChorusControl acts |
| Live Prism | Pin floors when installed; else NullAdapters labeled DEMO |

---

## Side 1 (commercial portal)

| Concern | Where |
|---------|--------|
| Buy / renew / upgrade | [www.insightits.com](https://www.insightits.com) |
| Stripe billing | Side 1 only |
| License **issuance** (Ed25519 private key) | Side 1 only |
| License **verification** | This repo (Side 2) |
| Support tickets | Side 1 support URL |

Handoff contract: [doc/Side1-insightits-com-Handoff.md](doc/Side1-insightits-com-Handoff.md).

---

## Docs

| Doc | Contents |
|-----|----------|
| [doc/README.md](doc/README.md) | Design doc index |
| [doc/ChorusControl-COMPLETE-DESIGN.md](doc/ChorusControl-COMPLETE-DESIGN.md) | Full design authority (**v1.8.1**) |
| [doc/Ops-Assistant.md](doc/Ops-Assistant.md) | Dashboard literacy + gated execute |
| [doc/Ops-Assistant-Actions.md](doc/Ops-Assistant-Actions.md) | **Per-tab prompt → execute.type** (agent KB) |
| [doc/Client-Chats.md](doc/Client-Chats.md) | End-user chat history + PrismCortex compact |
| [doc/Healthcare-Demo.md](doc/Healthcare-Demo.md) | Aurora Health walkthrough |
| [doc/ChorusControl-Enterprise-Depth.md](doc/ChorusControl-Enterprise-Depth.md) | Phase 3–6 depth shipped |
| [doc/ChorusControl-Future-Mother-HA.md](doc/ChorusControl-Future-Mother-HA.md) | Deferred multi-region HA |
| [doc/PACKAGING.md](doc/PACKAGING.md) | Wheels, extras, containers |
| [doc/Side1-insightits-com-Handoff.md](doc/Side1-insightits-com-Handoff.md) | Commercial portal / license issuance |

---

## Tests

```bash
pytest -q
```

Includes hot-path latency (S03), restart soak, publish-blocker regressions (license trust + fleet auth).

---

## Publish (maintainers)

Full checklist: [doc/PACKAGING.md](doc/PACKAGING.md) (Trusted Publisher + tag `v0.1.1`).

```bash
git tag v0.1.1
git push origin v0.1.1
# GitHub Actions Publish: test → build → PyPI
```

---

## License

Apache-2.0 — Insight IT Solutions LLC
