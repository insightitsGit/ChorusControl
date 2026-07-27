# ChorusControl — Review Resolutions

Merged from [ChorusControl-Design-Review.md](./ChorusControl-Design-Review.md) into the build.  
**No phase gating** — see [ChorusControl-Implementation-Plan.md](./ChorusControl-Implementation-Plan.md).

| ID | Resolution |
|----|------------|
| R01 | HTTP/PrismAPI **primary** control transport; Fabric optional secondary |
| R02 | License grace **14 days** read-only + banner; clock skew ±24h |
| R03 | Ledger sampling (always ship errors/gates/verdicts; sample healthy); retention config |
| R04 | Fleet registry `memory_endpoint` per tenant / `memory` node role |
| R05 | SQLite default for registry/tokens/cascade; Postgres via `DATABASE_URL` |
| R06 | `choruscontrol audit-verify` + pubkey in SOC2 pack; `kid` on envelopes |
| R07 | Heartbeat version → feature matrix; NACK unsupported; pin tests |
| R08 | README coexistence: OTel watches; ChorusControl acts |
| I01 | Policy drift badge (intended vs actual caps) |
| I02 | Fleet consistency SLO from INVALIDATE_ACK timings |
| I03 | Per-node daily version snapshots from heartbeats |
| I04 | docker-compose mother + 2 demo agents in Phase-less Day-1 deliverable |
| I05 | UI title “AI Operations Platform”; OS language in docs until graph+score live |

*July 2026*
