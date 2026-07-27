# ChorusControl — Implementation vs Design: Gap-Match Report

| Field | Value |
|-------|-------|
| Verifies | [ChorusControl-COMPLETE-DESIGN.md](./ChorusControl-COMPLETE-DESIGN.md) (Part B §3.x + §7) against the `choruscontrol/` implementation |
| Companion | [ChorusControl-Design-Review.md](./ChorusControl-Design-Review.md) (R01–R08, I01–I05) · [ChorusControl-Implementer-Handoff.md](./ChorusControl-Implementer-Handoff.md) |
| Test baseline | **34/34** passing (`pytest -q`) after WP1–WP12 |
| Date | July 2026 |

> **Verdict:** Side 2 implementer handoff WP1–WP12 closed. Remaining gaps are deliberate out-of-scope
> (Side 1, Fabric CI dual-backend, RBAC user CRUD UI, S05 deferred integrations).

---

## 1. Subsystem scorecard

Legend: ✅ implemented · ⚠️ partial · ❌ missing

| § | Subsystem | Status | Where / Notes |
|---|-----------|--------|---------------|
| 3.1 | Deployment boundary | ✅ | extras; no phone-home |
| 3.2 | Offline license protocol | ✅ | verify/grace/max_nodes/max_tenants + `require_feature` + upload store |
| 3.3 | Identity & RBAC | ✅ | local token + OIDC; user CRUD UI out of scope |
| 3.4 | Invalidation bus | ✅ | broadcaster + ACKs; Fabric live still optional stub |
| 3.5 | Maintenance job queue | ✅ | sleep/reindex/warm + `cascade.run` job |
| 3.6 | Cryptographic audit | ✅ | JSONL + Postgres dual-write + audit export |
| 3.7 | Control-plane APIs | ✅ | six tabs + tenants + stack licenses + license upload |
| 3.8 | Runtime / packaging | ✅ | multi-stage Dockerfiles; compose `--profile postgres` |
| 3.9 | Integration adapters | ✅ | Null + live pins; stack license parsers |
| 3.11 | Correction cascade | ✅ | job mutex + cascade.auto poll + CACHE_PREDATES_FACT_UPDATE |
| 3.12 | Honest caps | ✅ | |
| 3.13 | Warm-chunk / partitions | ✅ | warm job |
| 3.14 | Fleet topology | ✅ | GREEN/BLUE + `invalidation_coverage` + ledger drops |
| 3.15 | Cortex proxy | ✅ | conflicts/explain/recall_at |
| 3.16 | Stack license status | ✅ | `GET /admin/stack-licenses` |
| 3.17 | Doctor / demo | ✅ | non-zero exit on hard failures |
| 3.18 | SOC2 export pack | ✅ | caps + PEM + redaction + feature gate + alias path |
| 3.19 | Fleet agent | ✅ | TLS external, WS live, REQUEST_METRICS/DRAIN/REVOKE/RUN_REINDEX |

## 2. Handoff WP status

| WP | Status |
|----|--------|
| WP1 feature gates | ✅ |
| WP2 tenants / max_tenants | ✅ |
| WP3 TLS external | ✅ |
| WP4 SOC2 + audit export | ✅ |
| WP5 stack licenses | ✅ |
| WP6 license upload | ✅ |
| WP7 WS /fleet/live | ✅ |
| WP8 agent commands | ✅ |
| WP9 trace retention/sampling | ✅ |
| WP10 cascade completeness | ✅ |
| WP11 doctor exit + compose/Docker | ✅ |
| WP12 design-doc consistency | ✅ |

## 3. Deliberately remaining

- Side 1 (Stripe / issuance / portal)
- Fabric dual-backend CI / live Fabric subscriber
- RBAC user-management UI
- S05 InsightPlugIn / VectorBridge / deep alerts

---

*Insight IT Solutions LLC — gap report updated after implementer handoff close-out*
