# Ops Assistant — plain-English dashboard literacy

The mother **Ops Assistant** teaches values shown on every primary tab using **live telemetry** (rule/template answers + snapshot numbers). It does **not** invent world-true Guard PASS / Shine PASS.

It can also **gated-execute** the same actions as tab buttons. Full prompt → `execute.type` map: **[Ops-Assistant-Actions.md](./Ops-Assistant-Actions.md)** (agent KB; code: `assistant_actions.py`).

## How to use

1. Open any tab → Ops Assistant (rail or Chat FAB).
2. Use the **learn-this-screen** chips for that tab, or ask freely.
3. Answers include: meaning, **live value**, healthy/unhealthy, optional next tab/action.
4. When the answer proposes **gated actions**, click the button → Confirm — same APIs as the UI (audit logged).
5. Ask **“What can you do on {tab}?”** for runnable prompts on that screen.

## Example questions by tab

| Tab | Teach | Run (Confirm) |
|-----|-------|----------------|
| Overview | Explain scores · Why is Performance 0? · Cascade meaning · GREEN vs ORANGE | **Run correction cascade** · Open incident · Compliance scan · Blast radius |
| Trace | Zero-token replay · run_id · wire stages | **Seed demo trace** · **Replay the trace** |
| Taxonomy | Engine · partition version · staleness | **Reindex taxonomy** · **Warm partition** · Search taxonomy |
| Cortex | Digest / recall / sleep meaning | **Run cortex sleep** · Run cortex digest · Recall / explain |
| Guard | Shadow compare · ingress_profile | **Run shadow compare** · Save guard policy |
| Logs | Ops logs · sources · levels | **Show fleet logs** · Search ops logs |
| Admin | Pin floors · license · Client AI chats | **Create join token** · Compliance scan · **Compact raw client chat sessions** · List client chats · Doctor |

## Client AI chats (Admin) — teach + execute

End-user sessions are **not** Ops Assistant history. See [Client-Chats.md](./Client-Chats.md).

## Grounding rules

- Snapshot fields come from `dashboard_snapshot` (including `chats`).
- DEMO / NullAdapters stay labeled honestly.
- Glossaries: `assistant_glossary.py`. Actions: `assistant_actions.py`.

## Verification

```bash
python -m pytest tests/test_assistant_ho009.py tests/test_assistant_dashboard.py tests/test_assistant_client_chats.py tests/test_assistant_actions_catalog.py -q
```
