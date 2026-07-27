# ChorusControl — Implementation Plan (No Phases)

| Field | Value |
|-------|-------|
| Product | ChorusControl — Enterprise AI Operating System |
| Status | **Side 2 complete** (demo + live-adapter path) |
| Date | July 2026 |
| Inputs | COMPLETE-DESIGN v1.7 · Design-Review R01–R08 / I01–I05 |

> **Rule:** Do not stage work as “Phase 1 / 2 / 3.” Build the complete platform. Work items below are a **dependency-ordered checklist**, not gated releases.

---

## Sprint-0 decisions (locked from review)

| ID | Decision |
|----|----------|
| **R01** | **Control transport primary = PrismAPI/HTTP**; Fabric secondary/opt-in. |
| **R02** | License **grace window** default 14 days read-only + banner; mutating blocked; **±24h clock skew**. |
| **R05** | Mother state persists in **SQLite by default**; Postgres opt-in via `DATABASE_URL`. |
| **I05** | Customer UI product name: **ChorusControl — AI Operations Platform**. |

---

## Workstream checklist (complete all)

### A. Foundation
- [x] `pyproject.toml` extras `[server]`, `[agent]`, `[postgres]`, `[all]`, `[dev]`, `[packaging]`
- [x] Config / env (`Settings`)
- [x] Persistence: SQLite (WAL) + Postgres audit dual-write (`DATABASE_URL`)
- [x] `/healthz`, `/readyz` (license + Postgres + adapters)
- [x] Dockerfiles + `docker-compose` (mother + 2 agents + bootstrap; `--profile postgres`)
- [x] Packaging docs + build scripts + tag publish workflow

### B. License & Auth
- [x] Offline Ed25519/JWT verify + claims
- [x] Grace / skew / fail-closed middleware
- [x] Local admin token + RBAC roles
- [x] Optional OIDC/SSO (`CHORUSCONTROL_OIDC_*`)
- [x] Audit signing key bootstrap

### C. Fleet & Transport
- [x] Join tokens, enroll, revoke, `max_nodes`
- [x] HTTP transport (primary)
- [x] Fabric transport adapter stub (optional)
- [x] Agent probe + heartbeat + product inventory
- [x] Command dispatch + honest NACK + version negotiation
- [x] Memory endpoint mapping per tenant
- [x] Policy drift badge API
- [x] Version snapshots daily

### D. Engine
- [x] Job queue: sleep, reindex, warm
- [x] Invalidation broadcaster
- [x] Correction cascade + ack + consistency SLO
- [x] Ledger batch + sampling
- [x] Audit async JSONL + audit-verify CLI

### E. Adapters & Caps
- [x] Protocols + NullAdapters (demo)
- [x] Live adapters when packages installed (optional try-import + pin floors)
- [x] Caps aggregate service
- [x] Pin floors documented in doctor

### F. APIs & UI (all six tabs)
- [x] Overview / Trace / Taxonomy / Memory / Guard / Admin shells + APIs

### G. Platform intelligence
- [x] Asset Graph v1 sync + blast-radius API
- [x] AI Score transparent formula
- [x] Incident table + cascade linkage
- [x] Ops Assistant ask + gated execute (RBAC + audit)
- [x] Metric samples + retention + predictive/RCA recommendations
- [x] OTel coexistence note in README

### H. Verification
- [x] Unit tests: license grace, jobs, cascade, audit, API join, adapters
- [x] Hot-path latency dedicated harness (S03)
- [x] Restart soak test automation
- [x] Demo enroll + compose bootstrap scripts

---

## Out of this repo

- **S02 Side 1** (insightits.com / Stripe / license issuance) — handoff doc only
- InsightPlugIn / VectorBridge / ChorusMesh deep alerts (S05)

---

## Definition of done (whole Side 2 product)

Mother + agent installable; all six tabs served; fleet join/heartbeat/commands; cascade; caps; grace license; SQLite durability; demo compose with 2 agents; tests green including S03/S04; design review R/I items addressed.

*No phase gates. Checklist complete for Side 2.*
