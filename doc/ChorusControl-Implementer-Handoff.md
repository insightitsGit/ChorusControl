# ChorusControl — Implementer Handoff: Closing the Design Gaps

| Field | Value |
|-------|-------|
| Audience | Implementer agent working in **this repo** (`ChorusControl`, Side 2) |
| Source of truth | [ChorusControl-Implementation-Gap-Report.md](./ChorusControl-Implementation-Gap-Report.md) (the audit) · [ChorusControl-COMPLETE-DESIGN.md](./ChorusControl-COMPLETE-DESIGN.md) (design, Part B) |
| Baseline at handoff | **34/34** tests passing (`pytest -q`); UI themed (dark/light) — do not regress either |
| Version | 1.1.0 |
| Date | July 2026 |
| Status | **WP1–WP12 implemented** — see gap report |

---

## 0. Ground rules (do not violate)

1. **No phone-home.** License verification stays 100% offline. Never add network calls to insightits.com at runtime.
2. **Zero hot-path latency.** Nothing on the agent may block invoke/digest/recall. `tests/test_hotpath_latency.py` must keep passing.
3. **HTTP is the primary control transport** (decision R01). Fabric is optional (`[fabric]` extra); never make it required.
4. **Honest NACK / honest caps.** If an adapter or feature is unavailable, say so — never fake success (repo rule: never fake any implementation).
5. **Every mutating route** must: check RBAC (`require_role`), respect `_grace_block(s)`, and write an audit envelope via `s.audit.log_action`.
6. Do not push to git without the owner's permission.
7. Keep the existing UI contract: tab pages render `ui/templates/shell.html`; JS fetches `/api/v1/...` with `Authorization: Bearer <token>`.

### Key code anchors

| Thing | Where |
|-------|-------|
| All API routes | `choruscontrol/api/routes.py` (single `APIRouter(prefix="/api/v1")`) |
| RBAC dependency | `choruscontrol/auth/rbac.py` → `require_role(min_role)` |
| Feature check (exists, unused) | `choruscontrol/license/verifier.py` → `LicenseVerifier.has_feature(status, feature)` |
| Grace guard | `routes.py` → `_grace_block(s)` |
| License middleware + open paths | `choruscontrol/server.py` |
| Fleet registry / join / commands | `choruscontrol/fleet/registry.py` |
| Agent runtime / ledger / transport | `choruscontrol/agent/{runtime,ledger,transport}.py` |
| SQLite store + schema | `choruscontrol/persistence/__init__.py` |
| Settings | `choruscontrol/config.py` (env prefix `CHORUSCONTROL_`) |
| Job queue | `choruscontrol/engine/job_queue.py`; handlers registered in `app_state.py` |
| SOC2 zip | `routes.py` → `soc2_export` (`GET /api/v1/admin/soc2-export`) |

---

## 1. Work packages (in priority order)

### WP1 — Enforce license feature gates (§3.2) · P0

`has_feature()` exists but only the assistant checks it. Add a FastAPI dependency and apply it:

- Add `require_feature(feature: str)` next to `require_role` (composable; return 403 `{"detail": "FEATURE_NOT_LICENSED", "feature": ...}`).
- Gate at minimum: `trace.replay` → `POST /traces/{id}/replay`; `guard.shadow` → shadow compare/promote; `audit.export` → `soc2_export` (and WP4's export route).
- In **demo mode** (`settings.demo_mode`), gates pass but responses include `"demo": true` (consistent with existing honesty pattern).
- Tier→feature defaults live in [Side1-insightits-com-Handoff.md](./Side1-insightits-com-Handoff.md) §3.4.

**Tests:** license without feature → 403 on gated route; with feature → 200; demo mode → 200 + labeled.

### WP2 — Tenant CRUD + `max_tenants` enforcement (§3.2, §3.7.6) · P0

- New table `tenants(tenant_id TEXT PRIMARY KEY, name TEXT, created_at REAL, settings_json TEXT)` in the SQLite store.
- Routes: `GET/POST /api/v1/admin/tenants` (admin), `DELETE /api/v1/admin/tenants/{id}` (admin). POST enforces `license_status.claims.max_tenants` → 403 `TENANT_LIMIT` when at cap. Audit all mutations.
- Seed `default` tenant on first boot.

**Tests:** create under cap ok; at cap → 403; delete audited.

### WP3 — TLS required for out-of-network agents (§3.19.5) · P0 (security)

- On `POST /fleet/join`: if `network_zone == "external"` and the effective scheme is not HTTPS (check `request.url.scheme` and `x-forwarded-proto`), reject 403 `TLS_REQUIRED` — unless `CHORUSCONTROL_ALLOW_INSECURE_EXTERNAL=1` (new setting, default off, logged loudly).
- Agent side (`agent/runtime.py`): warn (do not crash) when `network_zone=external` and `mother_url` is `http://`.

**Tests:** external join over plain HTTP → 403; with override env → allowed; internal zone unaffected.

### WP4 — SOC2 pack completeness + audit export (§3.18, §3.6) · P1

Extend the zip in `soc2_export`:

- Add `caps_snapshot.json` (call the same service as `GET /health/caps`).
- Add `audit_public_key.pem` (the verifying key for the envelopes; from the audit logger's keypair).
- **Redact** license claims: keep `tier`, `exp`, `max_nodes`, `features`; drop/mask `sub` and `license_id`.
- Add route alias `GET /api/v1/admin/export/soc2-pack` (design name) delegating to the same handler; keep the old path.
- Add `GET /api/v1/admin/audit/export?since=<ts>` streaming raw JSONL (admin + `audit.export` gate from WP1).

**Tests:** unzip in-test and assert member names; verify one envelope against the included PEM; redaction asserted.

### WP5 — Stack license console (§3.16) · P1

- New `choruscontrol/license/stack.py`: read env keys `CHORUSGRAPH_LICENSE_KEY`, `PRISMGUARD_LICENSE_KEY`, `PRISMSHINE_LICENSE_KEY`, `PRISMCORTEX_LICENSE_KEY`, `PRISMRAG_LICENSE_KEY`, `CHORUSMESH_LICENSE_KEY`; parse exp/tier where the key is a JWT, else report `unknown_format`. Absent key → `not_configured` (honest, not an error).
- Route: `GET /api/v1/admin/stack-licenses` (viewer).
- UI: add a "Stack licenses" section card to the Admin tab (`renderAdmin` in `ui/static/app.js`, reuse the `section(...)` + `table.data` pattern).

**Tests:** parses a dev-signed JWT; absent → `not_configured`.

### WP6 — License upload + store (§3.2) · P1

- `choruscontrol/license/store.py`: persist an uploaded key to `<data_dir>/license.key`; precedence: stored file > `CHORUSCONTROL_LICENSE_KEY` env.
- Route: `POST /api/v1/admin/license` (admin, body `{"license_key": "..."}`) → verify first; reject invalid keys with the verifier's message; on success persist + refresh `cc.license_status` + audit.
- UI: textarea + "Install license" button in the Admin → License card.

**Tests:** upload valid dev key → state `valid` and survives restart (reuse restart-soak pattern); invalid → 400, state unchanged.

### WP7 — `WS /api/v1/fleet/live` (§3.19.8) · P2

- Mirror the existing `traces_live` WebSocket pattern: push topology snapshots on join/heartbeat/revoke/ack events (a simple asyncio broadcast set on `FleetRegistry` is fine; poll-fallback stays).
- UI: on the Overview, subscribe and re-render `CCViz.renderFleetTopology` on message (keep initial fetch as fallback).

**Tests:** ws client receives an event after a heartbeat.

### WP8 — Agent commands: `REQUEST_METRICS`, `DRAIN`, `REVOKE`; rename `RUN_REINDEX` (§3.19.6) · P2

- Accept both `REINDEX` and `RUN_REINDEX` on dispatch (design name is `RUN_REINDEX`; keep the old one for compat).
- `REQUEST_METRICS`: agent replies via existing ack path with a metrics snapshot (ledger queue depth, `ledger_dropped_total`, uptime).
- `DRAIN`: agent flushes its ledger buffer then acks.
- `REVOKE`: agent receives it, stops heartbeating, exits cleanly (mother already has `DELETE /fleet/nodes/{id}`; dispatch the command on revoke).
- Expose `agent_ledger_dropped_total` in heartbeat payload → surface in `GET /fleet/topology` and the Overview fleet detail panel (§3.19.6b).

**Tests:** each command round-trips through dispatch → poll → ack with honest NACK when unsupported.

### WP9 — Trace retention/sampling enforcement (R03, §3.7.2) · P2

- Fix the `sampled` column: write `1` when an entry is kept by sampling.
- Add a periodic purge task (piggyback on the metrics sampler loop in `app_state.py`): delete trace entries older than `trace_retention_days` and enforce the row-count quota.

**Tests:** insert old rows → purge removes them; sampled flag correct at rate 1.0 and 0.0.

### WP10 — Cascade completeness (§3.11, §3.5) · P3

- Add `cascade.run` as a queued job type (wraps `CascadeService.run`) so cascades respect the per-tenant mutex.
- `cascade.auto`: poll Cortex adapter for unresolved conflicts (Null adapter: no-op) and auto-open incidents; full `on_event` push can wait for a live Cortex.
- Surface `CACHE_PREDATES_FACT_UPDATE` in trace/replay responses when the cascade timestamp postdates a cached entry.

### WP11 — Doctor exit codes + compose Postgres (§3.17, §3.8) · P3

- `choruscontrol doctor`: exit 1 when license invalid (non-demo), pin floor violated, or (mother) store unwritable; keep JSON output.
- `docker-compose.yml`: add commented-out `postgres` service + `DATABASE_URL` wiring; make Dockerfiles multi-stage (builder → slim runtime).

**Tests:** doctor exit code via subprocess in a failing config.

### WP12 — Design-doc consistency edits (no code) · P3

Update `ChorusControl-COMPLETE-DESIGN.md`:

1. Part A hard rules + Decision Log: transport = **HTTP primary, Fabric optional** (R01).
2. §3.2 prose: replace hard fail-closed with the 14-day read-only **grace** policy (R02).
3. Record SOC2 path decision (`/admin/soc2-export` + alias) in the Decision Log.
4. Record the frontend decision: custom themed design system (light/dark) instead of Tailwind.

---

## 2. Deliberately out of scope

- **Side 1** (Stripe, issuance portal, support ticketing) — see [Side1-insightits-com-Handoff.md](./Side1-insightits-com-Handoff.md).
- **Fabric steady-state transport** — keep the stub honest until `chorus-fabric` is verifiable in CI (R01/R07 dual-backend CI is a separate effort).
- **RBAC user-management UI** — local token + OIDC role claims are the shipped model; full user CRUD only if a customer requires it.
- Rewriting the consolidated module layout (`api/routes.py`, `adapters/nulls.py`, …) into the design's many-small-files layout — cosmetic, not worth the churn.

## 3. Definition of done (per work package)

- New/changed routes have RBAC + grace + audit + (where applicable) feature gates.
- Tests added in `tests/` covering the happy path **and** the enforcement/failure path; `pytest -q` fully green.
- `ruff` clean; no new dependencies without a floor pin in `pyproject.toml`.
- Gap report row updated (flip ❌/⚠️ → ✅ in [ChorusControl-Implementation-Gap-Report.md](./ChorusControl-Implementation-Gap-Report.md)).
- UI additions follow the existing design system (`section(...)` helper, `table.data`, CSS custom properties — both themes must look right).

---

*Insight IT Solutions LLC — implementer handoff for ChorusControl (Side 2)*
