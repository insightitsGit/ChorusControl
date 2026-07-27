# ChorusControl — Implementation Readiness & Product Recommendations

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

## 1. Ownership — locked

| Side | Location | Builds now? | Responsibility |
|------|----------|-------------|----------------|
| **Side 2 — Main product** | **This folder / `ChorusControl` repo** | **Yes** | Self-hosted **AI Operations Platform** (mother + agents) beside ChorusGraph workers |
| **Side 1 — Commercial portal** | **www.insightits.com** (separate) | **Later handoff** | Stripe, support tickets, license *issuance* |

**Contract between sides:** offline signed license JWT + deep links. Side 2 never phones home to validate.

We are clear: **implement the product here; hand the website agent the Side 1 brief when ready.**

---

## 2. Do we have enough design to implement?

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

## 3. Ecosystem map (what ChorusControl actually orchestrates)

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

## 4. Dependency floors (align with shipped products)

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
# license public key source (adapter):
chorusmesh>=0.1.0   # or vendored chorusmesh.license public PEM
```

**Packaging rules from sibling READMEs (must follow):**

- Cortex: use `[prism-plus]` with ChorusGraph hosts — **never** mix `[prism]` + `[prism-plus]`.
- Guard ONNX weights are **not** in the wheel — document `prismguard-model download` for Guard tab enforce paths.
- Shine Tier-3 spans optional — Overview/capabilities must show honest `span_backend`.
- Prefer **adapters** over importing private modules.

---

## 5. Suggestions to make the product better

These are prioritized upgrades beyond “six tabs that call APIs.” They come directly from how your products already work together.

### P0 — Build these; they are the moat

#### 5.1 Correction Cascade (Cortex → Cache → Graph → Shine)

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

#### 5.2 Honest Capability Caps (no fake green)

Mirror Guard’s `prismguard caps` and Shine’s `gate.capabilities()`:

- Overview panel: **what is actually enabled** per node — Guard profile, ONNX ready, taxonomy on/off, Shine span backend, Cortex ANN, Fabric peers, license features.
- Never show scorecard metrics when profile is `web_chat`.
- `GET /api/v1/health/caps` aggregates adapter `caps()` calls.

Enterprise buyers trust **truth tables** more than dashboards that lie.

#### 5.3 Real Token-Tax & Driver metrics (not decorative counters)

Wire Overview to real APIs:

| Metric | Source |
|--------|--------|
| Cache hit rate / tokens saved / $ | `PrismCache.get_metrics()` (prismlib-plus ≥0.8) |
| Evictions | `evicted_by_tags` / `evicted_by_vector` |
| Driver read latency | PrismDriver health / query stats |
| Token-tax (Lang hops) | PrismLang / ChorusGraph ledger fields when present |
| Cold savings estimate | Wrap `chorusgraph-audit` style simulation on uploaded query logs |

Fake counters would undermine the benchmark story you’ve already published.

#### 5.4 Guard Policy Studio (profile-aware)

Guard README is explicit: wrong profile destroys UX (law ONNX on finance FX).

Admin **Guard** tab should encode policy, not just logs:

| Mode | UI behavior |
|------|-------------|
| Ingress profile | `web_chat` / `light` / `heavy` / `domain_pilot` + domain slug |
| Shadow | Shadow ONNX observe-only; promote after benign-allow gate |
| Lexicon | Tenant lexicon editor (Business+ honesty in UI) |
| Caps verify | Button → show `prismrag_taxonomy`, `onnx_tier`, etc. |

Default **recommended** finance/hub policy card: ingress `web_chat` + optional shadow `light` (from Guard README).

#### 5.5 Trace = Guard → Ledger → Shine (one wire)

Execution Trace should stitch what you already emit:

```
resolution_gate (Guard)
    → Route Ledger hops (ChorusGraph) + rule_chain / kind/detail
    → ShineVerdict (decision, resolution_gate, evidence_hash)
```

- Live WS stream of ledger steps from dogfood / worker exporters.
- **Zero-token replay:** replay from ledger/cache only (no `call_llm`) — matches cold audit + Shine “PASS ≠ world-true” honesty banner.

### P1 — Strong differentiators

#### 5.6 Warm-chunk / partition ops on Taxonomy tab

ChorusGraph ADR-005: `index(partition, version)`, `warm_retrieval`, `bump_partition_version`, `get_chunk_vectors`.

Taxonomy tab should show:

- Partition → version matrix per tenant
- “Bump version & warm” job (via maintenance queue)
- Chunk decay / category bleed heatmap from PrismRAG category_slug distribution

#### 5.7 Fleet topology (GREEN / BLUE / ORANGE)

PrismLib Micro already has roles and failover. Overview or Admin:

- Peer list with role, last HEALTH frame, hit contribution
- Invalidation ack coverage by node
- Optional later: deep-link ops to ChorusMesh Slack/PD (license-gated)

#### 5.8 Stack License Status Console

Customers may hold **multiple** offline keys (ChorusControl, ChorusMesh, Guard Team+, Cortex commercial). Admin should:

- Show status of each known key type (valid / exp / tier)
- Still **issue** none of them (Side 1)
- Deep-link “Get / renew license” → insightits.com

#### 5.9 Conflict & Explain deep links into Cortex

Prefer Cortex’s existing enterprise surfaces over reimplementation:

- Proxy or embed: `/conflicts`, `/conflicts/resolve`, `/explain`, `/recall_at`, replay certificate
- ChorusControl adds RBAC + audit + cascade — not a second memory engine

### P2 — Nice polish

| Idea | Why |
|------|-----|
| **Doctor CLI** `choruscontrol doctor` | Like `prismguard doctor` — pins, Fabric, license, DB, ONNX presence |
| **OpenAPI + ai-overview.md** | Matches sibling repo pattern for Cursor agents |
| **Demo mode** | NullAdapters + synthetic ledger so UI works without full fleet |
| **Export pack** | SOC2 zip: audit JSONL + license claims (redacted) + caps snapshot |
| **InsightPlugIn hook** (optional later) | SMS “MASTER: sleep tenant X” — only if you want ops-from-phone; not v1 |

### Explicit non-goals (keep the product sharp)

- Do **not** reimplement PrismRAG / Cortex / Guard inside ChorusControl.
- Do **not** put Stripe or license private keys in this repo.
- Do **not** require VectorBridge or InsightPlugIn for v1.
- Do **not** claim PASS/ALLOW means world-truth — reuse Shine/Guard honesty copy in UI.

---

## 6. Refined module checklist (build order)

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

## 7. Acceptance bar (product-quality)

Side 2 is “ready to sell beside the stack” when:

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

## 8. Summary

| Question | Answer |
|----------|--------|
| Clear on two sides? | **Yes** — this repo = product; insightits.com = future handoff |
| Enough design to implement? | **Yes** — gaps doc + this readiness doc |
| Best upgrade over the PDF? | **Correction cascade + honest caps + real token/driver metrics + Guard policy studio** |
| Biggest risk? | UI that fakes health/savings or ignores Guard profile rules |

*Insight IT Solutions LLC — ChorusControl implementation readiness*
