# ChorusControl — AI Operations Platform

Cursor / agent overview for this repo (Side 2).

## What it is

Self-hosted **mother** (FastAPI + UI) + **fleet agent** for Prism / Chorus:

- Observe fleet health, caps, token-tax, AI Score, **Ops Logs**
- Govern Guard policies, license features, RBAC
- Correct memory conflicts via cascade + invalidation
- Trace Guard → Ledger → Shine with zero-token replay
- **Cortex** digest / recall / sleep (PrismCortex)
- **Admin Client AI chats** — end-user session history; compact via PrismCortex
- **Ops Assistant** — teaches every dashboard value; gated execute for **all primary tab actions** ([Ops-Assistant-Actions.md](./Ops-Assistant-Actions.md))

## Layout

```
choruscontrol/
  server.py          # mother app
  api/routes.py      # /api/v1/*
  agent/             # background agent + ledger exporter
  adapters/          # Null + optional live Prism ports
  services/          # caps, graph, traces, doctor, client_chats, assistant, …
  ui/                # Jinja shell + static app.js/css
doc/                 # design + Side 1 handoff (COMPLETE-DESIGN v1.8)
```

## Key design refs

- [ChorusControl-COMPLETE-DESIGN.md](./ChorusControl-COMPLETE-DESIGN.md) §3.7.4a, §11.6
- [Client-Chats.md](./Client-Chats.md)
- [Ops-Assistant.md](./Ops-Assistant.md)
- [Ops-Assistant-Actions.md](./Ops-Assistant-Actions.md) — per-tab run prompts

## Commands

- `choruscontrol serve`
- `choruscontrol doctor --mode mother|agent`
- `choruscontrol audit-verify <jsonl> --pubkey <pem>`
- `choruscontrol-agent`

## Non-goals here

- insightits.com / Stripe / license **issuance** → Side 1 handoff
- InsightPlugIn SMS, VectorBridge deep alerts → deferred

## Auth

Bearer admin token (or OIDC when configured). Mutations respect license grace + RBAC.
