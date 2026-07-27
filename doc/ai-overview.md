# ChorusControl — AI Operations Platform

Cursor / agent overview for this repo (Side 2).

## What it is

Self-hosted **mother** (FastAPI + UI) + **fleet agent** for Prism / Chorus:

- Observe fleet health, caps, token-tax, AI Score
- Govern Guard policies, license features, RBAC
- Correct memory conflicts via cascade + invalidation
- Trace Guard → Ledger → Shine with zero-token replay

## Layout

```
choruscontrol/
  server.py          # mother app
  api/routes.py      # /api/v1/*
  agent/             # background agent + ledger exporter
  adapters/          # Null + optional live Prism ports
  services/          # caps, graph, traces, doctor, policy
  ui/                # Jinja shell + static app.js/css
doc/                 # design + Side 1 handoff
```

## Commands

- `choruscontrol serve`
- `choruscontrol doctor --mode mother|agent`
- `choruscontrol audit-verify <jsonl> --pubkey <pem>`
- `choruscontrol-agent`

## Non-goals here

- insightits.com / Stripe / license **issuance** → Side 1 handoff
- InsightPlugIn SMS, VectorBridge deep alerts → deferred

## Auth

`Authorization: Bearer <CHORUSCONTROL_ADMIN_TOKEN>`  
Optional role: `token:operator` or `token|user|role`.
