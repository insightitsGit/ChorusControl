# Side 1 Handoff Brief — www.insightits.com

| Field | Value |
|-------|-------|
| Audience | Website / Side 1 agent **and** Side 2 ChorusControl |
| Status | Contract live in Side 1 code; prod Azure routes may lag deploy |
| Companion | InsightitsAIAgent `docs/CHORUSCONTROL_SIDE1_LICENSE.md` · [ChorusControl-COMPLETE-DESIGN.md](./ChorusControl-COMPLETE-DESIGN.md) |
| Version | 1.2.0 |
| Date | July 2026 |

---

## 1. Why this handoff exists

**ChorusControl** is the self-hosted **Enterprise AI Operating System / AI Operations Platform** (Side 2). **www.insightits.com** is the commercial portal (Side 1).

| Side | Repo / surface | Responsibility |
|------|----------------|----------------|
| **Side 2** | `ChorusControl` (this project) | Self-hosted AI Ops Platform — mother + agents in customer VPC |
| **Side 1** | **www.insightits.com** (separate) | Commercial portal: sell, support, **issue** offline licenses, optional online validate |

Side 2 verifies licenses **offline first** (Ed25519). Connected installs **optionally** re-check Side 1 about every **14 days** for revocation. Air-gap never requires that call.

---

## 2. What Side 1 provides

1. Customer accounts / org identity (`sub`)
2. Stripe billing → `tier` / features / `max_nodes`
3. Ed25519-signed offline JWT (private key stays on Side 1)
4. License delivery UX (copy / download)
5. Support ticketing
6. **Optional online APIs** (below)

**Do not** implement Prism fleet control, Cortex, RAG taxonomy, Guard WAF, or audit sinks on Side 1.

---

## 3. Stable contract

### 3.1 Touchpoints

| Touchpoint | Side 2 | Side 1 |
|------------|--------|--------|
| License key | Paste Admin / `CHORUSCONTROL_LICENSE_KEY` | Issue + download |
| Support | `INSIGHTITS_SUPPORT_URL` | `/support` |
| Portal | `INSIGHTITS_PORTAL_URL` | Dashboard / billing |
| Side 1 API base | `CHORUSCONTROL_SIDE1_API_BASE_URL` (optional; default portal) | Local `http://127.0.0.1:5000` |

### 3.2 Cryptography (primary)

- Algorithm: **Ed25519 / EdDSA**
- Side 1 holds private key; Side 2 embeds public key
- **Offline verify is required** — air-gap works with zero network

### 3.3 Claims schema

```json
{
  "iss": "insightits.com",
  "sub": "customer-or-org-id",
  "iat": 1720000000,
  "exp": 1751536000,
  "tier": "enterprise",
  "max_nodes": 16,
  "max_tenants": 50,
  "features": ["trace.replay", "guard.shadow", "audit.export"],
  "license_id": "lic_..."
}
```

Default license length ~**90 days** (or Stripe period). Side 2 **14-day read-only grace** after `exp` (±24h clock skew).

### 3.3a Two meanings of “14 days”

| Meaning | Behavior |
|---------|----------|
| **Grace after `exp`** | Read-only mutations blocked; observe stays up |
| **Online re-check interval** | Connected mothers SHOULD call Side 1 validate ~every 14 days for revocation |

### 3.3b Online validate (optional — not a separate “14-day license URL”)

| Purpose | Method | Prod URL | Local |
|---------|--------|----------|-------|
| Public key + interval contract | `GET` | `https://www.insightits.com/api/choruscontrol/public-key` | `http://127.0.0.1:5000/api/choruscontrol/public-key` |
| Online validate / revoke status | `POST` | `https://www.insightits.com/api/choruscontrol/validate` | `http://127.0.0.1:5000/api/choruscontrol/validate` |

Validate body:

```json
{
  "licenseKey": "<CHORUSCONTROL_LICENSE_KEY>",
  "instanceId": "optional-stable-node-id",
  "productVersion": "1.2.0"
}
```

Side 2 guidance:

- Network failure → **keep last offline verdict** until `exp` + grace
- `status=revoked` → **fail closed** even if JWT still verifies
- `phoneHomeRequired` is always `false`; `offlineOk` always `true`
- Disable: `CHORUSCONTROL_LICENSE_ONLINE_CHECK=0`
- Force from UI/API: `POST /api/v1/admin/license/online-check`

### 3.4 Tier → features

| Tier | Features |
|------|----------|
| `starter` | Core UI, sleep, basic taxonomy |
| `enterprise` | + `trace.replay`, `guard.shadow`, `audit.export` |
| `sovereign` | Enterprise + air-gap SLA (commercial) |

---

## 4. Side 2 implementation (this repo)

- Offline verifier + middleware (fail-closed / grace)
- Admin license status / upload + **online_check** block
- Periodic sampler tick (~14d) + install-time check
- Air-gap safe when online check disabled or Side 1 unreachable

---

## 5. E2E test (local)

1. Start Side 1: `meeting-scheduler` → `python app.py` (:5000) with local Ed25519 hex env
2. Login `superadmin@insightits.com` / `superadmin12345` → issue ChorusControl JWT
3. Start Side 2 with that JWT as `CHORUSCONTROL_LICENSE_KEY` and:
   - `CHORUSCONTROL_SIDE1_API_BASE_URL=http://127.0.0.1:5000`
   - `CHORUSCONTROL_LICENSE_ONLINE_CHECK=1`
   - `CHORUSCONTROL_DEMO_MODE=0` (or `CHORUSCONTROL_LICENSE_ONLINE_CHECK_IN_DEMO=1`)
4. `POST /api/v1/admin/license/online-check` or curl Side 1 `/validate` directly

**Note:** Prod `GET …/public-key` may 404 until Side 1 Azure deploy; local Side 1 must be running for live E2E.

---

## 6. Non-goals / anti-patterns

- Do not put Stripe or ticket DB in ChorusControl
- Do not **require** Side 1 online to start mother
- Do not rename claims without coordinated version bump
- Do not embed Side 1 **private** signing key in Side 2

---

*Insight IT Solutions LLC — Side 1 handoff brief v1.2.0*
