# ChorusGraph Pack vs LangGraph Pack vs AWS Bedrock Pack

**Race E eye-to-eye board** — same mid finance fixture, seed 42, n=100/lane.

| “Pack” in the title | What we actually ran |
|---------------------|----------------------|
| **ChorusGraph Pack** | PrismGuard → **ChorusGraph** → PrismShine (+ PrismAPI + Cortex sidecar on PC) |
| **LangGraph Pack** | **LangGraph** peer + re-embed on the same Postgres (**L2**) |
| **AWS Bedrock Pack** | Bedrock **AgentCore Runtime** + Guardrails + KB (**A1**) — not “all of AWS” |

**Who this is for:** engineers comparing production agent stacks.  
**Where you are:** [ChorusControl](https://github.com/insightitsGit/ChorusControl) docs — the ops plane that **governs** the ChorusGraph / Prism Pack. These numbers measure those stacks, not the ChorusControl dashboard UI.

> **GitHub tip:** This folder’s file list only shows `README.md` + `race-e/`.  
> **Open this README** (or the research note) for lane codes **PC / PN / L2 / A1** and product names. They are in the tables below — not as separate folder names.

---

## What’s in the Prism Pack (the names)

These are the **pack libraries** (each is open source on its own). Race E wired them as a system:

| Name | Job in the pack |
|------|-----------------|
| **PrismGuard** | Ingress / prompt-injection gate |
| **ChorusGraph** | Agent runtime / orchestration |
| **PrismShine** | Egress / grounding |
| **PrismAPI** (prismlib-plus) | Shared embed dataplane (**PC** lane) |
| **PrismCortex** | Agent memory sidecar on **PC** — **running / healthy**, memory quality **not scored** on Race E |
| **ChorusControl** | Ops roof (this repo) — optional; not a Race E lane |

Peers on the same board (not pack): **LangGraph** (**L2**) · **AWS Bedrock AgentCore + Guardrails + KB** (**A1**).

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

→ **[ChorusGraph Pack vs LangGraph Pack vs AWS Bedrock Pack — Who Actually Wins?](race-e/RESEARCH-NOTE-pack-vs-langgraph-vs-aws-bedrock.md)**

Machine appendix (raw lane tables): [`race-e/COMPARISON_REPORT.md`](race-e/COMPARISON_REPORT.md)

---

## Lane names (what PC / PN / L2 / A1 mean)

| Code | Name in plain English | Stack |
|------|----------------------|--------|
| **PC** | **P**ack + PrismAPI **C**lient dataplane | **PrismGuard** → **ChorusGraph** → **PrismShine** + **PrismAPI** + **PrismCortex** sidecar (health only) |
| **PN** | **P**ack control (**N**o shared API — re-embed) | Same pack quality path (Guard → Graph → Shine); each worker re-embeds · no PrismAPI |
| **L2** | **L**angGraph peer | **LangGraph** 1.2.4 + re-embed on the **same** Postgres |
| **A1** | **A**WS peer mode **1** | Bedrock **AgentCore Runtime** + **Guardrails** + **KB** + Lambda tools + Gemini via Identity |

Pins on the live run: `chorusgraph==1.3.0` · `prismguard==0.1.10` · `prismshine==0.2.2` · `prismcortex==0.3.0` · `prismlib-plus` (PrismAPI)

**Pack wiring that matters:** Guard on ingress **before** cache/tools/LLM; Shine on egress with evidence. Mis-wiring collapses task %. Cortex was in compose on PC but **not** scored for memory quality — this is a **systems** task/PI + embed-tax result, not a Cortex memory win.

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
**Not fair:** latency or $ vs AWS · “beat AWS overall” · “Cortex memory win.”  
**Disclosed weak cell:** Race E **strict** grounding ~**10%** (PASS ≠ world-true).

**PC vs PN:** quality tied at 100/100/100 — PrismAPI did **not** create the PI/task win; it cut embeds **0.70 vs 4.20** (~83%). Fleet fan-out: **20 vs 120** embeds (**6×**).

---

## Why this lives under ChorusControl

ChorusControl is the self-hosted **ops / governance roof** for the Prism Pack. Enterprise buyers look here for “does the stack we operate have honest proof?”

The Race E lanes are still **Pack vs LangGraph vs AgentCore** — not a claim that the ChorusControl UI was under test.

**You can use every pack library open-source on its own** (pip + GitHub). ChorusControl is optional when you want the fleet ops plane on top.

| Library | Role in the pack | Open source |
|---------|------------------|---------------|
| **PrismGuard** | Ingress / PI | [GitHub](https://github.com/insightitsGit/PrismGuard) · [PyPI](https://pypi.org/project/prismguard/) · [Scorecard](https://github.com/insightitsGit/PrismGuard/blob/main/docs/scorecard.md) |
| **ChorusGraph** | Agent runtime / orchestration | [GitHub](https://github.com/insightitsGit/ChorusGraph) · [PyPI](https://pypi.org/project/chorusgraph/) · [vs LangGraph benches](https://github.com/insightitsGit/ChorusGraph/blob/master/docs/BENCHMARK_RESULTS.md) |
| **PrismShine** | Egress / grounding | [GitHub](https://github.com/insightitsGit/PrismShine) · [PyPI](https://pypi.org/project/prismshine/) |
| **PrismAPI** / PrismLib Plus | Shared embed dataplane (PC lane) | [GitHub](https://github.com/insightitsGit/prismlibplusapi) · [PyPI](https://pypi.org/project/prismlib-plus/) |
| **PrismCortex** | Agent memory (PC sidecar = **health only** on Race E) | [GitHub](https://github.com/insightitsGit/PrismCortex) · [PyPI](https://pypi.org/project/prismcortex/) · **separate memory bench:** [RESULTS.md](https://github.com/insightitsGit/PrismCortex/blob/master/benchmarks/RESULTS.md) (gist vs log **~5.2×**) |
| **ChorusControl** | Ops / governance roof (this repo) | [GitHub](https://github.com/insightitsGit/ChorusControl) · [landing](https://www.insightits.com/products/choruscontrol.html) |

Pack family site board: [prism-pack.html](https://www.insightits.com/products/prism-pack.html)

| Soft ask | Link |
|----------|------|
| Enterprise roof | **CONTROL** → [ChorusControl](https://www.insightits.com/products/choruscontrol.html) |
| PI on *your* prompts | **GRADE** → [Scorecard](https://github.com/insightitsGit/PrismGuard/blob/main/docs/scorecard.md) |

No cold Calendly.
