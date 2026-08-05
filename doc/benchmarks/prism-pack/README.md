# Pack family benchmarks

**Who this is for:** engineers comparing production agent stacks.  
**Where you are:** [ChorusControl](https://github.com/insightitsGit/ChorusControl) docs — the ops plane that **governs** the Prism Pack. The numbers below measure the **pack** (and peers), not the ChorusControl dashboard UI.

---

## What we did (Race E)

We ran a vendor-authored mid finance-agent bake-off (**FinancePackBench**) so each stack faces the **same job** on the same fixture — not one blended “who beats AWS” score.

| Setting | Value |
|---------|--------|
| Primary run | `general_v1_pcl2a_20260725` (**Race E**) |
| Fixture | `2026-07-23.mid` finance FAQ + planted PI / hallucination suites |
| Seed | **42** (paired across lanes) |
| n per lane | **100** (40 task · 20 PI attack · 10 PI benign · 30 hallucination) |
| Model | `gemini-2.5-flash` |
| Hosting | **H2-phase2** — pack + LangGraph on local Docker compose; AgentCore on AWS (same day, torn down) |

**Start here:** the full write-up — method, lane names, topology, results, and how to read them:

→ **[Pack vs LangGraph vs AWS Bedrock — Who Actually Wins?](race-e/RESEARCH-NOTE-pack-vs-langgraph-vs-aws-bedrock.md)**

Machine appendix (raw lane tables): [`race-e/COMPARISON_REPORT.md`](race-e/COMPARISON_REPORT.md)

---

## Lane names (what PC / PN / L2 / A1 mean)

| Code | Name in plain English | Stack |
|------|----------------------|--------|
| **PC** | **P**ack + shared embed (**C**lient dataplane) | PrismGuard → ChorusGraph → PrismShine + **PrismAPI** |
| **PN** | **P**ack control (**N**o shared API — re-embed) | Same pack quality path; each worker re-embeds |
| **L2** | **L**angGraph peer | LangGraph 1.2.4 + re-embed on the **same** Postgres |
| **A1** | **A**WS peer mode **1** | Bedrock **AgentCore Runtime** + **Guardrails** + **KB** + Lambda tools + Gemini via Identity |

Pins on the live run: `chorusgraph==1.3.0` · `prismguard==0.1.10` · `prismshine==0.2.2`

**Pack wiring that matters:** Guard on ingress **before** cache/tools/LLM; Shine on egress with evidence. Mis-wiring collapses task % — this is a **systems** result, not a single-library microbench.

---

## Scoreboard (agent quality + PI)

| Lane | Task % | PI block % | Benign allow % | Mean embeds | Mean LLM | Task P50 |
|------|--------|------------|----------------|-------------|----------|----------|
| **PC** | **100** | **100** | **100** | **0.70** | 0.60 | ~2.9 s *local* |
| **PN** | **100** | **100** | **100** | 4.20 | 0.60 | ~2.9 s *local* |
| **L2** | 92.5 | 85 | 100 | 4.20 | 1.12 | ~3.6 s *local* |
| **A1** | **100** | **45** | 100 | — | n/a‡ | ~4.3 s *AWS* |

‡ AgentCore’s harness LLM counter is **not comparable** — do not claim “fewer LLM calls than Bedrock.”

**Fair to cite:** task · PI · benign · PC vs PN embed tax · mean LLM among **local** lanes.  
**Not fair:** latency or $ vs AWS · “beat AWS overall.”  
**Disclosed weak cell:** Race E **strict** grounding ~**10%** (PASS ≠ world-true).

**PC vs PN:** quality tied at 100/100/100 — PrismAPI did **not** create the PI/task win; it cut embeds **0.70 vs 4.20** (~83%). Fleet fan-out: **20 vs 120** embeds (**6×**).

---

## Why this lives under ChorusControl

ChorusControl is the self-hosted **ops / governance roof** for Guard · ChorusGraph · Shine · Cortex · related pack libs. Enterprise buyers look here for “does the stack we operate have honest proof?”  

The Race E lanes are still **Pack vs LangGraph vs AgentCore** — not a claim that the ChorusControl UI was under test.

| Product page | Soft ask |
|--------------|----------|
| [ChorusControl](https://www.insightits.com/products/choruscontrol.html) | **CONTROL** (enterprise access) |
| [Prism Pack benchmarks](https://www.insightits.com/products/prism-pack.html) | Job-by-job site board |
| [Guardrail Scorecard](https://github.com/insightitsGit/PrismGuard/blob/main/docs/scorecard.md) | Reply **GRADE** for PI on *your* prompts |

No cold Calendly.
