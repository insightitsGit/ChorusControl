# ChorusControl — Complete Design Specification (Single Source)

| Field | Value |
|-------|-------|
| Vendor | Insight IT Solutions LLC (insightits.com) |
| Product | **ChorusControl — Enterprise AI Operating System** |
| Subtitle | AI Operations Platform for Enterprise AI |
| Document | **Complete Design — single file** |
| Version | 1.7.0 |
| Status | Design complete — implementation not started |
| Date | July 2026 |
| Relates to | *ChorusControl Architecture & Design Spec* PDF v1.0.0 |
| Repo | Side 2 main product. Side 1 = future www.insightits.com handoff |

> **This is the one file to read.** Overview, architecture, Implementation Strategy (§10), Product Vision Enhancements (§11), Side 1 handoff, shipping gaps, readiness.
>
> **Position as:** Enterprise AI Operating System / AI Operations Platform.  
> **Not:** dashboard · monitoring tool · observability-only · control-plane product.  
> **Core question:** Can I trust my organization's AI?

---

## Table of contents

1. [Part A — Design Overview](#part-a--design-overview)
2. [Part B — Normative Architecture (Gaps & Solutions)](#part-b--normative-architecture-gaps--solutions)
3. [Part C — Side 1 Handoff (www.insightits.com)](#part-c--side-1-handoff-wwwinsightitscom)
4. [Part D — Shipping Gaps (S01–S07)](#part-d--shipping-gaps-s01s07)
5. [Part E — Implementation Readiness & Ecosystem](#part-e--implementation-readiness--ecosystem)

---


# Part A — Design Overview

| Field | Value |
|-------|-------|
| Product | **ChorusControl — Enterprise AI Operating System** |
| Subtitle | AI Operations Platform for Enterprise AI |
| Portal | www.insightits.com (Side 1 — future handoff) |
| Design version | 1.7.0 |
| Status | Design complete — implementation not started |
| Date | July 2026 |

**Canonical full text:** [ChorusControl-COMPLETE-DESIGN.md](./ChorusControl-COMPLETE-DESIGN.md)

---

### Positioning

**Be:** Enterprise AI Operating System / AI Operations Platform for Enterprise AI.  
**Don’t be:** AI dashboard · monitoring tool · observability-only · “control plane” product.

**Mission:** Deploy · Observe · Govern · Secure · Evaluate · Improve · Audit · Scale AI.  
**Core question:** *Can I trust my organization's AI?*

---

### System picture

Mother (`choruscontrol[server]`) + fleet agents (`choruscontrol[agent]`) over Fabric/PrismAPI; zero hot-path latency; offline license; Side 1 issues keys later.

---

### Six pillars

Governance · Observability · Security · Operations · Intelligence · Ecosystem

### Defining capabilities (staged)

| Capability | Phase |
|------------|-------|
| Mother + agent + six tabs + cascade/caps | 1–2 |
| **Enterprise AI Asset Graph** | 3 |
| Incident / version / policy engine | 4–5 |
| **AI Score** + predictive | 5 |
| Exec + Eng experiences | 4–5 |
| **AI Operations Assistant** | 6 |

---

### Lifecycle

Develop → Deploy → Observe → Govern → Evaluate → Improve → Audit → Scale

---

### Hard rules

Mother once / agent everywhere · zero hot-path latency · **HTTP primary (Fabric optional)** · async ledger · honest caps · no fake Score/Assistant · unified platform · everything connected via Asset Graph.

---

### Success

Manage an intelligent AI organization like cloud infrastructure — observable, governed, secure, versioned, measurable, auditable, continuously improving.

---

*Insight IT Solutions LLC — ChorusControl Design Overview v1.7.0*


# Part B — Normative Architecture (Gaps & Solutions)

| Field | Value |
|-------|-------|
| Vendor | Insight IT Solutions LLC (insightits.com) |
| Product | **ChorusControl — Enterprise AI Operating System** (AI Operations Platform) |
| Technical role | Self-hosted mother + fleet agent architecture for Prism / Chorus |
| Document | Design Gaps Analysis & Resolved Architecture |
| Version | 1.7.0 |
| Status | Approved for implementation |
| Date | July 2026 |
| Relates to | *ChorusControl Architecture & Design Spec* v1.0.0 |
| Companions | [Side1-insightits-com-Handoff.md](./Side1-insightits-com-Handoff.md) · [ChorusControl-Implementation-Readiness.md](./ChorusControl-Implementation-Readiness.md) · [ChorusControl-COMPLETE-DESIGN.md](./ChorusControl-COMPLETE-DESIGN.md) · [README.md](./README.md) |

---

### 1. Purpose

This document reconciles the enterprise Architecture & Design Spec (v1.0.0) with the Cursor implementation prompt and the full Insight ITS Prism / Chorus product family. It:

1. Records every material gap between the PDF spec and the original implementation prompt.
2. Defines the **resolved design** that closes each gap.
3. Incorporates **product upgrades** grounded in shipped sibling APIs (ChorusGraph, PrismGuard, PrismShine, PrismCortex, PrismRAG, prismlib-plus, Fabric, Resonance, PrismLang, ChorusMesh).
4. Positions ChorusControl as the **Enterprise AI Operating System / AI Operations Platform** — see §1.1, §10, §11.
5. Serves as the authoritative implementation blueprint for the **main product** built in this repository.

#### 1.1 Product positioning — Enterprise AI Operating System

| Term | Use |
|------|-----|
| **ChorusControl** | Product / package name |
| **Enterprise AI Operating System** | Primary strategic positioning |
| **AI Operations Platform** | Alternate category / UI subtitle |
| **Mother + fleet agent** | Technical architecture (engineering only — not marketing) |

**Position as:**

> The Enterprise AI Operating System  
> — or —  
> The AI Operations Platform for Enterprise AI

**Do not position as:** AI Dashboard · Monitoring Tool · Observability Platform · Control Plane (those name slices, not the platform).

**Mission:** Enable organizations to manage AI with the same confidence they manage cloud infrastructure — a single platform to **Deploy · Observe · Govern · Secure · Evaluate · Improve · Audit · Scale** AI.

**Core question every feature must answer:** *Can I trust my organization's AI?* Trust dimensions: Security, Governance, Compliance, Performance, Reliability, Explainability, Cost Efficiency, Operational Health.

Customers should experience **one intelligent operational layer** above frameworks and models — not disconnected tabs or a handful of agents. Full vision, pillars, Asset Graph, Ops Assistant, and lifecycle: **§11**.

**Tagline:** *ChorusControl — the Enterprise AI Operating System for the Prism / Chorus stack.*

#### Ownership model (two sides, one product family)

| Side | Where it lives | Who builds it | What it is |
|------|----------------|---------------|------------|
| **Side 2 — Main product** | **This folder / this repo** (`ChorusControl`) | This project team / this agent | Self-hosted **AI Operations Platform** (mother + agents) in customer VPC/on-prem |
| **Side 1 — Commercial portal** | **www.insightits.com** (separate site/repo) | **Future handoff** to the insightits.com agent | Billing (Stripe), support ticketing, license *issuance* |

That split is intentional:

- Customers run **ChorusControl** offline next to their ChorusGraph workers.
- Customers buy / renew / get support on **insightits.com**.
- The only durable join between sides is the **offline license JWT** (plus deep links for support and key download). Side 2 never depends on Side 1 being online to validate a license.

**In scope here (Side 2):** FastAPI **mother** (AI Operations Platform UI + API), lightweight **fleet agent**, PrismAPI / CHORUS Fabric discovery + handshake, Asset Graph foundation, six operational pillars (§11), product inventory, correction cascade, caps, fleet topology, Guard / enterprise policy studio, unified ops data model, offline license *verification*, audit, jobs, adapters, doctor, demo. Long-term: Ops Assistant, AI Score, predictive intelligence, incident intelligence, version intelligence — staged per §10–§11.

**Out of scope here (Side 1 — future handoff):** Stripe, hosted ticketing, license *issuance*, customer portal, commercial marketplace storefront.

**Explicit non-goals:** Do not run full UI on every worker. Do not reimplement PrismRAG / Cortex / Guard / Shine. Do not put Stripe or license private keys in this repo. Do not require VectorBridge or InsightPlugIn for v1. Do not claim PASS/ALLOW means world-truth. Do not phone-home for fleet discovery. Do not ship fake AI Score / Assistant claims without Asset Graph + real telemetry. Do not market the product as “just a dashboard / monitoring tool / control plane.”

---

### 2. Gap Register

| ID | Severity | Spec source | Gap summary | Resolution |
|----|----------|-------------|-------------|------------|
| G01 | Critical | §1 Two-sided model | Side 1 vs Side 2 boundary undefined in prompt | §3.1 |
| G02 | Critical | §4 Licensing | No JWT claims model, boot middleware, or tier/node enforcement | §3.2, §3.16 |
| G03 | Critical | §3 Admin + writes | No AuthN/AuthZ / RBAC for control-plane operators | §3.3 |
| G04 | High | Gap 1 | Invalidation is publisher-only; no worker subscriber contract | §3.4 |
| G05 | High | Gap 2 | Async queue covers sleep only; taxonomy re-index omitted | §3.5, §3.13 |
| G06 | High | Gap 3 | Audit JSONL only; no Postgres stream or SOC2/HIPAA export | §3.6, §3.18 |
| G07 | High | §3 UI tabs | Six tabs named; almost no backend APIs or domain services | §3.7–§3.16 |
| G08 | Medium | §1 Container | No packaging, config, secrets, or health endpoints | §3.8 |
| G09 | Medium | Core deps | Assumed Prism APIs with no adapter layer | §3.9 |
| G10 | Medium | Engine sketches | Global sleep lock, sync audit I/O, hard-coded threshold | §3.4–§3.6 |
| G11 | Low | Tests | Tests cover 3 kernels only | §3.10 |
| G12 | High | Ecosystem | Bare invalidate misses Cortex→Cache→Graph→Shine correction loop | §3.11 |
| G13 | High | Ecosystem | Dashboard can fake “green” without Guard/Shine capability truth | §3.12 |
| G14 | High | §3 Overview | Token-tax / Driver counters not wired to real metrics APIs | §3.7.1 |
| G15 | High | §3 Guard | No profile-aware policy studio; risk of law ONNX on hub/finance | §3.7.5 |
| G16 | High | §3 Trace | Trace not defined as Guard → Ledger → Shine single wire | §3.7.2 |
| G17 | Medium | ADR-005 | Taxonomy missing warm-chunk / partition version ops | §3.13 |
| G18 | Medium | PrismLib Micro | No GREEN/BLUE/ORANGE fleet topology view | §3.14 |
| G19 | Medium | Multi-product | No stack license status for sibling offline keys | §3.16 |
| G20 | Low | DX | No doctor CLI, demo mode, or OpenAPI/ai-overview | §3.17–§3.18 |
| G21 | Critical | Multi-container | No agent / PrismAPI discovery / out-of-network handshake for fleet nodes | §3.19 |

---

### 3. Resolved Architecture

#### 3.1 Deployment Boundary (closes G01)

```
┌─────────────────────────────────────────────────────────┐
│ Side 1 — www.insightits.com                             │
│ FUTURE HANDOFF (separate agent / site — NOT this repo)  │
│  Stripe billing · support tickets · license ISSUANCE    │
└───────────────────────────┬─────────────────────────────┘
                            │ customer copies license JWT
                            │ deep links: support / account
┌───────────────────────────▼─────────────────────────────┐
│ Side 2 — ChorusControl (THIS REPO)                      │
│                                                         │
│  MOTHER (one per customer env)                          │
│  ┌─────────────┐  ┌──────────────┐  ┌────────────────┐  │
│  │ FastAPI API │  │ Admin UI     │  │ Jobs + cascade │  │
│  │ + registry  │  │ (6 tabs)     │  │ + caps/doctor  │  │
│  └──────┬──────┘  └──────────────┘  └────────────────┘  │
│         │ PrismAPI / CHORUS Fabric (control channel)    │
│  ┌──────▼────────────────────────────────────────────┐  │
│  │ AGENTS on every app/worker container              │  │
│  │ pip install "choruscontrol[agent]"                │  │
│  │ detect local Prism libs → heartbeat → execute     │  │
│  │ invalidate / sleep / policy / caps locally        │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

**Ecosystem ChorusControl orchestrates (does not reimplement):**

```
Mother ──PrismAPI/Fabric──► Agent@node ──local──► ChorusGraph / Guard / Shine /
                                                    Cortex / RAG / prismlib-plus /
                                                    PrismLang / Resonance
Mother verifies license via chorusmesh public key (no phone-home)
```

**Rules**

- This repository builds **Side 2 only** — mother + agent from one package (extras).
- **Mother** = full control plane (UI + API). Install **once** per environment.
- **Agent** = thin process/library on every container that has Prism products. Not the UI.
- ChorusControl **never** phones home to insightits.com for license or fleet discovery.
- Fleet discovery uses **customer-controlled** PrismAPI / Fabric endpoints only.
- License keys are **issued** only by Side 1; Side 2 **verifies and enforces**.
- VectorBridge and InsightPlugIn are **out of v1 scope**.

---

#### 3.2 Offline License Protocol (closes G02)

##### Boot

1. Read `CHORUSCONTROL_LICENSE_KEY` (env) or uploaded key under `/admin`.
2. Verify signature using the embedded public key from `chorusmesh.license` (adapter §3.9).
3. Parse JWT-style claims → `LicenseClaims`.
4. **Grace (R02):** expired within the configured grace window (default **14 days**) → read-only mode (GET/HEAD/OPTIONS allowed; mutations `403 LICENSE_GRACE`). Missing/invalid (past grace or bad signature) → `503 LICENSE_INVALID` except `/admin/license`, `/admin/auth`, `/healthz`, `/readyz`, and fleet agent open paths. Demo mode may serve labeled demo responses.

##### Claims model

```python
class LicenseClaims(BaseModel):
    iss: str = "insightits.com"
    sub: str  # customer / org id
    iat: int
    exp: int
    tier: Literal["starter", "enterprise", "sovereign"]
    max_nodes: int
    max_tenants: int
    features: set[str]
    # e.g. trace.replay, guard.shadow, guard.policy, audit.export,
    #      cascade.auto, fleet.topology, caps.aggregate
    license_id: str
```

##### Enforcement points

| Check | Where |
|-------|--------|
| Signature + `exp` | Boot + hourly re-check |
| `max_nodes` | Fabric peer registration / heartbeat accept |
| `max_tenants` | Tenant create API |
| `features` | Feature-gated routes |

##### Modules

```
choruscontrol/license/
  verifier.py
  middleware.py
  store.py
```

See also **§3.16 Stack License Status Console** for sibling product keys (display only).

---

#### 3.3 Identity & RBAC (closes G03)

##### Roles

| Role | Capabilities |
|------|----------------|
| `viewer` | Read all tabs, caps, metrics, topology |
| `operator` | Sleep/reindex, resolve conflicts, trigger cascade/invalidate, warm partitions |
| `security` | Guard policy studio, lexicon, shadow promote; read audit |
| `admin` | RBAC, license upload, tenant matrix, audit export, doctor secrets config |

##### Auth modes

1. **Local admin** (air-gap default): bearer `CHORUSCONTROL_ADMIN_TOKEN` or session after login.
2. **OIDC** (optional): roles from `chorus_roles` claim.

All successful **mutating** requests call `AuditLogger.log_action(...)`.

```
choruscontrol/auth/
  models.py, rbac.py, deps.py, local.py, oidc.py
```

---

#### 3.4 Cross-Fleet Invalidation Bus (closes G04, G10)

Aligns with prismlib / prismlib-plus ≥0.8.0: `invalidate_tags()` and `invalidate_where(probe, threshold=…)`.

##### Publisher

```
InvalidationBroadcaster.broadcast_invalidation(
  tags: list[str],
  probe_vector: list[float] | None,
  mode: Literal["tags", "where"] = "tags",
  threshold: float | None = None,   # config default 0.55
  correlation_id: str,
  cascade_id: str | None = None,    # set when part of §3.11
)
```

```json
{
  "event": "INVALIDATE_CACHE",
  "v": 1,
  "correlation_id": "uuid",
  "cascade_id": "uuid-or-null",
  "tags": ["tenant:acme", "person_a"],
  "probe_vector": [0.1, 0.2],
  "threshold": 0.55,
  "mode": "tags",
  "issued_at": 1720000000.0
}
```

##### Subscriber contract (workers)

1. Subscribe to Fabric `INVALIDATE_CACHE`.
2. `mode=tags` → `cache.invalidate_tags(tags)`; `mode=where` → `cache.invalidate_where(probe, threshold)`.
3. Optionally also call ChorusGraph `mark_revalidate(...)` when payload includes `force_refresh: true` (cascade always sets this).
4. Optional `INVALIDATE_ACK` `{correlation_id, node_id, status, evicted_count?}`.

##### Config

```yaml
invalidation:
  default_threshold: 0.55
  require_ack: false
  ack_timeout_ms: 2000
```

```
choruscontrol/engine/invalidation.py
choruscontrol/engine/invalidation_schema.py
```

Invalidation is also driven automatically by **§3.11 Correction Cascade**.

---

#### 3.5 Maintenance Job Queue (closes G05, G10)

##### Job types

| `job_type` | Handler | Notes |
|------------|---------|-------|
| `cortex.sleep` | PrismCortex / PrismResonance passes 1–4 | Thread executor |
| `taxonomy.reindex` | PrismRAG hot-path re-index | Thread executor |
| `taxonomy.warm_partition` | `bump_partition_version` + `warm_retrieval` | ADR-005 (§3.13) |
| `cascade.run` | Full correction cascade orchestration | May fan out Fabric signals |

##### Semantics

- Per-tenant mutex for heavy jobs; global `jobs.max_concurrent` (default 2).
- Busy → `{status: "busy", active_job_id}` (no silent drop).
- Status: `queued | running | completed | failed`.

```
choruscontrol/engine/job_queue.py
choruscontrol/engine/handlers/{sleep,reindex,warm_partition,cascade}.py
choruscontrol/engine/memory_worker.py   # wrapper → cortex.sleep
```

---

#### 3.6 Cryptographic Audit Pipeline (closes G06, G10)

1. Envelope `{timestamp, admin_user, action, tenant_id, details}` → canonical JSON → Ed25519 sign.
2. Async append to `choruscontrol_audit.jsonl`.
3. Best-effort stream to Postgres `audit_events`.
4. Notable actions include: `correction_cascade`, `guard.policy.update`, `partition.warm`, `license.upload`, conflict resolve, etc.

```sql
CREATE TABLE audit_events (
  id BIGSERIAL PRIMARY KEY,
  event_time TIMESTAMPTZ NOT NULL,
  admin_user TEXT NOT NULL,
  action TEXT NOT NULL,
  tenant_id TEXT NOT NULL,
  details JSONB NOT NULL,
  signature TEXT NOT NULL,
  ingested_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
```

Export: `GET /api/v1/admin/audit/export` — feature `audit.export` + role `admin`.  
SOC2 pack: see **§3.18**.

```
choruscontrol/audit/{logger,async_sink,export,verify}.py
```

---

#### 3.7 Control-Plane APIs & UI Mapping (closes G07, G14–G16)

Base path: `/api/v1`. UI: custom themed design system (light/dark CSS variables, Chart.js where needed) under `choruscontrol/ui/` — **not** Tailwind (decision recorded July 2026).

Honesty banners required in UI:

- Shine: **PASS ≠ world-true** (grounded in preload only).
- Guard: scorecard rates require measured profile (`heavy` / domain artifact) — never implied from `web_chat`.

##### Master tab → API map

| Tab | UI | Backend |
|-----|-----|---------|
| Overview | `/overview` | health matrix, **caps**, token-tax, Driver latency, dogfood, **fleet topology summary** |
| Trace | `/trace` | live wire WS, ledger, **Guard→Ledger→Shine** stitch, zero-token replay |
| Taxonomy | `/taxonomy` | 64-d search, category tree, chunk health, reindex, **partition/warm ops** |
| Memory | `/memory` | bitemporal facts, sleep, conflicts, **cascade on resolve**, explain/recall_at proxy |
| Cortex | `/cortex` | PrismCortex activity, chunks, digest/recall/sleep; R04 `memory_endpoint` |
| Guard | `/guard` | logs, shadow compare, lexicon, **Policy Studio** |
| Admin | `/admin` | ChorusControl license, **stack license status**, tenants, audit/export, RBAC, support link, doctor snapshot |

---

##### 3.7.1 System Overview `/overview` (closes G14)

**One composition:** brand + health story — not a card dump.

| Capability | API | Real source (no placeholders) |
|------------|-----|-------------------------------|
| L0–L5 health matrix | `GET /health/matrix` | Process, license, audit DB, Fabric, Graph workers, Prism pack |
| **Capability caps** | `GET /health/caps` | §3.12 aggregate |
| Token tax / cache ROI | `GET /metrics/token-tax` | `PrismCache.get_metrics()` — hit_rate, tokens_saved, cost_saved, `evicted_by_tags`, `evicted_by_vector` |
| PrismDriver latency | `GET /metrics/prismdriver` | Driver health / query latency stats |
| Dogfood status | `GET /status/dogfood` | ChorusGraph dogfood / probe |
| Fleet snapshot | `GET /fleet/topology` | §3.14 summary strip |
| Cold audit estimate | `POST /metrics/cold-audit` | Upload query JSONL → chorusgraph-audit-style simulation (optional) |

**Layer health matrix (L0–L5)**

| Layer | Meaning | Probe |
|-------|---------|-------|
| L0 | Process / container | local up |
| L1 | License | claims valid |
| L2 | Postgres / audit sink | optional DB ping |
| L3 | Fabric / PrismAPI | connected + peer count |
| L4 | ChorusGraph workers | heartbeat / dogfood |
| L5 | Prism Pack | Guard/Shine/Cortex/RAG adapter health |

---

##### 3.7.2 Execution Trace `/trace` (closes G16)

**Single wire model** — every run is stitched as:

```
PrismGuard.resolution_gate
    → ChorusGraph Route Ledger (hops, rule_chain, kind/detail e.g. shine.verdict)
    → PrismShine ShineVerdict (decision, resolution_gate, evidence_hash)
```

| API | Behavior |
|-----|----------|
| `WS /traces/live` | Stream ledger steps + gate events from exporters / dogfood |
| `GET /traces/{id}` | Full stitched timeline |
| `GET /traces/{id}/ledger` | Raw Route Ledger |
| `POST /traces/{id}/replay` | **Zero-token replay** — cache/ledger only; assert no `call_llm` / provider calls |

Trace event schema (v1):

```json
{
  "v": 1,
  "run_id": "...",
  "tenant_id": "...",
  "ts": 0.0,
  "stage": "guard|graph|shine",
  "resolution_gate": "...",
  "hop": "...",
  "kind": "...",
  "detail": {},
  "decision": "allow|block|pass|flag|regenerate|null"
}
```

---

##### 3.7.3 RAG & Taxonomy `/taxonomy` (closes G17 partially — detail in §3.13)

| API | Behavior |
|-----|----------|
| `POST /taxonomy/search` | 64-d / PrismRAG search; return `category_slug` |
| `GET /taxonomy/tree` | Category tree from mapping |
| `GET /taxonomy/chunks/health` | Decay / bleed heatmap inputs |
| `POST /jobs/reindex` | `taxonomy.reindex` job |
| `GET /taxonomy/partitions` | Partition → version matrix |
| `POST /jobs/warm-partition` | `taxonomy.warm_partition` job |

---

##### 3.7.4 Cortex Memory `/memory` + `/cortex` (ties to §3.11, R04)

| API | Behavior |
|-----|----------|
| `GET /memory/facts` | Bitemporal active vs superseded |
| `POST /jobs/sleep` | `cortex.sleep` |
| `GET /memory/conflicts` | Open conflicts (prefer Cortex API proxy) |
| `POST /memory/conflicts/{id}/resolve` | Resolve **and** enqueue **correction cascade** |
| `POST /memory/explain` | Proxy Cortex `/explain` |
| `POST /memory/recall_at` | Proxy time-travel recall |
| `GET /memory/cascade/{id}` | Cascade status (acks, evictions) |
| `GET /cortex/snapshot` | Activity + chunks + facts + serving `memory_endpoint` |
| `POST /cortex/digest\|recall\|explain\|sleep` | Ops console against tenant memory |
| `POST /cortex/conflicts/resolve` | Resolve + cascade |

Tenant → memory addressing: fleet registry `memory_endpoint` (agent advertises via join/heartbeat). HTTP endpoints are proxied; `local://` / unset use mother-local PrismCortex.

Prefer Cortex HTTP enterprise surfaces (`/conflicts`, `/explain`, `/recall_at`, replay certificate) via adapter — ChorusControl adds RBAC, audit, and cascade, **not** a second graph store.

---

##### 3.7.5 Security WAF `/guard` — Policy Studio (closes G15)

Encode Guard README rules in product policy — wrong profile destroys UX.

| API | Behavior |
|-----|----------|
| `GET /guard/logs` | Decisions with `resolution_gate` |
| `GET /guard/shadow/compare` | web_chat (or ingress) vs shadow ONNX |
| `GET\|PUT /guard/lexicon` | Tenant lexicon editor |
| `GET\|PUT /guard/policy` | **Policy Studio** document (below) |
| `POST /guard/caps` | Live `prismguard caps` for active profile |
| `POST /guard/shadow/promote` | Promote shadow→enforce only after gate checklist |

**Policy document (per tenant)**

```json
{
  "ingress_profile": "web_chat",
  "ingress_use_onnx": false,
  "shadow_profile": "light",
  "shadow_enabled": true,
  "enforce_shadow": false,
  "domain_pilot": null,
  "domain_slug": null,
  "artifact_id": null,
  "recommended_preset": "finance_hub"
}
```

**Built-in recommended presets**

| Preset | Ingress | Shadow | Notes |
|--------|---------|--------|-------|
| `finance_hub` | `web_chat`, ONNX off | `light` observe-only | From Guard finance/hub wiring guidance |
| `production_latency` | `light` | optional | Hybrid ONNX |
| `scorecard` | `heavy` | — | Methodology parity only |
| `vertical_learn` | `domain_pilot` + domain artifact | — | Train-first; taxonomy on |

UI must block saving `domain_pilot` without matching `artifact_id` / domain warning.  
Never invent `finance_pilot` / `healthcare_pilot` — always `domain_pilot` + `domain=`.

---

##### 3.7.6 Admin & License `/admin` (ties to §3.16, §3.18)

| API | Behavior |
|-----|----------|
| License upload/status | ChorusControl key only (verify) |
| `GET /admin/stack-licenses` | Sibling key status (§3.16) |
| Tenant isolation matrix | CRUD within `max_tenants` |
| Audit console + export | §3.6 / §3.18 |
| RBAC management | §3.3 |
| Support deep link | Side 1 URL |
| `GET /admin/doctor` | Snapshot from §3.17 |

---

##### Module layout (API / UI / services)

```
choruscontrol/
  server.py
  api/{health,traces,taxonomy,memory,guard,admin,jobs,fleet,metrics,cascade}.py
  services/{overview,trace_service,taxonomy_service,memory_service,
            guard_service,cascade_service,caps_service,fleet_service}.py
  ui/templates/  ui/static/
```

---

#### 3.8 Runtime, Config & Packaging (closes G08)

| Variable | Purpose |
|----------|---------|
| `CHORUSCONTROL_LICENSE_KEY` | Offline license JWT |
| `CHORUSCONTROL_AUDIT_PRIVATE_KEY_PEM` | Audit signing |
| `CHORUSCONTROL_ADMIN_TOKEN` | Local admin auth |
| `DATABASE_URL` | Postgres audit stream |
| `FABRIC_ENDPOINT` | CHORUS Fabric / PrismAPI |
| `INSIGHTITS_SUPPORT_URL` | Side 1 support |
| `INSIGHTITS_PORTAL_URL` | Optional billing/account deep link |
| `JOBS_MAX_CONCURRENT` | Maintenance concurrency |
| `INVALIDATION_THRESHOLD` | Default probe threshold |
| `CHORUSCONTROL_DEMO_MODE` | NullAdapters + synthetic data (§3.17) |
| `PRISMCORTEX_URL` / API key | Optional Cortex HTTP |
| Sibling license env vars | Display-only (§3.16) |
| `CHORUSCONTROL_MOTHER_URL` | Agent → mother bootstrap URL (§3.19) |
| `CHORUSCONTROL_JOIN_TOKEN` | Agent enrollment token (§3.19) |
| `CHORUSCONTROL_NODE_ID` | Stable agent node id |
| `CHORUSCONTROL_NODE_ROLE` | GREEN/BLUE/ORANGE/worker/… |
| `CHORUSCONTROL_NETWORK_ZONE` | `in_vpc` \| `external` |

- Multi-stage `Dockerfile` (Python 3.11+).
- `docker-compose.yml`: `choruscontrol` + optional `postgres`.
- `/healthz` liveness; `/readyz` license + critical deps (unless demo mode).

##### Dependency floors

```
chorusgraph>=1.3.0
prismguard>=0.1.10
prismcortex[prism-plus]>=0.3.0
prismrag-patch>=0.2.1
prismshine>=0.2.2
prismlib-plus>=0.8.0
chorus-fabric>=0.2.0
prismlang>=0.1.2
prismresonance>=0.3.0
chorusmesh>=0.1.0
fastapi, uvicorn, pydantic>=2, cryptography, httpx, asyncpg|psycopg
```

**Rules:** Never mix Cortex `[prism]` + `[prism-plus]`. Document Guard/Shine ONNX downloads for enforce/span paths. Prefer adapters over private imports.

---

#### 3.9 Integration Adapters (closes G09)

```
choruscontrol/adapters/
  cortex.py         # digest/recall/sleep/facts/conflicts/on_event/explain/recall_at
  rag.py            # tree, search, reindex, chunk health
  guard.py          # check logs, caps, shadow, lexicon, policy apply
  shine.py          # verdicts, capabilities, consistency hooks
  graph.py          # ledger, dogfood, mark_revalidate, interceptors metadata
  cache.py          # get_metrics, invalidate_tags/where
  driver.py         # PrismDriver latency/health
  fabric.py         # broadcast / subscribe / peers
  license_keys.py   # chorusmesh public key + sibling status parsers
  partitions.py     # warm_retrieval, bump_partition_version, get_chunk_vectors
```

Each adapter: Protocol/ABC, **NullAdapter** (tests + demo mode), map errors → `ChorusControlError`.

---

#### 3.10 Verification Matrix (closes G11, G12–G20)

| Area | Required tests |
|------|----------------|
| License | Valid / expired / tampered / missing; node & tenant limits; feature gates |
| Job queue | Non-blocking vs digest/recall mocks; per-tenant busy; reindex; warm_partition |
| Invalidation | Schema; config threshold; publisher; subscriber eviction mock |
| **Cascade** | Conflict resolve → invalidate + mark_revalidate; single audit action; ack aggregation |
| **Caps** | Aggregate reflects Guard profile + Shine span_backend; no false scorecard flags |
| **Metrics** | Token-tax/Driver adapters called; demo mode returns labeled synthetic data |
| **Guard policy** | Reject unsafe save without artifact; finance_hub preset; shadow promote gate |
| **Trace wire** | Stitch guard+ledger+shine; replay zero LLM calls |
| **Partitions** | Warm job bumps version via adapter |
| **Fleet** | Topology roles parsed; ack coverage; join handshake; spoof rejected |
| **Agent latency** | Hot-path invoke/digest/recall does not await mother; ledger export is async/batched |
| **Transport** | Commands/telemetry on Fabric and/or PrismAPI; PrismLang not used as control wire |
| **Stack licenses** | Display valid/expired sibling keys without enforcing foreign private APIs |
| Audit | Sign round-trip; async sink; export verify; SOC2 pack contents |
| RBAC | Denied vs allowed on mutating routes |
| Health | L0–L5 degraded states |
| Doctor | Fails on missing floor versions |
| API smoke | Happy path per tab |

---

#### 3.11 Correction Cascade (closes G12) — **P0 moat**

Admin invalidate alone is insufficient. Own the end-to-end loop your products already support:

```
Cortex correction / conflict resolve / MemoryEvent(on_event)
        │
        ▼
CascadeService.run(cascade_id, tenant_id, tags, probe?)
        ├─► Fabric INVALIDATE_CACHE (tags and/or where) + force_refresh
        ├─► Workers: cache.invalidate_* + graph.mark_revalidate
        ├─► Shine consistency hint / CACHE_PREDATES_FACT_UPDATE surfacing
        └─► Audit action: correction_cascade (one envelope)
```

##### Triggers

| Trigger | Behavior |
|---------|----------|
| `POST /memory/conflicts/{id}/resolve` | Always runs cascade after successful resolve |
| Cortex `on_event` (in-process or webhook) | Auto-cascade when `cascade.auto` feature enabled |
| Manual `POST /cascade` | Operator-triggered with tags / probe |
| Taxonomy chunk edit | Optional cascade with doc/tag set |

##### Status API

`GET /api/v1/cascade/{id}` → `{steps[], acks[], evicted_estimate, mark_revalidate_sent, state}`.

Memory UI shows cascade progress after resolve — not a silent background fire-and-forget.

```
choruscontrol/services/cascade_service.py
choruscontrol/engine/handlers/cascade.py
```

---

#### 3.12 Honest Capability Caps (closes G13) — **P0**

Aggregate sibling truth tables; never invent green status.

`GET /api/v1/health/caps` returns:

```json
{
  "guard": {
    "profile": "web_chat",
    "onnx_tier": null,
    "onnx_ready": false,
    "prismrag_taxonomy": false,
    "shadow_onnx": true
  },
  "shine": {
    "span_backend": "lexical",
    "threshold_status": "proposal",
    "pass_means": "grounded_in_preload_not_world_true"
  },
  "cortex": {"ann": false, "prism_plus": true},
  "graph": {"version": "1.3.0", "dogfood_ok": true},
  "cache": {"backend": "prism", "metrics_available": true},
  "fabric": {"peers": 3, "connected": true},
  "license": {"tier": "enterprise", "features": ["..."]}
}
```

Overview renders caps as the **source of truth** beside the health matrix.  
UI copy must not claim law COMPARISON_REPORT rates on `web_chat`.

```
choruscontrol/services/caps_service.py
```

---

#### 3.13 Warm-Chunk / Partition Ops (closes G17) — **P1**

ChorusGraph ADR-005 surfaces in Taxonomy:

| Concept | Control-plane behavior |
|---------|------------------------|
| `partition` + `version` | Matrix per tenant on Taxonomy tab |
| `bump_partition_version` | Part of `taxonomy.warm_partition` job |
| `warm_retrieval` | Job step after bump |
| `get_chunk_vectors` | Optional inspector / decay viz input |
| Chunk health heatmap | Distribution of `category_slug` + stale version flags |

Job params: `{tenant_id, partition, version?}`.

---

#### 3.14 Fleet Topology GREEN / BLUE / ORANGE (closes G18) — **P1**

From PrismLib Micro cluster roles:

| Role | Meaning in UI |
|------|----------------|
| GREEN | Active master |
| BLUE | Warm standby (auto-promote) |
| ORANGE | Syncing reserve |

Fleet topology (§3.14) **and node inventory are fed by the agent registry in §3.19** — heartbeats carry role, zone, and product versions.

`GET /api/v1/fleet/topology`:

```json
{
  "nodes": [
    {"node_id": "n1", "role": "GREEN", "last_health_at": 0.0, "cache_contrib": true}
  ],
  "invalidation_coverage": {"last_correlation_id": "...", "acked": ["n1"], "pending": ["n2"]}
}
```

Overview shows a compact topology strip; full detail can live under Admin or Overview expand.  
Optional later (not v1 required): ChorusMesh Slack/PagerDuty deep integration when sibling license present.

---

#### 3.15 Cortex Deep-Link / Proxy (P1)

Do not fork Cortex enterprise APIs. Adapter methods proxy:

- Conflicts list/resolve  
- `/explain`  
- `/recall_at`  
- Replay certificate fetch (display / download)

ChorusControl layers: auth, audit, cascade, tenant scoping.

---

#### 3.16 Stack License Status Console (closes G19) — **P1**

Customers may hold multiple offline keys. Admin shows **status only** (verify with known public PEMs / parsers):

| Key type | Env / upload | Side 2 behavior |
|----------|--------------|-----------------|
| ChorusControl | `CHORUSCONTROL_LICENSE_KEY` | Enforce |
| ChorusMesh | `CHORUSMESH_LICENSE_KEY` | Display tier/exp/nodes |
| PrismGuard Team+/Business | product-specific | Display if detectable |
| PrismCortex commercial | product-specific | Display if detectable |

- **Never** embed foreign private signing keys.
- Deep link “Get / renew” → `INSIGHTITS_PORTAL_URL` (Side 1).
- Issuance remains Side 1 handoff only.

---

#### 3.17 Doctor CLI, Demo Mode, Agent Docs (closes G20) — **P2**

##### `choruscontrol doctor`

Checks: Python version, dependency floors, license present/valid, Fabric ping, Postgres (if configured), Guard/Shine ONNX presence when policy requires, adapter import errors. Exit non-zero on hard failures.

##### Demo mode

`CHORUSCONTROL_DEMO_MODE=1` → NullAdapters + synthetic ledger/metrics/caps labeled **DEMO** in UI. Enables UI development without a full fleet.

##### Agent / OpenAPI docs

Ship sibling-style docs in-repo:

- `docs/ai-overview.md` (or under `doc/`) — concise assistant context  
- OpenAPI from FastAPI auto-schema at `/openapi.json`

##### Optional later (explicitly deferred)

InsightPlugIn SMS (`MASTER: sleep tenant X`) — not v1.

---

#### 3.18 Export Pack & DX polish (P2)

`GET /api/v1/admin/export/soc2-pack` (alias of `GET /api/v1/admin/soc2-export`; feature `audit.export`) returns a zip:

- Verified audit JSONL  
- Redacted license claims snapshot  
- Caps snapshot  
- Doctor snapshot  

Supports SOC2/HIPAA evidence workflows called out in the PDF Admin tab.

---

#### 3.19 Fleet Agent, PrismAPI Discovery & Secure Handshake (closes G21)

This section answers the multi-container control question:

> Customers install a ChorusControl component on every codebase/container that runs Prism libs; the **mother** control plane discovers those nodes (in-network or out-of-network) over PrismAPI / CHORUS Fabric with a secure handshake, then shows and controls the whole fleet.

**Yes — with one refinement:** do **not** install the full mother UI on every worker. Ship **two install profiles** from the same package.

##### 3.19.1 Two install profiles (one package)

| Profile | Pip install | Where | What it runs |
|---------|-------------|-------|--------------|
| **Mother (control plane)** | `pip install "choruscontrol[server]"` | One (or HA pair) admin container | FastAPI + UI + registry + jobs + audit |
| **Agent (fleet node)** | `pip install "choruscontrol[agent]"` | Every app/worker/container with Prism libs | Thin daemon: detect products, heartbeat, receive commands |

```bash
## Mother
pip install "choruscontrol[server]"
choruscontrol serve --host 0.0.0.0 --port 8443

## Any worker / RAG / Guard / Graph container
pip install "choruscontrol[agent]"
export CHORUSCONTROL_MOTHER_URL=https://choruscontrol.internal:8443
export CHORUSCONTROL_JOIN_TOKEN=...          # short-lived join secret from mother
export CHORUSCONTROL_NODE_ID=worker-7
choruscontrol-agent run
```

Optional auto-start from app code (library mode):

```python
from choruscontrol.agent import attach_agent

## Call once at process boot — non-blocking background task
attach_agent()  # reads env; registers with mother over PrismAPI/Fabric
```

`[agent]` must stay **thin**: fabric/prismapi client, local product probe, command handlers. It must **not** pull the full UI, Chart.js assets, or Postgres audit stack.

##### 3.19.2 What the agent detects locally

On start and on a schedule, the agent inventories installed / importable Insight products and versions:

| Probe | Detects |
|-------|---------|
| `importlib.metadata` / try-import | `chorusgraph`, `prismguard`, `prismshine`, `prismcortex`, `prismrag_patch`, `prismlib`/`prismlib-plus`, `prismlang`, `prismresonance`, `chorus_fabric`, `chorusmesh` |
| Local caps hooks | Guard `caps`, Shine `capabilities`, cache metrics availability |
| Role hint | Env `CHORUSCONTROL_NODE_ROLE=GREEN\|BLUE\|ORANGE\|worker\|db-wrapper` |
| Tenant | `CHORUSCONTROL_TENANT_ID` / app tenant |

Heartbeat payload (PrismAPI frame or Fabric SIGNAL):

```json
{
  "event": "NODE_HEARTBEAT",
  "v": 1,
  "node_id": "worker-7",
  "tenant_id": "acme",
  "role": "GREEN",
  "network_zone": "in_vpc",
  "products": {
    "chorusgraph": "1.3.0",
    "prismguard": "0.1.10",
    "prismshine": "0.2.2",
    "prismlib-plus": "0.8.0"
  },
  "caps_digest": "...",
  "listen_endpoints": {"fabric": "10.0.2.15:50051"},
  "ts": 1720000000.0
}
```

Mother **Fleet / Overview** becomes a live inventory: which containers exist, which Prism products they run, versions, caps, online/offline.

##### 3.19.3 Transport: PrismAPI + CHORUS Fabric everywhere agents run

Agents do **not** invent a new proprietary bus. They use the stack customers already install:

| Channel | Use |
|---------|-----|
| **CHORUS Fabric** | Primary M2M: HEARTBEAT, INVALIDATE_CACHE, POLICY_PUSH, JOB_DISPATCH, ACK — encrypted float32/SIGNAL frames, watermarks |
| **PrismAPI** (prismlib-plus) | Vector-native / HTTP enterprise control where Fabric is not yet wired; same auth story |
| **Mother registry HTTP** | Bootstrap only: join + mTLS cert or session material issuance — then prefer Fabric for steady state |

Mother holds the **node registry** (source of truth for UI). Agents are dumb executors + sensors.

##### 3.19.4 In-network vs out-of-network

| Mode | Topology | Discovery | Trust |
|------|----------|-----------|-------|
| **In-network** | Same VPC / k8s / compose as mother | Agent dials `CHORUSCONTROL_MOTHER_URL` / Fabric control plane; optional multicast/DNS `choruscontrol` | Join token + Fabric session keys; private IPs OK |
| **Out-of-network** | Remote DC, partner VPC, edge, laptop agent | Agent dials public/mother ingress URL (customer-owned) | **Mandatory secure handshake** (§3.19.5); no plaintext control |

Out-of-network nodes appear in the same Fleet UI with a badge: `zone=external` / `zone=in_vpc`. Operators can filter and set policy (e.g. external nodes may receive invalidate but not lexicon pulls with PII — configurable).

**Important:** “Out of network” still means **customer’s** ChorusControl mother — **not** insightits.com. No phone-home.

##### 3.19.5 Secure handshake (especially out-of-network)

Bootstrap (once per node):

1. Admin creates a **join token** on mother (`POST /api/v1/fleet/join-tokens`) — TTL, max uses, allowed zones, optional node_id bind.
2. Agent presents join token + node metadata over TLS to mother `/api/v1/fleet/join`.
3. Mother verifies token, checks `max_nodes` license claim, issues:
   - Node identity (`node_id`)
   - Fabric/PrismAPI **session material** (or mTLS client cert)
   - Optional enrollment proof signed by mother’s enrollment key
4. Agent stores secrets in local secure path / secret mount (not app logs).
5. Steady state: Fabric handshake + rolling watermark / key epoch (CHORUS Fabric v0.2 forward secrecy). Heartbeats and commands ride authenticated channels only.

```
Agent                         Mother
  │  TLS + join_token           │
  │ ──────────────────────────► │  verify token, max_nodes
  │  node cert / session keys   │
  │ ◄────────────────────────── │
  │  Fabric Hello + watermark   │
  │ ──────────────────────────► │  registry upsert
  │  HEARTBEAT / ACK            │
  │ ◄────────────────────────── │  INVALIDATE / POLICY / JOB
```

Revocation: mother marks node `revoked` → refuse heartbeats; agent self-stops command execution. Short join-token TTL preferred over long-lived static shared secrets.

##### 3.19.6 Control plane → agent command surface

Once registered, mother can push (RBAC + audit + license feature gated):

| Command | Agent local action |
|---------|-------------------|
| `INVALIDATE_CACHE` | `cache.invalidate_tags` / `invalidate_where` + optional `mark_revalidate` |
| `APPLY_GUARD_POLICY` | Write/reload local Guard policy overlay |
| `RUN_SLEEP` / `RUN_REINDEX` / `WARM_PARTITION` | Execute if that product exists locally; else NACK `unsupported` |
| `REQUEST_CAPS` | Refresh local caps → reply |
| `REQUEST_METRICS` | Cache/Driver snapshot → reply |
| `DRAIN` / `REVOKE` | Stop accepting work / unregister |

Unsupported product on a node → honest NACK (e.g. sleep on a Guard-only sidecar). Mother UI shows per-node capability from inventory — don’t offer sleep on nodes without Cortex.

##### 3.19.6a Zero hot-path latency (hard requirement)

The agent must **never** add latency to ChorusGraph / Prism application paths (`invoke`, `digest`, `recall`, LLM calls, retrieve, Guard `check` on the request thread).

| Rule | Design |
|------|--------|
| **Out-of-band only** | Agent runs as a background task/thread/process. App hot path does not `await` mother RPCs. |
| **No sync phone-home on request** | Heartbeats, ledger shipping, caps refresh are scheduled / queued — never inside `Graph.invoke` or middleware that blocks the user request. |
| **Subscribe, don’t poll on hot path** | Commands arrive on Fabric/PrismAPI **async** channels; a worker loop applies them. |
| **Local-first commands** | Invalidation/policy apply is local in-process (or same-host) after async receipt — same cost as today’s `invalidate_tags`, not an extra network RTT on the user query. |
| **Bounded queues** | If mother is slow/unreachable, drop or spill ledger batches with backpressure metrics — **never** block the graph. |
| **Opt-in attach** | `attach_agent()` schedules background work; default is non-blocking. Document that wrapping the request path is forbidden. |
| **Budget** | Steady-state agent CPU/RAM overhead target: negligible vs app; heartbeat interval default 5–15s; ledger export batched (e.g. 100ms–1s flush), not per-hop sync. |

**Forbidden patterns**

```python
## FORBIDDEN — adds RTT to every user request
def node(state):
    mother.report_hop(state)   # sync
    return answer
```

```python
## REQUIRED — app unchanged; agent tails ledger/export queue
attach_agent()  # background
graph.invoke(...)  # zero agent await on this call
```

Mother UX may be eventually consistent (node went stale 10s ago) — that is preferred over slowing production traffic.

##### 3.19.6b Reading ChorusGraph logs / Route Ledger (async export)

Agents **observe** ChorusGraph without instrumenting every node by default:

| Source | What mother gets | How shipped |
|--------|------------------|-------------|
| **Route Ledger** | Per-hop audit: cache hits, `rule_chain`, `kind`/`detail` (e.g. `shine.verdict`) | Agent subscribes to ledger export hook / SQLite/Postgres ledger tail / dogfood exporter — **async batch** to mother |
| **Structured JSON logs** | ChorusGraph observability logs (if enabled) | Optional file/journal tail → batch upload on control channel |
| **Guard / Shine side events** | `resolution_gate`, `ShineVerdict` | Same stitch pipeline as Trace tab; agent forwards when present on node |
| **Cold audit artifacts** | `chorusgraph-audit` style JSONL | Operator upload or agent file watch — not on hot path |

Export frame (over Fabric SIGNAL or PrismAPI):

```json
{
  "event": "LEDGER_BATCH",
  "v": 1,
  "node_id": "worker-7",
  "tenant_id": "acme",
  "run_ids": ["..."],
  "entries": [ { "hop": "...", "rule_chain": [], "kind": "shine.verdict", "detail": {} } ],
  "truncated": false
}
```

If the queue is full → mark `truncated: true` or drop oldest batch; increment `agent_ledger_dropped_total`. Trace UI on mother consumes these batches for live wire (§3.7.2).

PrismLang **`rule_chain` / 64-d envelopes** appear **inside** ledger entries as payload. PrismLang is **not** the mother↔agent transport.

##### 3.19.6c Control transport — what carries mother ↔ agent traffic

| Channel | Role | Use for |
|---------|------|---------|
| **CHORUS Fabric** | **Primary** control & telemetry bus | Heartbeat, join session, INVALIDATE, POLICY_PUSH, JOB_DISPATCH, ACK, LEDGER_BATCH, CAPS |
| **PrismAPI** (prismlib-plus) | **Secondary / HTTP enterprise** control | Same command/telemetry set when Fabric not available; auth + metrics friendly |
| **PrismLang** | **Not a control bus** | Hop compression + `rule_chain` **content** inside ChorusGraph ledger; mother may *display* PrismLang fields but agents do not “talk to mother via PrismLang” |

```
ChorusGraph hot path          Agent (background)              Mother
  invoke / digest / recall  →  ledger queue (local, non-block) → Fabric/PrismAPI
       │                              ↑ commands async
       └── NO await mother ───────────┘
```

**Summary:** Good control = mother registry + async commands + ledger batches. Zero added request latency = never put Fabric/PrismAPI/PrismLang on the user hot path. Communication to mother = **Fabric or PrismAPI**; PrismLang is observed data, not the wire.

##### 3.19.7 Packaging extras

```toml
[project.optional-dependencies]
server = ["fastapi", "uvicorn", "jinja2", "..."]      # mother
agent = ["chorus-fabric", "httpx", "cryptography"]   # thin
all = ["choruscontrol[server,agent]"]
```

Entrypoints:

- `choruscontrol` / `choruscontrol serve` — mother
- `choruscontrol-agent` — agent daemon
- `choruscontrol doctor` — works on both (agent checks local products + mother reachability)

##### 3.19.8 Mother APIs added

| API | Purpose |
|-----|---------|
| `POST /fleet/join-tokens` | Admin creates join token |
| `POST /fleet/join` | Agent bootstrap |
| `GET /fleet/nodes` | Inventory (products, zone, last_seen, caps) |
| `POST /fleet/nodes/{id}/command` | Dispatch command |
| `DELETE /fleet/nodes/{id}` | Revoke |
| `WS /fleet/live` | Live join/leave/heartbeat for Overview |

Fleet topology (§3.14) is fed by this registry.

##### 3.19.9 Security rules

- Join tokens are single-purpose, TTL-bound, audited.
- Out-of-network **requires** TLS + handshake; refuse cleartext.
- Agent never embeds ChorusControl **license private** keys; it may carry a **node credential** only.
- Heartbeats authenticate; spoofed `node_id` without session material is rejected.
- PII-minimized heartbeats (versions/caps, not user prompts).
- License `max_nodes` enforced at join time.

##### 3.19.10 Modules

```
choruscontrol/
  agent/
    __init__.py          # attach_agent()
    runtime.py           # daemon loop
    probe.py             # product inventory
    handshake.py         # join + session
    commands.py          # local executors
    transport.py         # Fabric / PrismAPI client
  fleet/
    registry.py          # mother node store
    join.py              # tokens + enroll
    dispatcher.py        # command fan-out
```

---

### 4. Target Repository Layout

```
choruscontrol/
  __init__.py
  server.py
  config.py
  cli.py
  agent/ ...
  fleet/ ...
  api/ ...
  auth/ ...
  audit/ ...
  license/ ...
  engine/ ...
  adapters/ ...
  services/ ...
  ui/
doc/
tests/
Dockerfile                 # mother image
Dockerfile.agent           # optional slim agent image
docker-compose.yml         # mother + sample agent workers
pyproject.toml
README.md
```

---

### 5. Implementation Sequence

**Detail in §10.** Short form:

1. Platform foundation + runtime touch — `[server]`/`[agent]`, org/tenant/user auth, license, mother, agent join, first live Prism signal.
2. Core Prism adapters + caps / invalidate / Trace feed.
3. Unified ops data model (assets, events, metrics, logs, audit, policies).
4. Platform services — monitoring, versioning, governance, incident correlation.
5. Intelligence layer — AI Score / recommendations only on real data.
6. Enterprise polish — fleet at scale, reporting; marketplace via Side 1.

Each iteration ships **usable, connected** platform capability — not isolated widgets. Concrete engineering checklist remains: scaffolding → license/RBAC → fleet join → adapters → engine → commands/ledger → tabs/UI → doctor/tests → harden.

---

### 6. Decision Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Product category name | **Enterprise AI OS / AI Operations Platform** | Not dashboard/monitoring/control-plane product |
| Asset Graph | Core platform source of truth | Blast radius, incidents, Assistant |
| Ops Assistant | Native, gated exec, beside dashboards | AI-native ops |
| AI Score | Transparent, post-telemetry | Trust KPI without fake greens |
| Policy engine | Multi-domain, versioned | Beyond Guard-only |
| “Control plane” term | Architecture only (mother + agent) | Keep precise engineering language |
| Side 1 in this repo? | No — future insightits.com handoff | Portal vs product split |
| Full UI on every worker? | **No** — thin `[agent]` only | Avoid heavyweight surface on app nodes |
| How workers enroll | `pip install choruscontrol[agent]` + join handshake | Multi-container discovery |
| Discovery / control transport | **PrismAPI/HTTP primary; Fabric optional (`[fabric]`)** | R01 — Fabric not required for control plane |
| PrismLang as mother wire? | **No** — ledger payload only | Hop protocol ≠ control bus |
| Hot-path latency | **Hard zero** — agent out-of-band only | Never await mother on invoke/digest/recall |
| Ledger to mother | Async batched Route Ledger / log export | Trace without slowing graph |
| Out-of-network | TLS + join handshake | Multi-DC / edge; no phone-home |
| Phone-home to insightits.com for fleet? | **Forbidden** | Air-gap + sovereignty |
| Platform vs modules | **Unified platform** | Build once; everything connected (§10) |
| Intelligence layer timing | After real events/metrics | No fake AI Score |
| Marketplace | Side 1 / late enterprise | Not Side 2 v1 core |
| Orgs/Projects before Prism? | **Hybrid** — foundation + early runtime | Avoid empty shell CRM |
| Sleep concurrency | Per-tenant mutex + global cap | Avoid cross-tenant HOL blocking |
| Audit storage | JSONL + Postgres | Spec dual requirement |
| Invalidation acks | Optional | Air-gap friendly |
| Frontend | Custom themed HTML/JS + Chart.js (not Tailwind) | Design-system decision July 2026 |
| License phone-home | Forbidden | 100% offline verify |
| License lapse | **14-day read-only grace** + ±24h clock skew (R02) | Mutations blocked; UI banner |
| SOC2 export paths | `/admin/soc2-export` + `/admin/export/soc2-pack` | Alias for design name |
| Correction handling | First-class cascade service | Unique stack moat |
| Health honesty | Caps aggregate required | Guard/Shine ethics |
| Metrics | Real PrismCache/Driver only | Benchmark credibility |
| Guard UX | Policy Studio + presets | Prevent law-ONNX-on-finance |
| Trace model | Guard → Ledger → Shine | Real hop instrumentation |
| Cortex UI data | Proxy enterprise APIs | Don’t fork memory engine |
| Sibling licenses | Status display only | Issuance stays Side 1 |
| VectorBridge / InsightPlugIn | Out of v1 | Scope |

---

### 7. Acceptance Criteria

ChorusControl Side 2 succeeds as an **Enterprise AI Operating System / AI Operations Platform** when:

- [x] Product UI/docs present **Enterprise AI OS / AI Operations Platform** (not dashboard/monitoring/control-plane).
- [x] Offline license enforces signature, expiry, node/tenant limits, features — zero phone-home.
- [x] **Mother** (`[server]`) and **agent** (`[agent]`) ship from one package.
- [x] Agent detects local Prism products/versions and heartbeats into mother registry.
- [x] Join handshake in-network; out-of-network requires TLS + token; spoof rejected; `max_nodes` enforced.
- [x] Agent is **out-of-band**: no await of mother on `invoke` / `digest` / `recall`.
- [x] Route Ledger/logs ship as **async batches** over Fabric or PrismAPI; backpressure drops, never blocks.
- [x] Control transport is **HTTP/PrismAPI primary** (R01); Fabric optional; PrismLang is ledger content only.
- [x] Mother dispatches invalidate / policy / caps; unsupported commands NACK honestly.
- [x] Admin mutations RBAC-gated; Ed25519 audit in JSONL (+ Postgres when configured).
- [x] Sleep, reindex, warm-partition non-blocking vs digest/recall.
- [x] Correction cascade on conflict resolve; UI shows status.
- [x] Caps + Overview reflect real truth — no fake scorecard claims.
- [x] Token-tax / Driver metrics from adapters (or labeled DEMO).
- [x] Guard Policy Studio presets; unsafe domain_pilot save blocked.
- [x] Trace Guard → Ledger → Shine; replay zero LLM tokens.
- [x] Taxonomy partition matrix + warm jobs.
- [x] Fleet topology GREEN/BLUE/ORANGE + zone from registry.
- [x] Stack license status + Side 1 renew link.
- [x] Unified ops entities (events + audit + policies) feed more than one UI surface.
- [x] `choruscontrol doctor` (mother and agent modes).
- [x] Six UI tabs + §3.10 / fleet / latency tests pass in CI.
- [x] Iterations deliver connected platform value (no orphan features).

**North-star:** organizations manage AI like cloud infrastructure — observable, governed, secure, versioned, measurable, auditable, continuously improving — with ChorusControl as the single source of truth for enterprise AI operations on the Prism stack.

---

### 8. Traceability

#### 8.1 Original PDF gaps

| Spec “gap solved” | Implemented via |
|-------------------|-----------------|
| Opaque multi-agent failures | Trace wire + zero-token replay (§3.7.2) |
| Silent RAG decay / category bleed | Taxonomy + partitions + reindex (§3.7.3, §3.13) |
| Unverifiable agent memory | Memory APIs + sleep + cascade (§3.7.4, §3.11) |
| Probabilistic security risks | Guard Policy Studio + logs (§3.7.5) |
| Cross-fleet invalidation | Invalidation bus + cascade + agent command (§3.4, §3.11, §3.19) |
| Mutex / async maintenance | Job queue (§3.5) |
| Cryptographic audit | Audit pipeline + SOC2 pack (§3.6, §3.18) |

#### 8.2 Product upgrade register

| ID | Upgrade | Section | Priority |
|----|---------|---------|----------|
| U1 | Correction Cascade | §3.11 | P0 |
| U2 | Honest Capability Caps | §3.12 | P0 |
| U3 | Real Token-Tax & Driver metrics | §3.7.1 | P0 |
| U4 | Guard Policy Studio | §3.7.5 | P0 |
| U5 | Trace Guard→Ledger→Shine | §3.7.2 | P0 |
| U6 | Warm-chunk / partition ops | §3.13 | P1 |
| U7 | Fleet GREEN/BLUE/ORANGE | §3.14 | P1 |
| U8 | Cortex API proxy | §3.15 | P1 |
| U9 | Stack license status | §3.16 | P1 |
| U10 | Doctor CLI | §3.17 | P2 |
| U11 | Demo mode | §3.17 | P2 |
| U12 | OpenAPI + ai-overview | §3.17 | P2 |
| U13 | SOC2 export pack | §3.18 | P2 |
| U14 | InsightPlugIn SMS ops | deferred | — |
| U15 | Fleet agent + Fabric/PrismAPI discovery + handshake | §3.19 | P0 |
| U16 | Zero hot-path latency + async ledger export | §3.19.6a–c | P0 |
| **U17** | **Enterprise AI OS positioning + implementation strategy** | **§1.1, §10** | **P0** |
| **U18** | **Unified ops data model + connected platform services** | **§10.3–§10.4** | **P1** |
| **U19** | **Intelligence layer (AI Score, predictive, recommendations)** | **§10.5, §11.8–§11.9** | **P2** |
| **U20** | **Vision, pillars, lifecycle, trust philosophy** | **§11.1–§11.4** | **P0** |
| **U21** | **Enterprise AI Asset Graph** | **§11.5** | **P1** |
| **U22** | **AI Operations Assistant** | **§11.6** | **P2** |
| **U23** | **Exec/Eng UX, version/incident intelligence, policy engine** | **§11.7–§11.12** | **P1–P2** |

---

### 9. Remaining gaps (shipping — not architecture)

Canonical checklist: [ChorusControl-Shipping-Gaps.md](./ChorusControl-Shipping-Gaps.md).

| ID | Severity | Gap | Owner |
|----|----------|-----|-------|
| S01 | Critical | Product code not started (docs only) | This repo |
| S02 | High | Side 1 portal / license issuance | Future insightits.com agent |
| S03 | High | Zero-latency agent path not load-proven | This repo (CI) |
| S04 | High | Adapters not validated against live package pins | This repo |
| S05 | Low | InsightPlugIn, VectorBridge, ChorusMesh deep alerts | Deferred / out of v1 |
| S06 | Medium | Intelligence layer / marketplace not in v1 ship | Staged per §10–§11 |
| S07 | Medium | Asset Graph / Assistant / full AI Score not in first slice | Staged Phase 3–6 |

Complete file: [ChorusControl-COMPLETE-DESIGN.md](./ChorusControl-COMPLETE-DESIGN.md).

---

### 10. Implementation Strategy — AI Operations Platform

ChorusControl is a **unified Enterprise AI Operating System / AI Operations Platform**, not a collection of independent modules. Every capability in §10–§11 is part of the long-term product vision. Prioritize customer value while keeping one cohesive architecture.

#### 10.1 Guiding principles

| Principle | Meaning |
|-----------|---------|
| **Build once** | Extensible from day one; adapters + versioned schemas; no throwaway stubs |
| **Platform first** | Every feature integrates; no orphan widgets |
| **Everything connected** | Subsystems feed the Asset Graph and each other |
| **AI native** | Operational workflows enhanced by AI reasoning (Ops Assistant) — without replacing dashboards |
| **Design for scale** | Thousands of agents, multi-org, hybrid, multi-cloud, multi-provider, future Prism products |
| **Enterprise ready** | Multi-tenancy, RBAC, HA, auditability, hybrid deployment |
| **Incremental delivery** | Each iteration ships usable, connected platform value |

Platform-first checklist:

- Every **agent** participates in governance (inventory, policy, audit).
- Every **deployment** is versioned (packages, partitions, prompts, policies, eval results).
- Every **policy** is auditable (Ed25519 envelopes).
- Every **incident** is traceable (Guard → Ledger → Shine → cascade ids → Asset Graph links).
- Every **evaluation** contributes to organizational health (metrics → AI Score).

Connected flows:

```
PrismGuard  →  Security Events  →  Incident Intelligence  →  Executive / Compliance
PrismRAG    →  Knowledge Metrics  →  AI Score / Recommendations (staged)
PrismCortex →  MemoryEvents       →  Correction Cascade → Invalidate / Shine
ChorusGraph →  Route Ledger       →  Trace / Replay / Engineering UX
PrismCache  →  Token-tax metrics  →  Cost / Overview / AI Score
Fabric      →  Heartbeats/commands→  Fleet / Asset Graph nodes
```

#### 10.2 Hybrid development order (normative)

| Phase | Name | Delivers |
|-------|------|----------|
| **1** | Foundation + runtime touch | Orgs/tenants, users, auth, license, mother, agent join, health + **live Prism signal** |
| **2** | Core runtime integration | Prism adapters; caps; invalidate; Trace feed |
| **3** | Unified data model + **Asset Graph v1** | Assets/events/metrics/logs/audit/policies + relationship edges (§11.5) |
| **4** | Platform services | Monitoring, versioning, evaluation, governance, **incident intelligence** |
| **5** | Intelligence layer | Transparent **AI Score**, predictive analytics, recommendations, compliance automation |
| **6** | AI Ops Assistant + enterprise | Assistant (analyze + gated execute), exec/eng experiences, fleet at scale; **Marketplace via Side 1** |

**Phase 1 rule:** no CRM-only milestone.  
**Phase 5 rule:** no fake scores.  
**Phase 6 rule:** Assistant executes only via existing RBAC + audit + confirmation for destructive actions.

#### 10.3 Unified data model (platform nouns)

| Entity | Examples | Produced by |
|--------|----------|-------------|
| Organization / Tenant | License `sub`, tenant matrix | Auth + license |
| Project | App grouping under tenant | Foundation |
| Agent / Node | Fleet registry entry, role, zone | Agent heartbeat |
| Asset (graph node) | Workflow, prompt, KB, memory, model, tool, API, deployment | Probe + adapters + versioning |
| Edge | depends_on, uses_policy, deployed_as, impacted_by | Asset Graph |
| Event | Security, ledger hop, MemoryEvent, cascade, incident | Guard, Graph, Cortex, cascade |
| Metric | Hit rate, tokens, Driver latency, chunk health, cost | Cache, Driver, RAG |
| Log | Structured app logs | Agent export |
| Audit record | Signed admin / cascade / Assistant action | Audit pipeline |
| Policy | Multi-domain enterprise policies | Policy engine |

#### 10.4 Platform services (connected)

| Service | Role | Feeds |
|---------|------|-------|
| Monitoring | Health matrix, caps, fleet liveness | Overview / Exec |
| Versioning | Packages, partitions, prompts, policies, evals | Version intelligence |
| Evaluation | Replay, cold audit, eval history | Trace, Eng UX, AI Score |
| Governance | RBAC, license features, policy engine | All writes |
| Incident intelligence | Timeline, RCA, impact, graph-linked assets | Overview, Assistant |
| Asset Graph | Relationship source of truth | Assistant, incidents, blast radius |

#### 10.5 Intelligence layer (staged — no fake scores)

| Capability | Prerequisite | Notes |
|------------|--------------|-------|
| AI Score | Stable metrics + events + caps | Transparent multi-dimension KPI |
| Predictive analytics | Time-series retention | Failure, staleness, cost, capacity, degradation |
| Recommendations | Caps + incidents + metrics + graph | Actionable ops suggestions |
| Compliance automation | Audit + caps + policy history | Extends SOC2 pack |
| Root cause analysis | Version diffs + incidents + ledger | Auto-correlate regressions |

#### 10.6 Definition of success

Organizations no longer manage only individual agents — they manage an **intelligent AI organization**.

ChorusControl is the trusted operational layer for governance, visibility, security, intelligence, lifecycle, and continuous improvement — making enterprise AI as manageable and trustworthy as modern cloud infrastructure.

---

### 11. Product Vision Enhancements — Enterprise AI Operating System

Normative long-term vision. Capabilities are **staged** (§10.2); architecture must not block them.

#### 11.1 Vision statement

Enterprise AI is becoming enterprise infrastructure. Organizations move from a handful of assistants to hundreds or thousands of agents, workflows, knowledge bases, models, and AI services.

That requires more than observability: governance, operational intelligence, security, lifecycle management, explainability, and enterprise-wide visibility.

**ChorusControl is the Enterprise AI Operations Platform designed to become the operating system for enterprise AI.**

It does **not** replace AI frameworks or language models. It provides the **enterprise management layer above them**.

#### 11.2 Mission capabilities

| Verb | Platform support |
|------|------------------|
| Deploy | Fleet agent join, policy push, jobs, versioned deployments |
| Observe | Metrics, events, traces, logs, caps, Overview |
| Govern | RBAC, enterprise policy engine, license features, approvals |
| Secure | PrismGuard, shadow/enforce, risk analytics |
| Evaluate | Replay, cold audit, eval history, version compare |
| Improve | Cascade, recommendations, predictive alerts, Assistant actions |
| Audit | Ed25519 audit trail, SOC2 pack, compliance automation |
| Scale | Multi-tenant, hybrid zones, thousands of nodes, multi-provider |

#### 11.3 Six product pillars

| Pillar | Capabilities |
|--------|----------------|
| **Governance** | Policies, permissions, identity, audit, compliance |
| **Observability** | Metrics, events, traces, logs, runtime monitoring |
| **Security** | Prompt security, guardrails, threat detection, risk analytics |
| **Operations** | Fleet, deployments, versioning, incidents |
| **Intelligence** | AI Score, recommendations, predictive analytics, RCA |
| **Ecosystem** | Prism integrations, external providers, enterprise systems, multi-cloud |

UI tabs map into pillars (not 1:1): Overview→Observability+Intelligence; Trace→Observability; Taxonomy→Operations; Memory→Operations; Guard→Security+Governance; Admin→Governance+Ecosystem.

#### 11.4 Enterprise AI lifecycle

```text
Develop → Deploy → Observe → Govern → Evaluate → Improve → Audit → Scale
```

v1 emphasizes Deploy/Observe/Govern/Secure/Audit; Evaluate/Improve/Intelligence deepen in Phases 4–6.

#### 11.5 Enterprise AI Asset Graph

Everything in the AI ecosystem is a **connected asset**. The graph is a source of truth for dependency and blast-radius questions.

```text
Organization → Project → Agent/Node
  → Workflow → Prompt → Knowledge Base → Memory → Model
  → Policies → Tools → External APIs → Deployments → Incidents
```

**Must answer:** What depends on this KB? Which deployments use this prompt? Which agents does this policy hit? What fails if this API is down?

**Build notes:** Phase 3 nodes/edges from fleet, tenants, policies, partitions; enrich from ledger/Cortex/RAG; Postgres asset/edge tables; version mutable assets; power Overview blast radius, incidents, Assistant.

#### 11.6 AI Operations Assistant

Native assistant with Asset Graph + subsystem visibility. Primary ops interface for admins/devs/execs **alongside** dashboards (never a replacement).

Example asks: Why did Finance Agent fail? Prompt-changing deployments? Noisiest policies? Costliest systems? Explain incident. Compare deploy 42 vs 41. Stale knowledge? Upgrade Marketing agents. Compliance report. Review architecture.

**Gated execution:** rollback, model upgrade, rebuild indexes, assign policies, reports, open incidents, trigger evals — via same APIs as UI, RBAC + audit + confirm destructive ops. Feature `assistant.ops`. Ground in graph + telemetry; no invented world-truth.

#### 11.7 Executive vs engineering experience

| Audience | Focus |
|----------|--------|
| **Executive** | AI Score, agents, cost, critical incidents, compliance, security, failures, knowledge health, drift — business impact |
| **Engineering** | Execution graph, tool/memory timelines, prompt diff, version compare, token/retrieval analytics, replay, failure analysis, eval history |

#### 11.8 AI Score

Continuous org/tenant KPI. Dimensions e.g. Security, Governance, Reliability, Performance, Cost Efficiency, Knowledge Quality, Compliance, Operational Health. Transparent formula; inputs from real telemetry only (Phase 5+).

#### 11.9 Predictive intelligence

Failure prediction, knowledge staleness, cost/capacity forecasting, prompt/retrieval degradation, security risk prediction — proactive recommendations (Phase 5+).

#### 11.10 AI version intelligence

Version every deployment; compare prompts, models, policies, knowledge, memory config, eval/benchmarks; RCA correlates regressions with diffs (Phase 4–5).

#### 11.11 Enterprise policy engine

Multi-domain policies (data access, security, compliance, memory, models, APIs/tools, human/deployment approval) — versioned, auditable, enforceable beyond Guard-only studio.

#### 11.12 Incident intelligence

Timeline, RCA, AI summary, impact, suggested resolution, related deployments/policies/KB/models (graph links). Rapid diagnosis over log spelunking.

#### 11.13 Ecosystem integration

Operational center of Prism: ChorusGraph, Guard, RAG, Cortex, Shine, Resonance, PrismLang, PrismAPI, Fabric — continuous telemetry via adapters + agents, zero hot-path tax.

#### 11.14 Long-term vision

Manage an **intelligent AI organization**, not isolated agents. Trusted layer for governance, visibility, security, intelligence, lifecycle, continuous improvement.

#### 11.15 Vision → ship staging

| Capability | Earliest phase |
|------------|----------------|
| Pillars / lifecycle / trust framing in product | 1 |
| Asset Graph v1 | 3 |
| Incident + version intelligence | 4–5 |
| Enterprise policy engine (multi-domain) | 4 |
| AI Score + predictive | 5 |
| Exec / eng experiences | 4–5 |
| AI Ops Assistant | 6 |
| Marketplace | Side 1 / late 6 |

---

*End of document — Insight IT Solutions LLC / ChorusControl Design Gaps & Solutions v1.7.0 — Enterprise AI Operating System*


# Part C — Side 1 Handoff (www.insightits.com)

| Field | Value |
|-------|-------|
| Audience | Future Cursor / engineering agent working on **www.insightits.com** |
| Status | Deferred — do **not** implement in the ChorusControl repo |
| Owner (today) | ChorusControl team defines the **contract**; website team implements later |
| Companion | [ChorusControl-Design-Gaps-and-Solutions.md](./ChorusControl-Design-Gaps-and-Solutions.md) · [ChorusControl-COMPLETE-DESIGN.md](./ChorusControl-COMPLETE-DESIGN.md) |
| Version | 1.1.0 |
| Date | July 2026 |

---

### 1. Why this handoff exists

**ChorusControl** is the self-hosted **Enterprise AI Operating System / AI Operations Platform** (Side 2). **www.insightits.com** is the commercial portal (Side 1).

ChorusControl is a **two-sided** product family:

| Side | Repo / surface | Responsibility |
|------|----------------|----------------|
| **Side 2** | `ChorusControl` (this project) | Self-hosted **AI Operations Platform** — mother + agents in customer VPC |
| **Side 1** | **www.insightits.com** (separate) | Commercial portal: sell, support, and **issue** offline licenses |

Side 2 is built **now** in this folder. Side 1 is a **future handoff** to the insightits.com agent. The two sides must agree on a stable interface so license keys issued on the website validate offline inside ChorusControl with **zero phone-home**.

---

### 2. What the insightits.com agent will build (later)

When handed this brief, implement on the **website / portal** stack (not inside ChorusControl):

1. **Customer accounts** — org identity tied to `sub` / customer id in license claims.
2. **Stripe billing** — plans mapped to ChorusControl `tier` and feature entitlements.
3. **License issuance** — Ed25519-signed offline JWT (or compact JWS) matching the claim schema below; private key stays on Side 1 only.
4. **License delivery UX** — customer can copy/download the key to paste into ChorusControl Admin → License.
5. **Support ticketing** — hosted tickets; ChorusControl only deep-links here.
6. **Optional** — license history, renewals, seat/node upgrades that re-issue JWTs with updated `max_nodes` / `exp` / `features`.

**Do not** implement: Prism fleet control, Cortex sleep, RAG taxonomy UI, Guard WAF console, or audit sinks. Those belong exclusively to Side 2.

---

### 3. Stable contract Side 2 already depends on

The ChorusControl product will verify licenses using this contract. Side 1 **must** issue keys that satisfy it.

#### 3.1 Environment / UX touchpoints on Side 2

| Touchpoint | Side 2 behavior | Side 1 must provide |
|------------|-----------------|---------------------|
| License key | Customer pastes into Admin or sets `CHORUSCONTROL_LICENSE_KEY` | Issuance + download/copy UI |
| Support link | `INSIGHTITS_SUPPORT_URL` (default `https://www.insightits.com/support`) | Working support entry URL |
| Account / billing link (optional) | Configurable portal URL | Customer billing page |

#### 3.2 Cryptography

- Algorithm: **Ed25519**
- Side 1 holds the **private** signing key (HSM or secrets manager recommended).
- Side 2 embeds / ships the matching **public** key (via `chorusmesh.license` or equivalent adapter).
- Validation is **100% offline** — no callback to insightits.com at verify time.

#### 3.3 License claims schema (must match Side 2)

```json
{
  "iss": "insightits.com",
  "sub": "customer-or-org-id",
  "iat": 1720000000,
  "exp": 1751536000,
  "tier": "enterprise",
  "max_nodes": 16,
  "max_tenants": 50,
  "features": ["trace.replay", "guard.shadow", "audit.export"],
  "license_id": "lic_..."
}
```

| Claim | Rules |
|-------|--------|
| `iss` | Constant issuer string Side 2 expects (`insightits.com`) |
| `sub` | Stable customer/org id |
| `exp` | Unix seconds; Side 2 enters **14-day read-only grace** after expiry, then fail-closes |
| `tier` | One of `starter` \| `enterprise` \| `sovereign` |
| `max_nodes` | Enforced against Fabric peer / worker registration |
| `max_tenants` | Enforced on tenant create in ChorusControl |
| `features` | Feature flags; unknown flags ignored by older Side 2 builds |
| `license_id` | Unique id for support / revocation *records on Side 1* (Side 2 does not phone home to revoke) |

**Revocation note:** True online revocation requires phone-home or short `exp` + re-issue. Prefer short-lived renewals or documented air-gap policy; do not assume Side 2 can check a CRL at runtime.

#### 3.4 Tier → feature mapping (recommended default)

| Tier | Suggested features |
|------|--------------------|
| `starter` | Core UI, sleep, basic taxonomy |
| `enterprise` | + `trace.replay`, `guard.shadow`, `audit.export` |
| `sovereign` | All enterprise + air-gap support SLAs (commercial only) |

Side 1 billing products should map 1:1 to these tiers so Stripe plan changes produce correct JWTs.

---

### 4. What Side 2 delivers before handoff

The ChorusControl repo will ship:

- Offline verifier + middleware (fail-closed).
- Admin license status / upload UI.
- Deep link to support URL.
- Dev/test keypair workflow so Side 2 can be QA’d **before** the website issues production keys.
- This handoff brief kept in sync when claim schema changes (version bump + changelog entry).

---

### 5. Handoff checklist (when website work starts)

- [ ] Confirm Ed25519 key ceremony; publish public key into `chorusmesh.license` / Side 2 release.
- [ ] Implement issuer producing the claim schema in §3.3.
- [ ] Map Stripe products → `tier` / `max_nodes` / `features`.
- [ ] Customer “copy license key” UX.
- [ ] Support URL live at the configured default (or update Side 2 default).
- [ ] Cross-team test: key issued on insightits.com validates in ChorusControl with network disabled.
- [ ] Document renewal / upgrade re-issue flow for customers.

---

### 6. Non-goals / anti-patterns

- Do not put Stripe or ticket DB code into the ChorusControl container.
- Do not require ChorusControl to call insightits.com APIs to start.
- Do not change claim field names without a coordinated Side 2 version bump.
- Do not embed the **private** signing key in Side 2 images or this repo.

---

*Insight IT Solutions LLC — Side 1 handoff brief for www.insightits.com*


# Part D — Shipping Gaps (S01–S07)

| Field | Value |
|-------|-------|
| Status | **Side 2 shippable** — see [ChorusControl-Shipping-Gaps.md](./ChorusControl-Shipping-Gaps.md) |
| Design baseline | Gaps & Solutions v1.7.0 · Enterprise AI Operating System |
| Date | July 2026 |

Design gaps G01–G21 and upgrades U1–U23 are **resolved on paper**. Shipping:

| ID | Severity | Gap | Status |
|----|----------|-----|--------|
| **S01** | Critical | Product code | **Done** |
| **S02** | High | Side 1 portal | **Other agent** (handoff) |
| **S03** | High | Zero-latency proof | **Done** (CI harness) |
| **S04** | High | Sibling pin floors | **Done** (factory + doctor) |
| **S05** | Low | Deferred integrations | Deferred |
| **S06** | Medium | Marketplace | Side 1 |
| **S07** | Medium | Graph / Assistant / Score | **Done** (v1) |

### S01 — Implementation slices

- [x] `pyproject.toml` with `[server]` / `[agent]` extras  
- [x] Mother FastAPI `/healthz` `/readyz`  
- [x] License verifier + fail-closed middleware  
- [x] Auth / RBAC  
- [x] Fleet join tokens + registry + agent heartbeat  
- [x] Adapters + demo NullAdapters  
- [x] Job queue (sleep, reindex, warm, cascade)  
- [x] Invalidation + command dispatch  
- [x] Async ledger batch export  
- [x] Audit JSONL (+ Postgres optional)  
- [x] Six-tab APIs + UI  
- [x] `choruscontrol doctor`  
- [x] Docker / compose  

### S03 — Latency proof (acceptance)

```text
Baseline: ChorusGraph invoke (or Cortex digest/recall) without agent
Treatment: same + attach_agent() + mother reachable or unreachable
Pass: p50 delta within measurement noise; no await mother on request thread
Fail: any sync mother RPC on hot path
```

### S04 — Sibling pin matrix

| Package | Floor |
|---------|-------|
| chorusgraph | ≥1.3.0 |
| prismguard | ≥0.1.10 |
| prismcortex[prism-plus] | ≥0.3.0 |
| prismrag-patch | ≥0.2.1 |
| prismshine | ≥0.2.2 |
| prismlib-plus | ≥0.8.0 |
| chorus-fabric | ≥0.2.0 |
| prismlang | ≥0.1.2 |
| prismresonance | ≥0.3.0 |
| chorusmesh | ≥0.1.0 |

### S02 / S05 — Explicit non-blocking

| Item | Owner |
|------|--------|
| Stripe / license issuance / support portal | Side 1 handoff — **other agent** |
| InsightPlugIn SMS master commands | Deferred |
| VectorBridge | Out of scope |
| ChorusMesh Slack/PD as alert channel | Optional post-v1 |

### Relationship to design gaps

| Design | Shipping |
|--------|----------|
| G01–G21 closed in docs | S01 implements them |
| U1–U16 specified | S01–S04 prove them |
| Side 1 handoff written | S02 executes later elsewhere |

*Close S01+S03+S04 in this repo to call Side 2 shippable — **done**.*


# Part E — Implementation Readiness & Ecosystem

| Field | Value |
|-------|-------|
| Product | ChorusControl — AI Operations Platform (Side 2 — **this repo**) |
| Portal | www.insightits.com (Side 1 — **future handoff**) |
| Version | 1.2.0 |
| Date | July 2026 |
| Inputs | Architecture Spec PDF · Design Gaps & Solutions v1.6.0 · Insight ITS READMEs |
| Companions | [ChorusControl-COMPLETE-DESIGN.md](./ChorusControl-COMPLETE-DESIGN.md) · [ChorusControl-Design-Gaps-and-Solutions.md](./ChorusControl-Design-Gaps-and-Solutions.md) · [Side1-insightits-com-Handoff.md](./Side1-insightits-com-Handoff.md) |

> **Note:** Platform strategy (AI Operations Platform, Implementation Strategy §10) lives in the complete / gaps docs. This file is a short readiness summary.

---

### 1. Ownership — locked

| Side | Location | Builds now? | Responsibility |
|------|----------|-------------|----------------|
| **Side 2 — Main product** | **This folder / `ChorusControl` repo** | **Yes** | Self-hosted **AI Operations Platform** (mother + agents) beside ChorusGraph workers |
| **Side 1 — Commercial portal** | **www.insightits.com** (separate) | **Later handoff** | Stripe, support tickets, license *issuance* |

**Contract between sides:** offline signed license JWT + deep links. Side 2 never phones home to validate.

We are clear: **implement the product here; hand the website agent the Side 1 brief when ready.**

---

### 2. Do we have enough design to implement?

**Yes — for an MVP that matches the PDF**, if we treat [ChorusControl-Design-Gaps-and-Solutions.md](./ChorusControl-Design-Gaps-and-Solutions.md) as the build bible.

| Area | Ready? | Notes |
|------|--------|-------|
| Scope / Side split | ✅ | Locked above + handoff brief |
| License verify + claims | ✅ | Schema + middleware + fail-closed |
| Auth / RBAC | ✅ | Roles + local token; OIDC optional |
| Job queue (sleep + reindex) | ✅ | Per-tenant mutex |
| Invalidation bus | ✅ | Matches real `invalidate_tags` / `invalidate_where` |
| Audit JSONL + Postgres | ✅ | Ed25519 + export |
| Six-tab API map | ✅ | Enough to scaffold routes |
| Adapters / NullAdapters | ✅ | Prevents hard-wiring to unstable internals |
| Packaging | ✅ | Docker, env, health/ready |
| Test matrix | ✅ | Kernels + RBAC + health |

**Still thin (design enough to start; flesh during build):**

| Thin spot | Why it’s OK to start | What to lock in sprint 0 |
|-----------|----------------------|---------------------------|
| Exact sibling public APIs | READMEs give real entry points | Adapter interfaces + version pins below |
| Live wire / WS protocol | Ledger + Guard + Shine shapes are known | Trace event JSON schema |
| UI wireframes | Tab features are specified | One HTML shell + Chart.js panels |
| Unified multi-product license UX | ChorusMesh / Guard / Cortex have own keys | Status panel first; issuance stays Side 1 |

**Verdict:** Design is **implementation-ready** for Side 2. Do not block on Side 1. Do not invent new science — **wrap the stack you already ship**.

---

### 3. Ecosystem map (what ChorusControl actually orchestrates)

```
                    ┌──────────────────────────────┐
                    │     ChorusControl (Side 2)   │
                    │  observe · admin · invalidate │
                    │  sleep · license · audit      │
                    └──────────────┬───────────────┘
                                   │ Fabric SIGNAL / PrismAPI
         ┌─────────────────────────┼─────────────────────────┐
         ▼                         ▼                         ▼
   ChorusGraph               Prism Pack                 Data plane
   native Graph              Guard · Shine              PrismCache
   Route Ledger              Cortex · RAG               PrismDriver
   interceptors              Resonance sleep            ClusterCache
   mark_revalidate           PrismLang 64-d             BLUE/GREEN/ORANGE
```

| Product | Role for ChorusControl |
|---------|------------------------|
| **ChorusGraph** | Fleet runtime; Route Ledger; dogfood; `mark_revalidate`; health |
| **PrismGuard** | WAF tab — `resolution_gate`, profiles, shadow ONNX, lexicon |
| **PrismShine** | Trace/output — `ShineVerdict`, Tier-0 cause, consistency |
| **PrismCortex** | Memory tab — bitemporal facts, conflicts, `sleep()`, `on_event` |
| **PrismRAG** (`prismrag-patch`) | Taxonomy tab — mapping, category tree, chunk health |
| **PrismResonance** | Sleep passes 1–4 under Cortex consolidation |
| **PrismLang** | Overview token-tax / 64-d projection search substrate |
| **prismlib-plus** | Cache metrics, `invalidate_*`, PrismDriver latency, PrismAPI |
| **CHORUS Fabric** | Invalidation + health SIGNAL frames |
| **ChorusMesh** | License pattern / `license.py` public key; optional Slack alerts later |
| **VectorBridge** | Out of v1 scope (migration tool, not control plane) |
| **InsightPlugIn** | Out of scope (IDE SMS) |

---

### 4. Dependency floors (align with shipped products)

```
chorusgraph>=1.3.0
prismguard>=0.1.10
prismcortex[prism-plus]>=0.3.0
prismrag-patch>=0.2.1
prismshine>=0.2.2
prismlib-plus>=0.8.0
chorus-fabric>=0.2.0
prismlang>=0.1.2
prismresonance>=0.3.0
## license public key source (adapter):
chorusmesh>=0.1.0   # or vendored chorusmesh.license public PEM
```

**Packaging rules from sibling READMEs (must follow):**

- Cortex: use `[prism-plus]` with ChorusGraph hosts — **never** mix `[prism]` + `[prism-plus]`.
- Guard ONNX weights are **not** in the wheel — document `prismguard-model download` for Guard tab enforce paths.
- Shine Tier-3 spans optional — Overview/capabilities must show honest `span_backend`.
- Prefer **adapters** over importing private modules.

---

### 5. Suggestions to make the product better

These are prioritized upgrades beyond “six tabs that call APIs.” They come directly from how your products already work together.

#### P0 — Build these; they are the moat

##### 5.1 Correction Cascade (Cortex → Cache → Graph → Shine)

Today the PDF says “admin edits → INVALIDATE_CACHE.” Your stack already has a richer loop:

1. Cortex `digest` correction / conflict resolve → `MemoryEvent` via `on_event`
2. PrismCache `invalidate_tags` / `invalidate_where(probe, threshold=…)`
3. ChorusGraph `mark_revalidate` → `force_refresh` until re-seed
4. PrismShine consistency: `CACHE_PREDATES_FACT_UPDATE`

**ChorusControl should own the cascade as a first-class action:**

- Auto-subscribe to Cortex events (in-process or Cortex HTTP) and broadcast Fabric invalidation.
- Admin UI: “Resolve conflict” runs resolve **and** shows cascade status (nodes acked, tags evicted).
- Audit one envelope for the whole cascade (`action: correction_cascade`).

This is stronger than a bare invalidate button and unique to Insight ITS.

##### 5.2 Honest Capability Caps (no fake green)

Mirror Guard’s `prismguard caps` and Shine’s `gate.capabilities()`:

- Overview panel: **what is actually enabled** per node — Guard profile, ONNX ready, taxonomy on/off, Shine span backend, Cortex ANN, Fabric peers, license features.
- Never show scorecard metrics when profile is `web_chat`.
- `GET /api/v1/health/caps` aggregates adapter `caps()` calls.

Enterprise buyers trust **truth tables** more than dashboards that lie.

##### 5.3 Real Token-Tax & Driver metrics (not decorative counters)

Wire Overview to real APIs:

| Metric | Source |
|--------|--------|
| Cache hit rate / tokens saved / $ | `PrismCache.get_metrics()` (prismlib-plus ≥0.8) |
| Evictions | `evicted_by_tags` / `evicted_by_vector` |
| Driver read latency | PrismDriver health / query stats |
| Token-tax (Lang hops) | PrismLang / ChorusGraph ledger fields when present |
| Cold savings estimate | Wrap `chorusgraph-audit` style simulation on uploaded query logs |

Fake counters would undermine the benchmark story you’ve already published.

##### 5.4 Guard Policy Studio (profile-aware)

Guard README is explicit: wrong profile destroys UX (law ONNX on finance FX).

Admin **Guard** tab should encode policy, not just logs:

| Mode | UI behavior |
|------|-------------|
| Ingress profile | `web_chat` / `light` / `heavy` / `domain_pilot` + domain slug |
| Shadow | Shadow ONNX observe-only; promote after benign-allow gate |
| Lexicon | Tenant lexicon editor (Business+ honesty in UI) |
| Caps verify | Button → show `prismrag_taxonomy`, `onnx_tier`, etc. |

Default **recommended** finance/hub policy card: ingress `web_chat` + optional shadow `light` (from Guard README).

##### 5.5 Trace = Guard → Ledger → Shine (one wire)

Execution Trace should stitch what you already emit:

```
resolution_gate (Guard)
    → Route Ledger hops (ChorusGraph) + rule_chain / kind/detail
    → ShineVerdict (decision, resolution_gate, evidence_hash)
```

- Live WS stream of ledger steps from dogfood / worker exporters.
- **Zero-token replay:** replay from ledger/cache only (no `call_llm`) — matches cold audit + Shine “PASS ≠ world-true” honesty banner.

#### P1 — Strong differentiators

##### 5.6 Warm-chunk / partition ops on Taxonomy tab

ChorusGraph ADR-005: `index(partition, version)`, `warm_retrieval`, `bump_partition_version`, `get_chunk_vectors`.

Taxonomy tab should show:

- Partition → version matrix per tenant
- “Bump version & warm” job (via maintenance queue)
- Chunk decay / category bleed heatmap from PrismRAG category_slug distribution

##### 5.7 Fleet topology (GREEN / BLUE / ORANGE)

PrismLib Micro already has roles and failover. Overview or Admin:

- Peer list with role, last HEALTH frame, hit contribution
- Invalidation ack coverage by node
- Optional later: deep-link ops to ChorusMesh Slack/PD (license-gated)

##### 5.8 Stack License Status Console

Customers may hold **multiple** offline keys (ChorusControl, ChorusMesh, Guard Team+, Cortex commercial). Admin should:

- Show status of each known key type (valid / exp / tier)
- Still **issue** none of them (Side 1)
- Deep-link “Get / renew license” → insightits.com

##### 5.9 Conflict & Explain deep links into Cortex

Prefer Cortex’s existing enterprise surfaces over reimplementation:

- Proxy or embed: `/conflicts`, `/conflicts/resolve`, `/explain`, `/recall_at`, replay certificate
- ChorusControl adds RBAC + audit + cascade — not a second memory engine

#### P2 — Nice polish

| Idea | Why |
|------|-----|
| **Doctor CLI** `choruscontrol doctor` | Like `prismguard doctor` — pins, Fabric, license, DB, ONNX presence |
| **OpenAPI + ai-overview.md** | Matches sibling repo pattern for Cursor agents |
| **Demo mode** | NullAdapters + synthetic ledger so UI works without full fleet |
| **Export pack** | SOC2 zip: audit JSONL + license claims (redacted) + caps snapshot |
| **InsightPlugIn hook** (optional later) | SMS “MASTER: sleep tenant X” — only if you want ops-from-phone; not v1 |

#### Explicit non-goals (keep the product sharp)

- Do **not** reimplement PrismRAG / Cortex / Guard inside ChorusControl.
- Do **not** put Stripe or license private keys in this repo.
- Do **not** require VectorBridge or InsightPlugIn for v1.
- Do **not** claim PASS/ALLOW means world-truth — reuse Shine/Guard honesty copy in UI.

---

### 6. Refined module checklist (build order)

Use this as the sprint board for **this repo**:

1. Scaffold — `pyproject.toml`, config, FastAPI, Docker, `/healthz` `/readyz`
2. License verifier + middleware (dev keypair for tests)
3. Auth / RBAC
4. Adapters + NullAdapters (graph, guard, shine, cortex, rag, cache, fabric, driver)
5. Job queue — sleep + reindex handlers
6. Invalidation broadcaster + **correction cascade** service
7. Audit async sinks (JSONL + optional Postgres)
8. APIs for six tabs + `/health/matrix` + `/health/caps`
9. UI shells (Tailwind + Chart.js)
10. Tests per verification matrix
11. `choruscontrol doctor` + demo mode
12. Freeze Side 1 claim schema; keep handoff doc current

---

### 7. Acceptance bar (product-quality)

Side 2 is “ready to sell beside the stack” when:

# Part E readiness checklist (embedded) — Side 2
- [x] Offline license fail-closed; zero phone-home
- [x] Six tabs backed by real adapter calls (or honest empty/demo states)
- [x] Correction cascade: conflict resolve → invalidate → mark_revalidate path tested
- [x] Overview metrics from PrismCache / Driver / caps — not placeholders
- [x] Guard tab cannot silently force law ONNX onto hub profiles
- [x] Trace shows Guard gate + ledger + Shine verdict; replay burns zero LLM tokens
- [x] Admin mutations audited (Ed25519) to JSONL (+ Postgres when configured)
- [x] Sleep/reindex never block digest/recall (load test or concurrent unit proof)
- [x] `doctor` reports sibling version floors
- [x] Side 1 handoff doc still accurate

---

### 8. Summary

| Question | Answer |
|----------|--------|
| Clear on two sides? | **Yes** — this repo = product; insightits.com = future handoff |
| Enough design to implement? | **Yes** — gaps doc + this readiness doc |
| Best upgrade over the PDF? | **Correction cascade + honest caps + real token/driver metrics + Guard policy studio** |
| Biggest risk? | UI that fakes health/savings or ignores Guard profile rules |

*Insight IT Solutions LLC — ChorusControl implementation readiness*

---

## Document control

| Change | Date | Notes |
|--------|------|-------|
| 1.5.0 | 2026-07-26 | Single-file merge |
| 1.6.0 | 2026-07-26 | AI Operations Platform + Implementation Strategy |
| 1.7.0 | 2026-07-26 | Enterprise AI OS vision; Asset Graph; Ops Assistant; pillars; lifecycle; U20–U23 |

**Canonical file:** `ChorusControl-COMPLETE-DESIGN.md`.

*Insight IT Solutions LLC — ChorusControl Complete Design Specification v1.7.0 — Enterprise AI Operating System*
