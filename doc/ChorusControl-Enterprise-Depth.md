# ChorusControl — Enterprise Depth Progress (Phases 3–6)

| Field | Value |
|-------|-------|
| Date | 2026-07-27 |
| Scope | Side 2 only (this repo) |
| Companion | [ChorusControl-COMPLETE-DESIGN.md](./ChorusControl-COMPLETE-DESIGN.md) §10–§11 · [ChorusControl-Implementation-Gap-Report.md](./ChorusControl-Implementation-Gap-Report.md) |

> **Honest posture:** Phases 1–2 remain the solid control plane. This update ships **real** Phase 3–6 depth (not DEMO theater): Asset Graph enrichment, incident intelligence, multi-domain policies, version diffs, Score inputs from RAG, Cortex addressing, Postgres control-plane durability, compliance findings, Exec/Eng view modes. Still **not** enterprise GA — Side 1 commercial loop, formal SOC2, pen-test, and multi-mother HA are out of band.

## Shipped in this pass

| WP | Status | Notes |
|----|--------|-------|
| WP-D1 Mother durability | ✅ | Postgres DDL for nodes/join_tokens/cascades/acks/assets; dual-write; restore into empty SQLite |
| WP-R04 Cortex addressing | ✅ | Agent advertises `CHORUSCONTROL_MEMORY_ENDPOINT` or `local://` for memory/cortex roles; snapshot resolves + HTTP proxies |
| WP-G1 Graph enrichment | ✅ | tenant/memory/incident assets, `asset_versions`, cascade→graph links |
| WP-I1 Incident intelligence | ✅ | `PATCH` state, `/intelligence`, Admin+Overview lists, cascade asset binding |
| WP-S1 Score de-demo | ✅ | `knowledge_quality` from RAG staleness; `inputs` on score payload; honest `demo` flag |
| WP-V1 Version diff | ✅ | `/fleet/version-diff`, deployment snapshots, Eng panel |
| WP-P1 Multi-domain policy | ✅ | `memory.write` / `model.allowlist` / `deployment.approval` + enforce on assistant execute |
| WP-A1 Assistant execute | ✅ | `incident.create`, `guard.policy.put`, `traces.replay`, `compliance.scan` |
| WP-U1 Exec/Eng modes | ✅ | Overview `ops` / `exec` / `eng` toggle |
| WP-E1 Cold-audit honesty | ✅ | No invented 0.7 hit rate |
| WP-C1 Compliance findings | ✅ | `/compliance/scan` + findings table (not a certification claim) |

## Still not enterprise GA

- Side 1 issuance / Stripe / portal renewals *(commercial; tracked separately)*
- Formal SOC2 program / pen-test / support SLA *(new-launch track — do not rush into this phase)*
- Active-active / multi-region mother HA — **deferred**; see [ChorusControl-Future-Mother-HA.md](./ChorusControl-Future-Mother-HA.md)
- Full predictive suite (failure/capacity/security risk models)
- Live Fabric dual-backend CI

## API cheat sheet (new)

- `GET /api/v1/fleet/version-diff`
- `POST /api/v1/fleet/deployment-snapshot`
- `GET|PUT /api/v1/enterprise/policies`
- `GET /api/v1/compliance/findings` · `POST /api/v1/compliance/scan`
- `GET /api/v1/incidents/{id}/intelligence` · `PATCH /api/v1/incidents/{id}`
- Cortex snapshot includes `memory_endpoint` + `serving`
