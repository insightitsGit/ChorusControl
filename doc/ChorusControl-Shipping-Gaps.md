# ChorusControl — Shipping Gaps

| Field | Value |
|-------|-------|
| Status | **Side 2 shippable** — S01/S03/S04 closed in this repo; S02 owned by Side 1 agent |
| Design baseline | Gaps & Solutions v1.7.0 · Enterprise AI Operating System |
| Date | July 2026 |

Design gaps G01–G21 and upgrades U1–U23 are **resolved on paper**. Shipping status below.

---

## Shipping gap register

| ID | Severity | Gap | Status |
|----|----------|-----|--------|
| **S01** | Critical | Product code in repo | **Done** — mother + agent + six-tab UI |
| **S02** | High | Side 1 (insightits.com) not built | **Other agent** — [Side1-insightits-com-Handoff.md](./Side1-insightits-com-Handoff.md) |
| **S03** | High | Zero hot-path latency not proven | **Done** — `tests/test_hotpath_latency.py` + ledger drop-under-backpressure |
| **S04** | High | Sibling APIs not locked against live pins | **Done** — `adapters/pins.py` + factory live/Null + doctor report |
| **S05** | Low | Deferred integrations | Deferred — InsightPlugIn, VectorBridge, ChorusMesh deep alerts |
| **S06** | Medium | Intelligence / marketplace | **Done** (v1 Side 2) — metric retention + predictive/RCA recommendations; marketplace stays Side 1 |
| **S07** | Medium | Asset Graph / Assistant / AI Score | **Done** (v1) — graph + blast-radius, gated assistant, transparent score |
| **S08** | Medium | Enterprise soft gaps | **Done** (v1) — Postgres audit dual-write, OIDC/SSO, SQLite WAL, richer `/readyz`, packaging docs/CI |

---

## S01 — Implementation slices

- [x] `pyproject.toml` with `[server]` / `[agent]` extras  
- [x] Mother FastAPI `/healthz` `/readyz`  
- [x] License verifier + fail-closed middleware  
- [x] Auth / RBAC  
- [x] Fleet join tokens + registry + agent heartbeat  
- [x] Adapters + demo NullAdapters (+ optional live)  
- [x] Job queue (sleep, reindex, warm, cascade)  
- [x] Invalidation + command dispatch  
- [x] Async ledger batch export  
- [x] Audit JSONL (+ Postgres dual-write via `DATABASE_URL`)  
- [x] Six-tab APIs + UI  
- [x] `choruscontrol doctor`  
- [x] Docker / compose (mother + 2 agents; `--profile postgres` optional)  
- [x] OIDC/SSO alongside admin token  
- [x] Metrics samples + predictive recommendations  
- [x] Packaging docs + `scripts/build_release.*` + publish workflow

---

## S03 — Latency proof (acceptance)

```text
Baseline: invoke without agent ledger
Treatment: invoke_passthrough + enqueue-only ledger
Pass: p50 delta within measurement noise; no await mother on request thread
Fail: any sync mother RPC on hot path
```

Implemented in `tests/test_hotpath_latency.py` and `tests/test_restart_soak.py`.

---

## S04 — Sibling pin matrix

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

Live adapters activate when packages meet floors; otherwise NullAdapters with `demo: true`.

---

## S02 / S05 — Explicit non-blocking

| Item | Owner |
|------|--------|
| Stripe / license issuance / support portal | **Side 1 handoff — other agent** |
| InsightPlugIn SMS master commands | Deferred |
| VectorBridge | Out of scope |
| ChorusMesh Slack/PD as alert channel | Optional post-v1 |

---

## Relationship to design gaps

| Design | Shipping |
|--------|----------|
| G01–G21 closed in docs | S01 implements them |
| U1–U16 specified | S01–S04 prove them |
| Side 1 handoff written | S02 executes later elsewhere |

---

*Side 2 is shippable in this repo. Close S02 on insightits.com via the handoff doc.*
