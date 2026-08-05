# Pack vs LangGraph vs AWS Bedrock — Who Actually Wins?

**Research note · Race E · Insight IT Solutions**  
**Run:** `general_v1_pcl2a_20260725` · seed **42** · n=100 per lane · hosting **H2-phase2**

> Hosted under [ChorusControl](https://github.com/insightitsGit/ChorusControl) docs because ChorusControl **governs** the Prism Pack.  
> These numbers measure **Pack / LangGraph / AgentCore lanes** — **not** the ChorusControl UI.

**Also:** [folder index](../README.md) · [machine COMPARISON_REPORT](COMPARISON_REPORT.md) · [pack landing](https://www.insightits.com/products/prism-pack.html)

---

## Abstract

Production agents fail at different layers — ingress abuse, orchestration/tooling, answer grounding, embed tax under concurrency, and warm retrieve latency. We ran a vendor-authored mid-tier finance-agent harness (**FinancePackBench**) that compares stacks **eye-to-eye by job**, not as a single “who wins AWS” score.

On the General v1 board (`general_v1_pcl2a_20260725`, seed 42, n=100 per lane):

| Outcome | Pack (PC) | LangGraph (L2) | Bedrock AgentCore path (A1) |
|---------|-----------|----------------|------------------------------|
| Task success | **100%** | 92.5% | **100%** |
| Prompt-injection block | **100%** | 85% | **45%** |
| Benign allow | **100%** | 100% | 100% |

Mean embedding calls fell from **4.20 → 0.70** on the PrismAPI pack lane (PC) vs a re-embed pack lane (PN); a four-worker retrieve-only fan-out showed **20 vs 120** embed calls (**6.0×**).

We disclose: hosting split (local Docker for pack/LangGraph · AgentCore on AWS), non-comparable AgentCore LLM counters, and a weak **strict** grounding cell on Race E (~10%). This note explains **what we ran**, **what the lane names mean**, **topology**, **results**, and **how to read them**.

---

## 1. Research question

Engineers often ask:

> Who is better — our stack, LangGraph, or AWS Bedrock AgentCore?

That question is ill-posed. Those systems are not interchangeable peers on every metric. AgentCore runs on AWS; pack and LangGraph peers in this study ran in **local containers** on the same compose network as a shared Postgres. Bedrock does not expose a full, comparable per-turn LLM call ledger the way our instrumented local lanes do. **Prompt injection and task success are comparable** on a shared fixture. Latency and mean-LLM vs AgentCore are **not**.

Narrower questions we actually answered:

1. On the **same mid finance fixture**, does a wired pack (Guard → ChorusGraph → Shine) match or beat a LangGraph peer on **task** and **PI**?
2. Against **AgentCore Runtime + Guardrails**, where does the pack win, tie, or lose — without claiming a hosting-fair speed win?
3. Does adding a **shared embedding provider (PrismAPI)** reduce embed calls without changing task/PI quality vs a re-embed pack lane?
4. What must readers **not** infer from the table?

---

## 2. How the test was created

### 2.1 Fixture

| Setting | Value |
|---------|--------|
| Harness | FinancePackBench mid |
| Fixture | `2026-07-23.mid` finance FAQ + planted PI / hallucination suites |
| Seed | **42** (paired across lanes) |
| n per lane | **100** (40 task · 20 PI attack · 10 PI benign · 30 hallucination) |
| Model | `gemini-2.5-flash` (BYO on local lanes; Identity on AgentCore) |
| Vendor | Insight ITS — **not** a third-party audit |

Each event records lane, suite, latency, LLM/embed counters (where instrumented), PI decision, grounding decision/score, and run metadata. Summaries and bootstrap CIs are in [`COMPARISON_REPORT.md`](COMPARISON_REPORT.md).

### 2.2 Lane names — what PC, PN, L2, A1 mean

| Lane | Plain name | Stack under test |
|------|------------|------------------|
| **PC** | Pack + shared embed dataplane | **PrismGuard** → **ChorusGraph** → **PrismShine** + **PrismAPI** client · shared Postgres · **PrismCortex** sidecar present (**memory not scored** — health only) |
| **PN** | Pack control (re-embed) | Same pack quality path · **no** PrismAPI — re-embeds per worker |
| **L2** | LangGraph framework peer | **LangGraph** 1.2.4 + re-embed adapter on the **same** remote Postgres |
| **A1** | AWS managed peer (mode 1) | Bedrock **AgentCore Runtime** + **Guardrails** + **Knowledge Base** (Aurora pgvector) + **Lambda** tools + Gemini via **AgentCore Identity** |

**Pins frozen on the live run:**  
`chorusgraph==1.3.0` · `prismguard==0.1.10` · `prismshine==0.2.2` · `prismlib-plus==0.8.0` · `prismcortex==0.3.0` · `langgraph==1.2.4`

**Pack wiring (why this is a systems result):** ingress Guard **before** cache/tools/LLM; FAQ evidence in retrieval/history — not pasted into the user message; Shine on egress with evidence required. Mis-wiring (wrong Guard profile, FAQ in `message`) collapses task %.

### 2.3 Hosting topology (read before any latency column)

```text
LOCAL (Docker Compose) — H2-phase2
  [db: Postgres+pgvector]  [dataplane: PrismAPI]  [cortex: health sidecar]
       │                         │
       ├──── PC workers ─────────┘  (vectors out; embed once)
       ├──── PN workers             (SQL + re-embed)
       └──── L2 LangGraph workers   (SQL + re-embed)

AWS us-east-1 — Lane A1 (same calendar day; torn down same day)
  AgentCore Runtime
    → Guardrails (in/out)
    → Knowledge Base on Aurora pgvector (same FAQ bytes ≠ PrismRAG)
    → Lambda tools
    → Gemini via Identity (BYO Google key — not a Bedrock foundation model)
```

**What we did *not* run for this board:** identical Fargate containers for pack and AgentCore on one VPC (**H1**, deferred).

| Comparison | Fair? |
|------------|-------|
| Quality / PI / embeds among local instrumented lanes | **Yes** |
| Task / PI vs AgentCore on the same fixture | **Yes** (product outcomes) |
| Latency or $/token vs AgentCore | **No** under H2 |
| AgentCore Memory | **OFF** (single-turn fairness) |
| Classic Bedrock Agents | **Not used** |

Same-day teardown was a hard gate (compose down + AWS inventory tagged `Project=FinancePackBench` → 0).

### 2.4 Supporting runs (same program, different jobs)

| Run ID | Job |
|--------|-----|
| `general_v1_pcl2a_20260725` | **Primary** — Race E General v1 (PC / PN / L2 / A1) |
| `multiworker_embed_racee_20260725` | Fleet embed tax (4 workers × FAQ retrieves) |
| `mid_pla_faqfix_20260724` (+ A fixed) | Earlier classic mid (Race A) |
| `driver_ablation_20260725` | Warm PrismDriver vs SQL retrieve (**separate** job — do not mix) |
| `hall_onnx_judge_20260726` | Shine ONNX + judge hall arm only |

---

## 3. Technologies under test

| Layer | Pack path | Peer path |
|-------|-----------|-----------|
| Ingress / PI | **PrismGuard** 0.1.10 | AgentCore **Guardrails** (this board) |
| Orchestration | **ChorusGraph** 1.3.0 (native runtime — not a LangGraph wrapper) | **LangGraph** 1.2.4 · AgentCore Runtime |
| Egress / grounding | **PrismShine** 0.2.2 | AgentCore grounding signals / binary peers |
| Embed dataplane | **PrismAPI** (PC) | Per-worker re-embed (PN / L2) |
| Memory | **PrismCortex** 0.3.0 sidecar — **health only** | AgentCore Memory OFF |
| Data | Shared Postgres FAQ | Aurora KB with **identical FAQ bytes** (different retriever) |
| Model | Gemini 2.5 Flash | Same family via Identity on A1 |

PrismRAG was **excluded** from the core race. Race C (Driver vs SQL retrieve) is a **different job** — do not mix into the agent-quality table.

---

## 4. Results

### 4.1 Agent quality + PI (primary table)

| Lane | Task % | PI block % | Benign % | Mean embeds | Mean LLM† | Task P50 |
|------|--------|------------|----------|-------------|-----------|----------|
| **PC** (pack + PrismAPI) | **100** | **100** | **100** | **0.70** | 0.60 | 2895 ms *local* |
| **PN** (pack, re-embed) | **100** | **100** | **100** | 4.20 | 0.60 | 2900 ms *local* |
| **L2** (LangGraph) | 92.5 | 85 | 100 | 4.20 | 1.12 | 3602 ms *local* |
| **A1** (AgentCore) | **100** | **45** | 100 | — | 0.40‡ | 4264 ms *AWS* |

† Mean LLM is a fair efficiency signal **among local instrumented lanes**.  
‡ AgentCore’s harness LLM field is **not comparable** — do **not** claim “fewer LLM calls than Bedrock.”

**Bootstrap (PI attack, n=20):** PC **100%** [100, 100] · L2 **85%** [65, 100] · A1 **45%** [20, 70].

### 4.2 What PC vs PN proves

PC and PN tied at **100 / 100 / 100**. PrismAPI did **not** create the security or task win. It removed embed work: **0.70 vs 4.20** mean embeds (−3.50 absolute; **~83%** relative reduction vs the re-embed pack lane). Multi-worker: **20 vs 120** (**6.0×**).

### 4.3 Grounding — dual board (do not collapse to one %)

On Race E, **strict pass** (Shine/HHEM `pass` only) for PC/PN was **~10%** — a **losing cell** vs A1 binary **26.7%**. Mean Shine score on Race E was **~0.68** vs L2 peer **~0.15**. Allow (`pass|flag`) on pack was **100%** under Shine’s gray policy.

Follow-up hall-only run (`hall_onnx_judge_20260726`, n=30):

| Metric | Pack Shine | Binary peer |
|--------|------------|-------------|
| Strict pass | 30% | 30% |
| Allow | **100%** | 30% |
| Mean score | **0.54** | 0.30 |

**PASS ≠ world-true.** Grounding here is a planted suite, not production RAG certification.

### 4.4 Classic mid (Race A) — same PI story

`mid_pla_faqfix_20260724` / A fixed: Pack **100/100/100** · LangGraph+peer **95/85/100** · AgentCore **100/45/100**. Efficiency **0.60 vs 1.11** mean LLM — **vs LangGraph only**.

---

## 5. How to understand the results

| If you care about… | Look at… | Correct reading |
|--------------------|----------|-----------------|
| Safer on PI? | PI block % + benign allow | Pack **best of three** here; AgentCore Guardrails **45%** is the soft cell |
| Work still gets done? | Task % | Pack **ties** AgentCore at 100%; **beats** LangGraph |
| Normal users blocked? | Benign allow | All three at **100%** here |
| Is PrismAPI the quality hero? | PC vs PN | **No** — quality tied; API wins **embed tax** |
| More efficient than LangGraph? | Mean LLM PC/PN vs L2 | **Yes on this board** (0.60 vs ~1.1) |
| More efficient than Bedrock? | — | **Not claimable** from this harness |
| Faster than AgentCore? | Task P50 | **Do not claim** — different hosts (H2) |
| Grounding solved? | Strict vs allow vs mean | Strict was weak on Race E; allow/mean tell a different story |
| Did Cortex win? | — | **No memory suite scored** |

**Takeaway:** production agents need a **layered path** — who checks ingress, who runs tools, who grounds the answer, who owns embeds at fleet scale — measured **per job**, not as one leaderboard row.

---

## 6. Limitations (publish with the table)

1. Vendor-authored harness.  
2. Hosting **H2-phase2** — no cross-host latency or $ win vs AgentCore.  
3. AgentCore LLM / cost fields not comparable.  
4. Gemini via Identity ≠ Bedrock foundation model.  
5. Aurora KB ≠ PrismRAG.  
6. Cortex = health only on this board.  
7. Grounding = planted suite; Race E strict pass is a disclosed lose.  
8. PI holdout is small (20 attacks) — not “100% forever.”  
9. Not multi-cloud; Classic Agents not used; Memory OFF on A.  
10. Race C Driver retrieve is a **separate** experiment.

---

## 7. Implications

1. **Wire the pack first.** PN matching PC on quality means Guard → ChorusGraph → Shine is the load-bearing path.  
2. **Add PrismAPI when workers share a KB** and you pay embed tax — not to “fix” task %.  
3. Name the AWS peer honestly: **AgentCore Runtime + Guardrails + KB (A1)** — not “all of AWS.”  
4. Refuse blended P50 and refuse LLM-efficiency headlines vs Bedrock until the meter is honest.  
5. Soft asks: **CONTROL** for [ChorusControl](https://www.insightits.com/products/choruscontrol.html) · **GRADE** / [Scorecard](https://github.com/insightitsGit/PrismGuard/blob/main/docs/scorecard.md) for PI on your prompts · no cold Calendly.

### Open-source pack (use each lib alone)

Each pack component is available as open source. ChorusControl is the optional ops roof.

| Library | GitHub |
|---------|--------|
| PrismGuard | https://github.com/insightitsGit/PrismGuard |
| ChorusGraph | https://github.com/insightitsGit/ChorusGraph |
| PrismShine | https://github.com/insightitsGit/PrismShine |
| PrismAPI / prismlib-plus | https://github.com/insightitsGit/prismlibplusapi |
| PrismCortex (memory — **not scored** on Race E; see separate bench) | https://github.com/insightitsGit/PrismCortex · [benchmarks/RESULTS.md](https://github.com/insightitsGit/PrismCortex/blob/master/benchmarks/RESULTS.md) (~5.2× gist vs log) |
| ChorusControl (this roof) | https://github.com/insightitsGit/ChorusControl |

Pack site: https://www.insightits.com/products/prism-pack.html

---

## 8. Artifacts

| Artifact | Location |
|----------|----------|
| This research note | this file |
| Machine report | [`COMPARISON_REPORT.md`](COMPARISON_REPORT.md) |
| Folder index | [../README.md](../README.md) |
| Pack landing | https://www.insightits.com/products/prism-pack.html |
| ChorusControl | https://www.insightits.com/products/choruscontrol.html |
| Scorecard | https://github.com/insightitsGit/PrismGuard/blob/main/docs/scorecard.md |
