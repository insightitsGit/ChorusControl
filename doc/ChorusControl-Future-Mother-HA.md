# ChorusControl — Future Phase: Mother HA & Multi-Region

| Field | Value |
|-------|-------|
| Status | **Deferred** — after go-live of current Side 2 phase |
| Priority | Post-GA / enterprise scale customers |
| Audience | Implementers, ops, sales engineering |
| Date | 2026-07-27 |
| Related | [ChorusControl-Enterprise-Depth.md](./ChorusControl-Enterprise-Depth.md) · Design Review R05 |

---

## Why this exists

Current go-live target is a **single mother** per environment with optional Postgres durability (dual-write / restore). That is enough for pilots and first production fleets.

**Active-active mother HA** and **multi-region** are real use cases — but they add coordination complexity. Capture them here so they are not forgotten, and so they are **not** pulled into the current launch.

---

## Use case (when a buyer asks)

Keep the ops **control plane** (UI, API, fleet join/heartbeat, cascades, Admin) up with near-zero downtime if one mother host or availability zone fails.

| Scenario | Why HA helps |
|----------|----------------|
| Mother VM/container crash during cascade / agent storm | Other mother keeps heartbeats + Admin |
| Rolling mother upgrade | No long maintenance window |
| Multi-AZ / multi-region policy | “Failover in under a minute” is not enough |

**Not** an AI-feature ask — it is infrastructure for **large fleets / regulated multi-region ops**.

Early buyers: one mother + restart/replace + Postgres or sticky volume is fine.

---

## Patterns (do not confuse)

| Pattern | Meaning | Current phase |
|---------|---------|---------------|
| **Single mother** | One process; restart to recover | **Ship this** |
| **Active-standby** | One active; standby promotes on failure (shared Postgres) | Sensible *next* HA step |
| **Active-active** | Two+ mothers both live, both serving traffic | **This future phase** — hardest |

What we already have toward durability: Postgres dual-write for nodes / join tokens / cascades / assets + restore into empty SQLite. That supports **replace-the-mother**, not two live mothers.

---

## Future phase scope (when opened)

1. **Decide first:** active-standby vs active-active (prefer standby unless buyer mandates active-active).
2. **Shared store:** Postgres (or equivalent) as primary for registry, join tokens, cascades, acks — not audit-only.
3. **Leader / sticky routing:** how agents find “the” mother (DNS, LB, or explicit primary URL).
4. **Split-brain rules:** who runs cascade.auto, job queue, license online-check — only one writer for mutating control jobs.
5. **Multi-region:** async replica vs dual-write; RPO/RTO written into the customer runbook.
6. **Tests:** kill primary under load; agents re-attach; no duplicate cascades; license state consistent.
7. **Docs:** ops runbook + sales “HA add-on” language (honest: control-plane HA ≠ Prism hot-path HA).

### Explicit non-goals for that phase

- Do not invent a second fleet discovery path to insightits.com
- Do not weaken offline license / air-gap story
- Do not require Fabric for HA (HTTP control remains primary)

---

## Trigger to start this work

Open this phase only when **all** of the following are true:

- Current product phase is **live** with paying / pilot customers
- At least one customer (or sales commit) needs multi-AZ / multi-region control-plane SLA
- Side 1 commercial loop and core Side 2 tabs are stable in production

Until then: document the ask, quote **active-standby + Postgres** as the usual answer, and keep active-active off the sprint board.

---

## One-line capture for roadmaps

> **Future:** Mother active-standby (then optional active-active) + multi-region backups for control-plane HA — after go-live; not in current launch.**

---

*Insight IT Solutions LLC — deferred HA / multi-region note*
