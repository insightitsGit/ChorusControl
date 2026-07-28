# Ops Assistant — plain-English dashboard literacy

The mother **Ops Assistant** teaches values shown on every primary tab using **live telemetry** (rule/template answers + snapshot numbers). It does **not** invent world-true Guard PASS / Shine PASS.

## How to use

1. Open any tab → Ops Assistant (rail or Chat FAB).
2. Use the **learn-this-screen** chips for that tab, or ask freely.
3. Answers include: meaning, **live value**, healthy/unhealthy, optional next tab/action.

## Example questions by tab

| Tab | Ask |
|-----|-----|
| Overview | Explain scores · Why is Performance 0? · Why is Reliability low? · Explain L0–L5 · What does cascade completed mean? · Explain GREEN vs ORANGE |
| Trace | What is zero-token replay? · What is a run_id? · What do wire stages mean? · What is the Route Ledger? |
| Taxonomy | What does Taxonomy engine prismrag-patch mean? · What is a partition version? · What does chunk staleness mean? · What is taxonomy_packs.ready? |
| Cortex | What does Cortex digest committed mean? · What does recall mean? · What does sleep consolidated mean? |
| Guard | What is Guard shadow compare? · What does ingress_profile mean? · What is the lexicon for? |
| Logs | What are Ops Logs? · What do source / level / node filters mean? |
| Admin | What do pin floors mean? Core vs optional? · What is taxonomy_packs.ready? · What does license grace mean? · What is the SOC2 export zip? |

## Grounding rules

- Snapshot fields come from the same APIs the UI uses (`dashboard_snapshot` in `services/assistant.py`).
- DEMO / NullAdapters stay labeled honestly.
- Glossaries live in `services/assistant_glossary.py` (`TAXONOMY_PLAIN`, `TRACE_PLAIN`, `GUARD_PLAIN`, `CORTEX_PLAIN`, `DOCTOR_PLAIN`, `LOGS_PLAIN`, …).

## Verification

```bash
python -m pytest tests/test_assistant_ho009.py tests/test_assistant_dashboard.py -q
```
