# Prism Pack family benchmarks (hosted under ChorusControl)

**ChorusControl** is the self-hosted ops / governance plane for the **Prism Pack**.  
This folder is the **job-by-eye proof of the pack** that plane is built to operate and observe — so enterprise buyers find stack evidence under one roof.

**Primary narrative (posted research note):**  
[`RESEARCH-NOTE-pack-vs-langgraph-vs-aws-bedrock.md`](race-e/RESEARCH-NOTE-pack-vs-langgraph-vs-aws-bedrock.md)  
**Machine report:** [`race-e/COMPARISON_REPORT.md`](race-e/COMPARISON_REPORT.md)  
**Run:** `general_v1_pcl2a_20260725` · seed **42** · n=100/lane · hosting **H2-phase2**

```
proof · prism-pack · race-e · hosted-under:choruscontrol · measured:pack-lanes
```

---

## Claims guard

| Say | Do **not** say |
|-----|----------------|
| Pack (Guard → ChorusGraph → Shine ± PrismAPI) vs LangGraph vs Bedrock AgentCore path | “ChorusControl beat Bedrock / LangGraph” |
| Evidence for the stack CC governs | “Race E measured the ChorusControl UI” |
| Soft CTA: **CONTROL** (enterprise roof) · **GRADE** / Scorecard for PI | Cold Calendly · “beat AWS overall” |
| Disclosures: H2 host · grounding strict weak cell · AgentCore LLM counter not comparable | Cross-host latency win · fewer LLM calls than Bedrock |

---

## Primary board (from research note)

| Lane | Task % | PI block % | Benign % | Mean embeds | Notes |
|------|--------|------------|----------|-------------|--------|
| **PC** pack + PrismAPI | **100** | **100** | **100** | **0.70** | Local Docker |
| **PN** pack re-embed | **100** | **100** | **100** | 4.20 | Quality ties PC |
| **L2** LangGraph | 92.5 | 85 | 100 | 4.20 | Same Postgres |
| **A1** AgentCore+Guardrails+KB | **100** | **45** | 100 | — | AWS · PI soft cell |

**Fair:** task · PI · benign · PC vs PN embeds · mean LLM among **local** lanes.  
**Not fair:** latency vs AWS · “fewer LLM calls than Bedrock.”  
**Disclose:** Race E strict grounding ~10% (weak cell) · PASS ≠ world-true.

Pins: `chorusgraph==1.3.0` · `prismguard==0.1.10` · `prismshine==0.2.2`

---

## Links

| Asset | URL |
|-------|-----|
| Pack landing | https://www.insightits.com/products/prism-pack.html |
| ChorusControl landing | https://www.insightits.com/products/choruscontrol.html |
| Guardrail Scorecard (GRADE) | https://github.com/insightitsGit/PrismGuard/blob/main/docs/scorecard.md |
| This research note (GH) | [race-e/RESEARCH-NOTE-…](race-e/RESEARCH-NOTE-pack-vs-langgraph-vs-aws-bedrock.md) |

Marketing source article: `Marketing/kb/articles/financepackbench/ARTICLE-3-pack-vs-langgraph-vs-agentcore-race-e.md`  
LI/X paste pack: `LINKEDIN-X-POST-ARTICLE-3-RACE-E.md`
