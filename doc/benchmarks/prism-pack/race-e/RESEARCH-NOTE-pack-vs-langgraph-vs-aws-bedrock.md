# Pack vs LangGraph vs AWS Bedrock — Who Actually Wins?

> **Hosted under ChorusControl docs.** ChorusControl governs the Prism Pack. This note is the job-by-job **pack** proof (Guard → ChorusGraph → Shine ± PrismAPI) vs LangGraph vs Bedrock AgentCore — **not** a measurement of the ChorusControl UI. Soft CTA for the roof: **CONTROL**. Soft CTA for PI: **GRADE** / Scorecard.

**Marketing source:** posted LI research note · Article 3 · run `general_v1_pcl2a_20260725`

---

# Article 3 — Research note (engineer-facing · Prism Pack Family)


```
prismmarket · voice:research-b2b · product:stack|PG · channel:LI|X
methods: PM-02, PM-PROOF, PM-DISCLOSE, PM-GRADE, PM-URLS
prismtitle · product:stack · angle:pain|comparison · PT-PAIN · PT-BOLD-COMPARE · PT-OLDNEW · PT-ONE
```

**Status:** Draft v0.1 — ready for Amin review · **do not post same feed day as Shine PDF (2026-08-04)** · wait ~48–72h  
**Hero:** Prism Pack wiring (PrismGuard → ChorusGraph → PrismShine) · supporting: PrismAPI embed tax  
**Soft CTA:** **GRADE** · **no Calendly** · no “beat AWS overall”  
**Primary evidence:** `general_v1_pcl2a_20260725` (Race E) · supporting: `mid_pla_faqfix_20260724` / `_a_fixed_` · `multiworker_embed_racee_20260725` · `hall_onnx_judge_20260726` (grounding only)  
**Canon:** `C:\code\QA\projects\FinancePackBench\BEST-PRACTICES.md` · `BENCHMARKS-HONEST.md` · `docs/2026-07-26-eye-to-eye-comparisons.md`

---

## TITLE

**Pack vs LangGraph vs AWS Bedrock — Who Actually Wins?**

*Subtitle:* Same mid finance fixture, seed 42, n=100 per lane. A job-by-job Race E board against a Bedrock AgentCore Runtime path (Guardrails + KB) — and how to read the numbers without turning a stubbed LLM counter into a win.

---

## BODY

> **Abstract.** Production agents fail at different layers — ingress abuse, orchestration/tooling, answer grounding, embed tax under concurrency, and warm retrieve latency. We ran a vendor-authored mid-tier finance-agent harness (**FinancePackBench**) that compares stacks **eye-to-eye by job**, not as a single “who wins AWS” score. On the General v1 board (`general_v1_pcl2a_20260725`, seed 42, n=100 per lane), a best-practice **Prism pack** lane (ChorusGraph + PrismGuard 0.1.10 + PrismShine 0.2.2, with PrismAPI on the PC lane) reached **100%** task success and **100%** prompt-injection block with **100%** benign allow. A LangGraph peer reached **92.5% / 85% / 100%**. An AWS Bedrock **AgentCore Runtime** lane (Guardrails + Knowledge Base + Lambda tools + Gemini via Identity) reached **100% / 45% / 100%**. Mean embedding calls fell from **4.20 to 0.70** on the PrismAPI lane versus a re-embed peer; a four-worker retrieve-only fan-out showed **20 vs 120** embed calls (**6.0×**). We disclose hosting split (**H2-phase2**: local Docker compose for pack/LangGraph · AgentCore on AWS), the non-comparability of AgentCore’s harness LLM counter, and a weak lexical **strict** grounding cell on Race E. This note explains method, topology, technologies, results, and how to interpret them.

### 1. Research question

Engineers (and marketers) often ask one question:

> Who is better — our stack, LangGraph, or AWS Bedrock AgentCore?

That question is ill-posed. Those systems are not interchangeable peers on every metric. AgentCore runs on AWS; our pack and LangGraph peers in this study ran in **local containers** on the same compose network as a shared Postgres. Bedrock does not expose a full, comparable per-turn LLM call ledger the way our instrumented local lanes do. Prompt injection and task success *are* comparable on a shared fixture. Latency and mean-LLM vs AgentCore are not.

So we asked a narrower set of questions:

1. On the **same mid finance fixture**, does a wired pack (Guard → ChorusGraph → Shine) match or beat a LangGraph+peer-guard stack on **task** and **PI**?
2. Against **AgentCore Runtime + Guardrails**, where does the pack win, tie, or lose — without claiming a hosting-fair speed win?
3. Does adding a **shared embedding provider (PrismAPI)** reduce embed calls without changing task/PI quality vs a re-embed pack lane?
4. What must readers **not** infer from the table?

### 2. How the test was created

#### 2.1 Fixture and suites

| Setting | Value |
|---------|--------|
| Harness | FinancePackBench mid |
| Fixture | `2026-07-23.mid` finance FAQ + planted PI / hallucination suites |
| Seed | **42** (paired across lanes) |
| n per lane | **100** (40 task · 20 PI attack · 10 PI benign · 30 hallucination) |
| Model | `gemini-2.5-flash` (BYO on local lanes; Identity on AgentCore) |
| Vendor | Insight ITS — **not** a third-party audit |

Each event records lane, suite, latency, LLM/embed counters (where instrumented), PI decision, grounding decision/score, and run metadata. Lane summaries and bootstrap CIs are written to `summary_*.json` and `COMPARISON_REPORT.md`.

#### 2.2 Lanes (what “peer” means)

| Lane | Role | Stack |
|------|------|--------|
| **PC** | Pack + shared embed dataplane | PrismGuard → ChorusGraph → PrismShine + **PrismAPI** client · shared Postgres · Cortex sidecar present (memory **not** scored) |
| **PN** | Pack control (re-embed) | Same pack quality path · **no** PrismAPI — re-embeds per worker |
| **L2** | Framework peer | **LangGraph** + re-embed adapter on **same** remote Postgres |
| **A1** | AWS managed peer | Bedrock **AgentCore Runtime** + **Guardrails** + **KB** (Aurora pgvector) + **Lambda** tools + Gemini via **AgentCore Identity** |

Pins frozen on the live run: `chorusgraph==1.3.0` · `prismguard==0.1.10` · `prismshine==0.2.2` · `prismlib-plus==0.8.0` · `prismcortex==0.3.0` · `langgraph==1.2.4`.

**Pack wiring (Tier 0):** ingress Guard **before** cache/tools/LLM; FAQ evidence in retrieval/history — not pasted into the user message; Shine on egress with evidence required. Mis-wiring (wrong Guard profile, FAQ in `message`) collapses task %. That is why this is a **systems** result, not a single-library microbench.

#### 2.3 Hosting topology (read this before the latency column)

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
    → Gemini via Identity (BYO Google key — not a Bedrock FM)
```

**What we did *not* run for this board:** identical Fargate containers for pack and AgentCore on one VPC (that was **H1**, deferred). So:

- Quality / PI / embeds among instrumented local lanes: **fair to compare**.
- Task/PI vs AgentCore on the **same fixture**: **fair to compare as product outcomes**.
- Latency or $/token vs AgentCore: **not** a victory claim under H2.
- AgentCore Memory: **OFF** (single-turn fairness). Classic Bedrock Agents: **not used**.

Same-day teardown was a hard gate: compose `down -v` + AWS inventory tagged `Project=FinancePackBench` → **0**.

#### 2.4 Supporting runs (same program, different jobs)

| Run ID | Job |
|--------|-----|
| `general_v1_pcl2a_20260725` | **Primary** — Race E General v1 (PC/PN/L2/A1) |
| `multiworker_embed_racee_20260725` | Fleet embed tax (4 workers × FAQ retrieves) |
| `mid_pla_faqfix_20260724` (+ A fixed) | Earlier classic P / L / A mid (Race A) |
| `driver_ablation_20260725` | Warm PrismDriver vs SQL retrieve (**separate** job) |
| `hall_onnx_judge_20260726` | Shine ONNX+judge hall arm only |

### 3. Technologies under test

| Layer | Pack path | Peer path |
|-------|-----------|-----------|
| Ingress / PI | **PrismGuard** 0.1.10 (`domain_pilot` + finance artifact on PI suite) | LLM Guard (classic mid) / AgentCore **Guardrails** |
| Orchestration | **ChorusGraph** 1.3.0 (native BSP runtime — not a LangGraph wrapper) | **LangGraph** 1.2.4 · AgentCore Runtime |
| Egress / grounding | **PrismShine** 0.2.2 (pass / flag / block + named gate) | HHEM / binary peers · AgentCore grounding signals |
| Embed dataplane | **PrismAPI** (PC) via `prismlib-plus` | Per-worker re-embed (PN/L2) |
| Memory | **PrismCortex** 0.3.0 sidecar — **health only** on this board | AgentCore Memory OFF |
| Data | Shared Postgres FAQ | Aurora KB with **identical FAQ bytes** (different retriever) |
| Model | Gemini 2.5 Flash | Same family via Identity on A1 |

PrismRAG was **excluded** from the core race (taxonomy remap ≠ transport). Race C (Driver ~353× vs SQL) is a **different job** — do not mix into the agent-quality table.

### 4. Results

#### 4.1 Agent quality + PI (Race E) — primary table

Run: `general_v1_pcl2a_20260725` · hosting **H2-phase2** · Lane A = **A1**.

| Lane | Task % | PI block % | Benign % | Mean embeds | Mean LLM† | Task P50 |
|------|--------|------------|----------|-------------|-----------|----------|
| **PC** (pack + PrismAPI) | **100** | **100** | **100** | **0.70** | 0.60 | 2895 ms *local* |
| **PN** (pack, re-embed) | **100** | **100** | **100** | 4.20 | 0.60 | 2900 ms *local* |
| **L2** (LangGraph) | 92.5 | 85 | 100 | 4.20 | 1.12 | 3602 ms *local* |
| **A1** (AgentCore) | **100** | **45** | 100 | — | 0.40‡ | 4264 ms *AWS* |

† Mean LLM is a fair efficiency signal **among local instrumented lanes**.  
‡ AgentCore’s harness LLM field is **not comparable** — internals are not fully exposed; the mid bake-off documents a **stubbed / hardcoded** successful-task counter. **Do not** claim “fewer LLM calls than Bedrock.”

**Bootstrap (PI attack, n=20):** PC **100%** [100, 100] · L2 **85%** [65, 100] · A1 **45%** [20, 70].

#### 4.2 What PC vs PN proves

PC and PN tied at **100 / 100 / 100**. PrismAPI did **not** create the security or task win. It removed embed work: **0.70 vs 4.20** mean embeds (−3.50 absolute; **~83%** relative reduction vs the re-embed pack lane). Multi-worker: **20 vs 120** (**6.0×**).

#### 4.3 Grounding — dual board (do not collapse to one %)

On Race E, **strict pass** (Shine/HHEM `pass` only) for PC/PN was **~10%** — a **losing cell** vs A1 binary **26.7%**. Mean Shine score on Race E was **~0.68** vs L2 peer **~0.15**. Allow (`pass|flag`) on pack was **100%** under Shine’s gray policy.

A follow-up hall-only run with ONNX spans + judge (`hall_onnx_judge_20260726`, n=30):

| Metric | Pack Shine (P) | Binary peer (L) |
|--------|----------------|-----------------|
| Strict pass | 30% | 30% |
| Allow | **100%** | 30% |
| Mean score | **0.54** | 0.30 |
| Expect agree (allow) | **100%** | 93.3% |

**PASS ≠ world-true.** Grounding here is a planted suite, not production RAG certification.

#### 4.4 Classic mid (Race A) — same PI story, simpler lanes

`mid_pla_faqfix_20260724` / A fixed: Pack **100/100/100** · LangGraph+LLM Guard **95/85/100** · AgentCore **100/45/100**. Efficiency **0.60 vs 1.11** mean LLM — **vs LangGraph only**.

### 5. How to understand the results

| If you care about… | Look at… | Correct reading |
|--------------------|----------|-----------------|
| “Is the agent safer on PI?” | PI block % + benign allow | Pack **best of three** on this fixture; AgentCore Guardrails **45%** is the soft cell |
| “Does work still get done?” | Task % | Pack **ties** AgentCore at 100%; **beats** LangGraph |
| “Did we cripple normal users?” | Benign allow | All three at **100%** here |
| “Is PrismAPI the quality hero?” | PC vs PN | **No** — quality tied; API wins **embed tax** |
| “Are we more efficient than LangGraph?” | Mean LLM PC/PN vs L2 | **Yes on this board** (0.60 vs ~1.1) |
| “Are we more efficient than Bedrock?” | — | **Unknown / not claimable** from this harness |
| “Are we faster than AgentCore?” | Task P50 | **Do not claim** — different hosts (H2) |
| “Is grounding solved?” | Strict vs allow vs mean score | Strict was weak on Race E; allow/mean tell a different story; HO-010 is hall-arm only |
| “Did Cortex win?” | — | **No memory suite scored** |

**Category belief (not jargon):** production agents need a **layered verdict path** — who checks ingress, who runs tools, who grounds the answer, who owns embeds at fleet scale — measured **per job**, not as one leaderboard row.

### 6. Limitations (publish with the table)

1. Vendor-authored harness.  
2. Hosting **H2-phase2** — no cross-host latency or $ win vs AgentCore.  
3. AgentCore LLM / cost fields not comparable (stub / BYO $0).  
4. Gemini via Identity ≠ Bedrock foundation model.  
5. Aurora KB ≠ PrismRAG.  
6. Cortex = health only.  
7. Grounding = planted suite; Race E strict pass is a disclosed lose.  
8. PI holdout size is small (20 attacks) — not “100% forever.”  
9. Not multi-cloud; not Classic Agents; Memory OFF on A.  
10. Race C Driver retrieve is a **separate** experiment.

### 7. Implications for practitioners

1. **Wire the pack first.** PN matching PC on quality means Guard → Chorus → Shine is the load-bearing path.  
2. **Add PrismAPI when workers share a KB** and you pay embed tax — not to “fix” task %.  
3. **Keep AgentCore as a named peer**, not a straw man — and say **A1 Runtime** when that is what you ran.  
4. **Refuse blended P50** and refuse LLM-efficiency headlines vs Bedrock until the meter is honest.  
5. **Scorecard before calendar** — reply **GRADE** for a Guardrail Scorecard pass on *your* prompts (process lock v0.4.6).

### 8. Reproduce

| Artifact | Location |
|----------|----------|
| Race E report | `FinancePackBench/results-archive/general_v1_pcl2a_20260725/COMPARISON_REPORT.md` |
| Best practices | `FinancePackBench/BEST-PRACTICES.md` |
| Eye-to-eye map | `FinancePackBench/docs/2026-07-26-eye-to-eye-comparisons.md` |
| Honest dossier | `FinancePackBench/BENCHMARKS-HONEST.md` |
| Pack landing (site) | https://www.insightits.com/products/prism-pack.html |
| Scorecard | https://github.com/insightitsGit/PrismGuard/blob/main/docs/scorecard.md |

---

## FEED TEASER notes

Pain-first · full value in body · links in first comment · soft CTA **GRADE** · one hero = pack PI / eye-to-eye method · product names after the insight.
