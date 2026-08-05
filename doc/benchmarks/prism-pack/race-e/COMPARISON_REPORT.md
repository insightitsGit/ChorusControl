# FinancePackBench COMPARISON_REPORT — `general_v1_pcl2a_20260725`

**UTC:** 2026-07-26T00:03:49.147032+00:00  
**Tier:** mid  
**Seed:** 42  
**Lanes:** PC, PN, L2, A  
**Hosting:** H2-phase2  
**Lane A mode:** A1  
**Fixture version:** 2026-07-23.mid  
**n/lane:** 100  

## Disclosures

- Hosting class **H2-phase2** — do not claim cross-host latency victory unless H1.
- Lane A = **A1** (AgentCore Runtime + Guardrails + KB + tools + Gemini Identity).
- Gemini = BYO / Identity — **not** a Bedrock foundation model.
- KB (Aurora pgvector) ≠ PrismRAG; identical FAQ bytes, different retriever.
- Phase-2: PrismRAG **excluded** from core dataplane race (taxonomy remap ≠ transport).
- AgentCore Memory **OFF**; Classic Agents not used.
- Vendor-authored harness — not a neutral third-party audit.
- Tear down AWS resources after the run (see AWS-COST-HYGIENE).
- **Do not headline blended P50** — use suite-split latency below.
- **Cost:** Gemini BYO on PC/PN/L2; A1 Runtime may report $0 for model (Identity) — disclose.

## Cost scorecard (General v1)

| Lane | Total USD | Mean USD/turn | $/successful task | n task ok |
|------|-----------|---------------|-------------------|-----------|
| A | 0.00 | 0.00 | 0.00 | 40 |
| L2 | 0.01 | 0.00 | 0.00 | 37 |
| PC | 0.01 | 0.00 | 0.00 | 40 |
| PN | 0.01 | 0.00 | 0.00 | 40 |

## Lane summaries (blended — reference only)

| Lane | n | Task % | P50 | P95 | Mean LLM | Embed | Saved | Retr ms | PI block % | PI allow % | Grounding % |
|------|---|--------|-----|-----|----------|-------|-------|---------|------------|------------|-------------|
| A | 100 | 100.00 | 318.8 | 5583.6 | 0.40 | 0.00 | 0.00 | 0.0 | 45.00 | 100.00 | 26.67 |
| L2 | 100 | 92.50 | 166.4 | 4593.0 | 1.12 | 4.20 | 0.00 | 914.3 | 85.00 | 100.00 | 13.33 |
| PC | 100 | 100.00 | 31.4 | 3068.1 | 0.60 | 0.70 | 3.50 | 77.5 | 100.00 | 100.00 | 10.00 |
| PN | 100 | 100.00 | 40.1 | 3192.5 | 0.60 | 4.20 | 0.00 | 846.6 | 100.00 | 100.00 | 10.00 |

## Latency by suite (required for claims)

| Lane | Suite | n | P50 ms | P95 ms | Mean ms |
|------|-------|---|--------|--------|---------|
| A | task | 40 | 4263.5 | 6711.4 | 4463.4 |
| A | pi | 30 | 252.0 | 933.7 | 302.2 |
| A | hallucination | 30 | 308.2 | 344.7 | 289.3 |
| L2 | task | 40 | 3602.0 | 5259.0 | 3400.6 |
| L2 | pi | 30 | 64.3 | 87.0 | 66.1 |
| L2 | hallucination | 30 | 162.3 | 179.1 | 184.3 |
| PC | task | 40 | 2895.3 | 3133.2 | 2349.0 |
| PC | pi | 30 | 0.2 | 200.0 | 59.0 |
| PC | hallucination | 30 | 6.0 | 6.8 | 6.7 |
| PN | task | 40 | 2899.5 | 3342.8 | 2590.4 |
| PN | pi | 30 | 0.2 | 204.4 | 60.5 |
| PN | hallucination | 30 | 7.3 | 12.3 | 8.3 |

## 95% bootstrap CI (headline %)

| Lane | Metric | Point | Lo | Hi | n |
|------|--------|-------|----|----|---|
| A | task_success_pct | 100.00 | 100.00 | 100.00 | 40 |
| A | pi_attack_block_pct | 45.00 | 20.00 | 70.00 | 20 |
| A | pi_normal_allow_pct | 100.00 | 100.00 | 100.00 | 10 |
| A | grounding_pass_pct | 26.67 | 13.33 | 43.33 | 30 |
| L2 | task_success_pct | 92.50 | 82.50 | 100.00 | 40 |
| L2 | pi_attack_block_pct | 85.00 | 65.00 | 100.00 | 20 |
| L2 | pi_normal_allow_pct | 100.00 | 100.00 | 100.00 | 10 |
| L2 | grounding_pass_pct | 13.33 | 3.33 | 26.67 | 30 |
| PC | task_success_pct | 100.00 | 100.00 | 100.00 | 40 |
| PC | pi_attack_block_pct | 100.00 | 100.00 | 100.00 | 20 |
| PC | pi_normal_allow_pct | 100.00 | 100.00 | 100.00 | 10 |
| PC | grounding_pass_pct | 10.00 | 0.00 | 20.00 | 30 |
| PN | task_success_pct | 100.00 | 100.00 | 100.00 | 40 |
| PN | pi_attack_block_pct | 100.00 | 100.00 | 100.00 | 20 |
| PN | pi_normal_allow_pct | 100.00 | 100.00 | 100.00 | 10 |
| PN | grounding_pass_pct | 10.00 | 0.00 | 20.00 | 30 |

## Pairwise deltas (left − right)

### PC_vs_PN

| Metric | Left | Right | Δ |
|--------|------|-------|---|
| task_success_pct | 100.00 | 100.00 | 0.00 |
| latency_p50_ms | 31.41 | 40.11 | -8.69 |
| latency_p95_ms | 3068.13 | 3192.50 | -124.37 |
| mean_llm_calls | 0.60 | 0.60 | 0.00 |
| mean_tokens_in | 250.75 | 251.06 | -0.31 |
| mean_tokens_out | 46.63 | 46.58 | 0.05 |
| mean_cost_usd | 0.00 | 0.00 | -0.00 |
| total_cost_usd | 0.01 | 0.01 | -0.00 |
| cost_per_successful_task_usd | 0.00 | 0.00 | -0.00 |
| pi_attack_block_pct | 100.00 | 100.00 | 0.00 |
| pi_normal_allow_pct | 100.00 | 100.00 | 0.00 |
| grounding_pass_pct | 10.00 | 10.00 | 0.00 |
| mean_grounding_score | 0.68 | 0.68 | 0.00 |
| mean_embed_calls | 0.70 | 4.20 | -3.50 |
| mean_embed_calls_saved | 3.50 | 0.00 | 3.50 |
| mean_retrieval_ms | 77.55 | 846.63 | -769.08 |

### PC_vs_L2

| Metric | Left | Right | Δ |
|--------|------|-------|---|
| task_success_pct | 100.00 | 92.50 | 7.50 |
| latency_p50_ms | 31.41 | 166.43 | -135.02 |
| latency_p95_ms | 3068.13 | 4593.00 | -1524.87 |
| mean_llm_calls | 0.60 | 1.12 | -0.52 |
| mean_tokens_in | 250.75 | 368.39 | -117.64 |
| mean_tokens_out | 46.63 | 79.93 | -33.30 |
| mean_cost_usd | 0.00 | 0.00 | -0.00 |
| total_cost_usd | 0.01 | 0.01 | -0.00 |
| cost_per_successful_task_usd | 0.00 | 0.00 | -0.00 |
| pi_attack_block_pct | 100.00 | 85.00 | 15.00 |
| pi_normal_allow_pct | 100.00 | 100.00 | 0.00 |
| grounding_pass_pct | 10.00 | 13.33 | -3.33 |
| mean_grounding_score | 0.68 | 0.15 | 0.53 |
| mean_embed_calls | 0.70 | 4.20 | -3.50 |
| mean_embed_calls_saved | 3.50 | 0.00 | 3.50 |
| mean_retrieval_ms | 77.55 | 914.31 | -836.77 |

### PN_vs_L2

| Metric | Left | Right | Δ |
|--------|------|-------|---|
| task_success_pct | 100.00 | 92.50 | 7.50 |
| latency_p50_ms | 40.11 | 166.43 | -126.33 |
| latency_p95_ms | 3192.50 | 4593.00 | -1400.50 |
| mean_llm_calls | 0.60 | 1.12 | -0.52 |
| mean_tokens_in | 251.06 | 368.39 | -117.33 |
| mean_tokens_out | 46.58 | 79.93 | -33.35 |
| mean_cost_usd | 0.00 | 0.00 | -0.00 |
| total_cost_usd | 0.01 | 0.01 | -0.00 |
| cost_per_successful_task_usd | 0.00 | 0.00 | -0.00 |
| pi_attack_block_pct | 100.00 | 85.00 | 15.00 |
| pi_normal_allow_pct | 100.00 | 100.00 | 0.00 |
| grounding_pass_pct | 10.00 | 13.33 | -3.33 |
| mean_grounding_score | 0.68 | 0.15 | 0.53 |
| mean_embed_calls | 4.20 | 4.20 | 0.00 |
| mean_embed_calls_saved | 0.00 | 0.00 | 0.00 |
| mean_retrieval_ms | 846.63 | 914.31 | -67.68 |

### PC_vs_A

| Metric | Left | Right | Δ |
|--------|------|-------|---|
| task_success_pct | 100.00 | 100.00 | 0.00 |
| latency_p50_ms | 31.41 | 318.85 | -287.44 |
| latency_p95_ms | 3068.13 | 5583.57 | -2515.44 |
| mean_llm_calls | 0.60 | 0.40 | 0.20 |
| mean_tokens_in | 250.75 | 0.00 | 250.75 |
| mean_tokens_out | 46.63 | 0.00 | 46.63 |
| mean_cost_usd | 0.00 | 0.00 | 0.00 |
| total_cost_usd | 0.01 | 0.00 | 0.01 |
| cost_per_successful_task_usd | 0.00 | 0.00 | 0.00 |
| pi_attack_block_pct | 100.00 | 45.00 | 55.00 |
| pi_normal_allow_pct | 100.00 | 100.00 | 0.00 |
| grounding_pass_pct | 10.00 | 26.67 | -16.67 |
| mean_grounding_score | 0.68 | 0.27 | 0.41 |
| mean_embed_calls | 0.70 | 0.00 | 0.70 |
| mean_embed_calls_saved | 3.50 | 0.00 | 3.50 |
| mean_retrieval_ms | 77.55 | 0.00 | 77.55 |

### PN_vs_A

| Metric | Left | Right | Δ |
|--------|------|-------|---|
| task_success_pct | 100.00 | 100.00 | 0.00 |
| latency_p50_ms | 40.11 | 318.85 | -278.74 |
| latency_p95_ms | 3192.50 | 5583.57 | -2391.07 |
| mean_llm_calls | 0.60 | 0.40 | 0.20 |
| mean_tokens_in | 251.06 | 0.00 | 251.06 |
| mean_tokens_out | 46.58 | 0.00 | 46.58 |
| mean_cost_usd | 0.00 | 0.00 | 0.00 |
| total_cost_usd | 0.01 | 0.00 | 0.01 |
| cost_per_successful_task_usd | 0.00 | 0.00 | 0.00 |
| pi_attack_block_pct | 100.00 | 45.00 | 55.00 |
| pi_normal_allow_pct | 100.00 | 100.00 | 0.00 |
| grounding_pass_pct | 10.00 | 26.67 | -16.67 |
| mean_grounding_score | 0.68 | 0.27 | 0.41 |
| mean_embed_calls | 4.20 | 0.00 | 4.20 |
| mean_embed_calls_saved | 0.00 | 0.00 | 0.00 |
| mean_retrieval_ms | 846.63 | 0.00 | 846.63 |

### L2_vs_A

| Metric | Left | Right | Δ |
|--------|------|-------|---|
| task_success_pct | 92.50 | 100.00 | -7.50 |
| latency_p50_ms | 166.43 | 318.85 | -152.41 |
| latency_p95_ms | 4593.00 | 5583.57 | -990.57 |
| mean_llm_calls | 1.12 | 0.40 | 0.72 |
| mean_tokens_in | 368.39 | 0.00 | 368.39 |
| mean_tokens_out | 79.93 | 0.00 | 79.93 |
| mean_cost_usd | 0.00 | 0.00 | 0.00 |
| total_cost_usd | 0.01 | 0.00 | 0.01 |
| cost_per_successful_task_usd | 0.00 | 0.00 | 0.00 |
| pi_attack_block_pct | 85.00 | 45.00 | 40.00 |
| pi_normal_allow_pct | 100.00 | 100.00 | 0.00 |
| grounding_pass_pct | 13.33 | 26.67 | -13.33 |
| mean_grounding_score | 0.15 | 0.27 | -0.11 |
| mean_embed_calls | 4.20 | 0.00 | 4.20 |
| mean_embed_calls_saved | 0.00 | 0.00 | 0.00 |
| mean_retrieval_ms | 914.31 | 0.00 | 914.31 |

