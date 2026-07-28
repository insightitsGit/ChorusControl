# ChorusControl — Design Review: Gaps & Suggestions

| Field | Value |
|-------|-------|
| Reviews | [ChorusControl-COMPLETE-DESIGN.md](./ChorusControl-COMPLETE-DESIGN.md) **v1.7.0** (historical); current design **v1.8.0** adds §3.7.4a Client AI chats + §11.6 execute matrix |
| Scope | Independent review — architecture risks (R01–R08) + product suggestions (I01–I05) |
| Status | Open — items to resolve before / during sprint 0 |
| Date | July 2026 |

> **Verdict:** The design is implementation-ready for Phases 1–2. The gap register (G01–G21),
> decision log, and traceability are real engineering rigor, and the design consistently reuses
> the shipped stack instead of inventing new science. The dominant risk is **scope gravity** —
> the Enterprise AI OS vision (Asset Graph, AI Score, Ops Assistant) sits on top of a repo with
> zero code (S01). Architecture is sound; the review items below are what would be expensive to
> change *after* code exists.

---

## 1. What is genuinely strong (keep, do not dilute)

| # | Strength | Why it matters |
|---|----------|----------------|
| 1 | **Correction Cascade (§3.11)** | The real moat. `Cortex on_event → invalidate_tags/where → mark_revalidate → CACHE_PREDATES_FACT_UPDATE` as one audited action is only possible because Insight ITS owns all four layers. No competitor can copy it. |
| 2 | **Honest Caps (§3.12)** | A differentiator, not just ethics. Guard `caps`, Shine `capabilities()`, and "PASS ≠ world-true" carry through. Enterprise buyers trust truth tables over dashboards that lie. |
| 3 | **Zero hot-path latency as hard rule (§3.19.6a)** | Forbidden code patterns written into the spec + S03 CI latency gate. If violated, adoption on production ChorusGraph fleets dies. |
| 4 | **Two-sided split + offline Ed25519 license** | Clean boundary, consistent with Cortex/ChorusMesh sovereignty story. Side 1 contract is precise enough to prevent claim-schema drift. |
| 5 | **Adapters + NullAdapters + demo mode** | Lets UI ship before a fleet exists; insulates against sibling release velocity. |

---

## 2. Design gaps / risks to resolve (R01–R08)

### R01 — Fabric as primary control transport is unverified · **Critical · resolve in sprint 0**

CHORUS Fabric is designed for encrypted **float32 tensor streaming**. The control plane needs
JSON-ish frames: `HEARTBEAT`, `POLICY_PUSH`, `JOB_DISPATCH`, `LEDGER_BATCH`, `ACK`. PrismLib
Micro's `TOKEN_SYNC` / `HEALTH` / `SIGNAL` frames are precedent, but the design bets the whole
command surface on Fabric before confirming:

- Frame types suitable for structured control payloads
- Payload size limits (ledger batches can be large)
- Reconnect / backpressure semantics for long-lived agent sessions

**Recommendation:** For v1, invert the priority — **PrismAPI/HTTP primary, Fabric as the
optimization**. The `transport.py` abstraction (§3.19.10) already makes this a config flip, and
the acceptance criteria say "Fabric **and/or** PrismAPI." Do not let Fabric debugging block
Phase 1. Run a Fabric control-frame spike as a parallel task; promote it to primary when proven.

**Done when:** transport interface is proven with both backends in CI; a decision record states
which is primary for v1 and why.

---

### R02 — License lapse behavior is undefined · **High**

Fail-closed at boot is correct, but the hourly re-check (§3.2) means an `exp` passing at 2 AM
Saturday turns the entire ops platform into `503 LICENSE_INVALID` for an air-gapped customer who
cannot reach Side 1 to renew.

**Recommendation:**

- Add a documented **grace window** (e.g. 7–14 days) of read-only / degraded mode with a loud
  banner instead of a hard 503 — mutating routes blocked, observability stays up.
- Add clock-skew tolerance (e.g. ±24h) on `exp`/`iat` checks.
- Reflect grace behavior in the **Side 1 handoff contract** (Part C) since it affects renewal UX
  and short-`exp` re-issue policy.

**Done when:** grace policy is in §3.2 + Part C §3.3; license tests cover in-grace and
past-grace states.

---

### R03 — Trace / ledger volume has no retention or sampling model · **High**

`LEDGER_BATCH` (§3.19.6b) ships Route Ledger entries from every worker to the mother. On a
high-QPS fleet this is the first thing that falls over in a pilot. Mother-side storage for
traces (table? retention? per-tenant quota?) is not defined anywhere.

**Recommendation:**

- **Always ship:** Guard gate events, errors, Shine verdicts, cascade-related hops.
- **Sample:** pass-through / healthy hops (configurable rate, default e.g. 10%).
- Define mother storage: Postgres trace tables with retention days + per-tenant quota; document
  `agent_ledger_dropped_total` surfaced in Overview so drops are honest, not silent.

**Done when:** trace event schema (§3.7.2) gains a `sampled` flag; retention config exists;
load test demonstrates bounded mother storage under sustained ledger traffic.

---

### R04 — Cortex proxy needs an addressing model · **High**

`/memory/*` (§3.7.4, §3.15) proxies "Cortex" — but a fleet has many nodes and Cortex may run
in-process on several. Which node answers `GET /memory/facts` for tenant X is undefined; the
Memory tab becomes ambiguous the moment there are two workers.

**Recommendation:** add an explicit **tenant → memory-endpoint mapping** to the fleet registry
(or a designated `memory` node role in `CHORUSCONTROL_NODE_ROLE`). Memory APIs take/resolve a
`(tenant_id, endpoint)` pair; the UI shows which node is serving memory for the tenant.

**Done when:** registry schema includes memory endpoint per tenant; Memory tab renders the
serving node; conflict-resolve + cascade tests run against the mapped endpoint.

---

### R05 — Mother durability / HA unspecified · **High · decide in sprint 0**

Mother is "one per env," but the design never says where the **node registry, cascade state,
and join tokens** live across a restart. Postgres is optional (audit only). Losing the registry
on restart orphans the fleet.

**Recommendation:**

- Sprint 0 decision: **SQLite default, Postgres opt-in** for registry + cascade + join-token
  state (mirrors the ChorusGraph checkpoint pattern).
- Define agent behavior while the mother is down: buffer + retry with backoff (already implied
  by §3.19.6a bounded queues) and automatic re-register on reconnect.
- Document (even if deferred) the HA-pair story the §3.19.1 table mentions in passing.

**Done when:** persistence backend decision recorded; restart test proves agents re-appear
without re-joining; cascade state survives mother restart.

---

### R06 — Audit signatures lack a verification story · **Medium**

Audit envelopes are Ed25519-signed (§3.6), but nothing says **who verifies them, with what key,
and how**. Without that, the signatures are ceremony for an auditor.

**Recommendation:**

- SOC2 export pack (§3.18) must include the audit **public key** + a standalone verify
  tool/script (`choruscontrol audit-verify export.jsonl --pubkey ...`).
- Spec rotation for `CHORUSCONTROL_AUDIT_PRIVATE_KEY_PEM` (key id in each envelope; pack ships
  the key history).

**Done when:** an auditor with only the export zip can verify every envelope offline.

---

### R07 — Sibling version churn needs continuous defense · **Medium**

Ten floor-pinned packages, all moving (S04). A one-time adapter smoke check will rot.

**Recommendation:**

- Make S04 a **nightly CI matrix** against live PyPI pins, not a one-time gate.
- Add **version negotiation**: agents already report product versions in heartbeats — the mother
  should degrade features per node (e.g. no `invalidate_where` on `prismlib-plus <0.8.0`,
  NACK `warm_partition` on `chorusgraph <1.1.0`) instead of assuming fleet-wide floors.
  This extends the existing "honest NACK" pattern (§3.19.6) to versions, not just presence.

**Done when:** nightly pin job exists; per-node feature matrix derives from heartbeat versions;
command dispatch consults it.

---

### R08 — No competitive / OTel coexistence stance · **Medium**

An enterprise buyer will ask: *"Why not Grafana + LangSmith/LangFuse + our existing OTel
pipeline?"* ChorusGraph already emits OpenTelemetry — ChorusControl must not fight the
customer's existing observability stack.

**Recommendation:** add a short section to Part B:

- **Coexist:** don't replace OTel/Grafana; optionally forward or link out; never require
  disabling existing telemetry.
- **Positioning answer (one paragraph):** the things OTel cannot do — correction cascade,
  capability truth tables, Guard Policy Studio, zero-token replay, offline-sovereign licensing,
  fleet policy control. Observability tools *watch*; ChorusControl *acts* with RBAC + audit.

**Done when:** the section exists and sales/docs copy reuses it.

---

## 3. Product suggestions (I01–I05)

### I01 — Policy drift detection · **P0-adjacent, nearly free**

Agents already probe local Guard caps (§3.19.2). Compare each node's **actual**
profile/artifact against the mother's **intended** Policy Studio document (§3.7.5) and show a
**drift badge** per node. This directly operationalizes the "law ONNX on finance" failure mode
Guard's README warns about — using data already in the heartbeat payload.

### I02 — Fleet consistency SLO from cascade acks · **P1**

`INVALIDATE_ACK` per node is already collected (§3.4, §3.14). Compute and display
**"time until whole fleet consistent after a correction."** A marketable, benchmarkable number
in the same receipts culture as the published cache/latency results — and it makes the cascade
visibly better than a bare invalidate button.

### I03 — Version snapshots before the Asset Graph · **P1**

Full Asset Graph is Phase 3, but heartbeats already carry product versions and caps digests.
Persist a **per-node, per-day snapshot** from Phase 1 and "what changed before this incident?"
comes almost for free — a down payment on version intelligence (§11.10) with no graph engine.

### I04 — Promote the demo-mode quickstart to Phase 1 · **P1 (was P2 polish)**

A `docker-compose up` that starts **mother + two demo agents** in `CHORUSCONTROL_DEMO_MODE`
mirrors the `chorusgraph-demo` / `prismshine verify --demo` culture across the sibling repos and
will be the best sales and docs asset. Should be a Phase 1 deliverable, not polish.

### I05 — Name the first sellable slice explicitly · **P0 scope guard**

Phases 1–2 (fleet inventory + caps + cascade + trace feed + Guard Policy Studio) is already a
product someone would pay for. Add one line to §10.2 defining that as **v1 GA**, and defer the
"Enterprise AI OS" language in *customer-facing UI* until Phase 3+ — so marketing claims never
outrun the caps philosophy the design itself enforces.

---

## 4. Document consistency nits

| Nit | Fix |
|-----|-----|
| Part A status "Design complete — implementation not started" vs Part B "Approved for implementation" | Pick one status string |
| Document control jumps 1.5.0 → 1.7.0 while Part C is 1.1.0 and Part E is 1.2.0 | Add a note that sub-parts version independently (or align) |

---

## 5. Suggested resolution order

| When | Items |
|------|-------|
| **Sprint 0 (before code)** | R01 (transport primary), R05 (mother persistence), R02 (grace policy — affects Side 1 contract), I05 (v1 GA definition) |
| **Phase 1** | R07 (nightly pin CI + version negotiation), I04 (demo quickstart), I03 (version snapshots) |
| **Phase 2** | R03 (trace sampling/retention), R04 (memory addressing), I01 (policy drift), I02 (consistency SLO) |
| **Before first enterprise pilot** | R06 (audit verify tool), R08 (OTel/competitive section) |

R01 and R05 are the two decisions that are **expensive to change after code exists** — lock them
first.

---

*Independent design review of ChorusControl COMPLETE-DESIGN v1.7.0 — July 2026*
