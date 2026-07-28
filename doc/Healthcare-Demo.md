# Aurora Health — local full-stack demo

Mother + **Postgres audit dual-write** + three fleet agents (clinical GREEN, pharmacy BLUE, edge ORANGE),
clinical Guard policy, DEMO med-recon cascade, incidents, traces.

> **DEMO only.** No real PHI. Lexicon and traces are labeled illustrative.

## Quick start

```bash
docker compose -f docker-compose.healthcare.yml up --build
```

Open:

| Surface | URL / value |
|---------|-------------|
| Overview | http://127.0.0.1:8443/overview |
| Admin | http://127.0.0.1:8443/admin |
| Bearer token | `healthcare-demo-token` |
| API docs | http://127.0.0.1:8443/docs |

Paste the token in the UI (localStorage `cc_token`) or:

```bash
curl -H "Authorization: Bearer healthcare-demo-token" http://127.0.0.1:8443/api/v1/health/caps
```

## What the seed installs

| Piece | Detail |
|-------|--------|
| Tenants | `aurora-health`, `aurora-pharmacy` |
| Guard | `clinical_hub` preset — ingress `clinical_chat`, law ONNX off |
| Lexicon | MRN, med recon, discharge, allergy, prior_auth (DEMO labels) |
| Traces | Seeded clinical Guard → Ledger → Shine wires |
| Incident | Medication reconciliation conflict (DEMO) |
| Cascade | Invalidates `t:med_recon`, discharge, clinical guidelines partition |
| Agents | `aurora-clinical-green`, `aurora-pharmacy-blue`, `aurora-edge-orange` |

## Explore the six tabs

1. **Overview** — AI Score, fleet topology (3 nodes), live pipeline viz, WS fleet updates  
2. **Trace** — open a clinical run; Replay (zero-token)  
3. **Taxonomy** — warm / reindex jobs for clinical partitions  
4. **Cortex** (`/cortex`) — PrismCortex activity log, memory-graph chunks, facts/edges, digest / recall / sleep (seeded for `aurora-health`)  
5. **Guard** — clinical policy + shadow compare  
6. **Logs** — mother ops log bus (audit / fleet / agent)  
7. **Admin** — license, doctor, stack licenses, tenants, **Client AI chats** (end-user sessions + Compact), SOC2 export, recommendations  

Ops Assistant (FAB): **Guard → ChorusGraph → Shine** wire on every ask, then plain-English
answers from live telemetry. Can **teach** Client AI chats / Cortex and **gated-execute**
`chats.*` / `cortex.*` after Confirm. Rail **Light / Dark** theme switch.

## Re-seed against a running mother

```bash
set CHORUSCONTROL_MOTHER_URL=http://127.0.0.1:8443
set CHORUSCONTROL_ADMIN_TOKEN=healthcare-demo-token
set JOIN_TOKEN_FILE=./join_token.txt
python scripts/healthcare_demo_seed.py
```

## Tear down

```bash
docker compose -f docker-compose.healthcare.yml down -v
```

## Learning gaps

Use this demo to observe honest NullAdapter labels, pin floors in Doctor, OIDC-off token auth,
and anything still stubbed until live Prism packs are installed — see
[ChorusControl-Implementation-Gap-Report.md](./ChorusControl-Implementation-Gap-Report.md).
