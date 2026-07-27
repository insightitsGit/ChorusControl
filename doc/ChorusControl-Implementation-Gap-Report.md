# ChorusControl — Implementation vs Design: Gap-Match Report

| Field | Value |
|-------|-------|
| Verifies | [ChorusControl-COMPLETE-DESIGN.md](./ChorusControl-COMPLETE-DESIGN.md) (Part B §3.x + §7) against the `choruscontrol/` implementation |
| Companion | [ChorusControl-Design-Review.md](./ChorusControl-Design-Review.md) (R01–R08, I01–I05) · [ChorusControl-Implementer-Handoff.md](./ChorusControl-Implementer-Handoff.md) |
| Test baseline | **34/34** passing (`pytest -q`) after WP1–WP12 |
| Date | July 2026 |

> **Verdict:** Side 2 implementer handoff WP1–WP12 closed. Enterprise depth WPs (Phases 3–6
> skeletons → real depth) shipped 2026-07-27 — see [ChorusControl-Enterprise-Depth.md](./ChorusControl-Enterprise-Depth.md).
> Remaining gaps are deliberate out-of-scope (Side 1 commercial, Fabric CI dual-backend,
> formal SOC2 certification, active-active HA, RBAC user CRUD UI, S05 deferred integrations).

---

## 1. Subsystem scorecard

Legend: ✅ implemented · ⚠️ partial · ❌ missing

| § | Subsystem | Status | Where / Notes |
|---|-----------|--------|---------------|
| 3.1 | Deployment boundary | ✅ | extras; no phone-home |
| 3.2 | Offline license protocol | ✅ | pinned Side 1 pubkey + grace + `require_feature`; optional 14d online validate; **no** non-demo auto-issue (HO-001) |
| 3.3 | Identity & RBAC | ✅ | local token + OIDC; user CRUD UI out of scope |
| 3.4 | Invalidation bus | ✅ | broadcaster + ACKs; Fabric live still optional stub |
| 3.5 | Maintenance job queue | ✅ | sleep/reindex/warm + `cascade.run` + `compliance.scan` |
| 3.6 | Cryptographic audit | ✅ | JSONL + Postgres dual-write + audit export |
| 3.7 | Control-plane APIs | ✅ | six tabs (+ Cortex) + tenants + stack licenses + license upload |
| 3.8 | Runtime / packaging | ✅ | multi-stage Dockerfiles; compose `--profile postgres` |
| 3.9 | Integration adapters | ✅ | Null + live pins; stack license parsers |
| 3.11 | Correction cascade | ✅ | job mutex + cascade.auto poll + CACHE_PREDATES_FACT_UPDATE |
| 3.12 | Honest caps | ✅ | |
| 3.13 | Warm-chunk / partitions | ✅ | warm job |
| 3.14 | Fleet topology | ✅ | GREEN/BLUE + `invalidation_coverage` + ledger drops |
| 3.15 | Cortex proxy | ✅ | conflicts/explain + `/cortex/*` activity/chunks + R04 addressing |
| 3.16 | Stack license status | ✅ | `GET /admin/stack-licenses` |
| 3.17 | Doctor / demo | ✅ | non-zero exit on hard failures |
| 3.18 | SOC2 export pack | ✅ | caps + PEM + redaction + feature gate + alias path |
| 3.19 | Fleet agent | ✅ | TLS external, WS live, REQUEST_METRICS/DRAIN/REVOKE/RUN_REINDEX + memory_endpoint |
| §11.5 | Asset Graph | ⚠️ | Enriched v1 (tenant/memory/incident/versions); not full Project/Workflow/Model ontology |
| §11.8 | AI Score | ⚠️ | Transparent formula + RAG staleness inputs; DEMO when NullAdapters |
| §11.11 | Enterprise policy | ⚠️ | 3 domains enforced; not full multi-domain OS |
| §11.12 | Incident intelligence | ⚠️ | Graph links + intelligence API + UI; no LLM summary |
| R05 | Mother durability | ⚠️ | Postgres control-plane dual-write + restore; not active-active HA |

## 2. Handoff WP status

| WP | Status |
|----|--------|
| WP1–WP12 | ✅ |
| Enterprise depth (see Enterprise-Depth.md) | ✅ Side 2 depth; GA blockers remain |

## 3. Deliberately remaining

- Side 1 (Stripe / issuance / portal) — commercial track
- Fabric dual-backend CI / live Fabric subscriber
- RBAC user-management UI
- S05 InsightPlugIn / VectorBridge / deep alerts
- Formal SOC2 certification / pen-test / support SLA — **new launch; do not rush**
- Active-active / multi-region mother HA — **future phase after go-live** → [ChorusControl-Future-Mother-HA.md](./ChorusControl-Future-Mother-HA.md)

---

*Insight IT Solutions LLC — gap report updated after enterprise depth pass*
