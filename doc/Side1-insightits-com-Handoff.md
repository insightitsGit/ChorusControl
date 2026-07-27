# Side 1 Handoff Brief — www.insightits.com

| Field | Value |
|-------|-------|
| Audience | Future Cursor / engineering agent working on **www.insightits.com** |
| Status | Deferred — do **not** implement in the ChorusControl repo; **hand to website/Side 1 agent** |
| Owner (today) | ChorusControl team defines the **contract**; website team implements later |
| Companion | [ChorusControl-Design-Gaps-and-Solutions.md](./ChorusControl-Design-Gaps-and-Solutions.md) · [ChorusControl-COMPLETE-DESIGN.md](./ChorusControl-COMPLETE-DESIGN.md) |
| Version | 1.1.0 |
| Date | July 2026 |

---

## 1. Why this handoff exists

**ChorusControl** is the self-hosted **Enterprise AI Operating System / AI Operations Platform** (Side 2). **www.insightits.com** is the commercial portal (Side 1).

ChorusControl is a **two-sided** product family:

| Side | Repo / surface | Responsibility |
|------|----------------|----------------|
| **Side 2** | `ChorusControl` (this project) | Self-hosted **AI Operations Platform** — mother + agents in customer VPC |
| **Side 1** | **www.insightits.com** (separate) | Commercial portal: sell, support, and **issue** offline licenses |

Side 2 is built **now** in this folder. Side 1 is a **future handoff** to the insightits.com agent. The two sides must agree on a stable interface so license keys issued on the website validate offline inside ChorusControl with **zero phone-home**.

---

## 2. What the insightits.com agent will build (later)

When handed this brief, implement on the **website / portal** stack (not inside ChorusControl):

1. **Customer accounts** — org identity tied to `sub` / customer id in license claims.
2. **Stripe billing** — plans mapped to ChorusControl `tier` and feature entitlements.
3. **License issuance** — Ed25519-signed offline JWT (or compact JWS) matching the claim schema below; private key stays on Side 1 only.
4. **License delivery UX** — customer can copy/download the key to paste into ChorusControl Admin → License.
5. **Support ticketing** — hosted tickets; ChorusControl only deep-links here.
6. **Optional** — license history, renewals, seat/node upgrades that re-issue JWTs with updated `max_nodes` / `exp` / `features`.

**Do not** implement: Prism fleet control, Cortex sleep, RAG taxonomy UI, Guard WAF console, or audit sinks. Those belong exclusively to Side 2.

---

## 3. Stable contract Side 2 already depends on

The ChorusControl product will verify licenses using this contract. Side 1 **must** issue keys that satisfy it.

### 3.1 Environment / UX touchpoints on Side 2

| Touchpoint | Side 2 behavior | Side 1 must provide |
|------------|-----------------|---------------------|
| License key | Customer pastes into Admin or sets `CHORUSCONTROL_LICENSE_KEY` | Issuance + download/copy UI |
| Support link | `INSIGHTITS_SUPPORT_URL` (default `https://www.insightits.com/support`) | Working support entry URL |
| Account / billing link (optional) | Configurable portal URL | Customer billing page |

### 3.2 Cryptography

- Algorithm: **Ed25519**
- Side 1 holds the **private** signing key (HSM or secrets manager recommended).
- Side 2 embeds / ships the matching **public** key (via `chorusmesh.license` or equivalent adapter).
- Validation is **100% offline** — no callback to insightits.com at verify time.

### 3.3 License claims schema (must match Side 2)

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

| Claim | Rules |
|-------|--------|
| `iss` | Constant issuer string Side 2 expects (`insightits.com`) |
| `sub` | Stable customer/org id |
| `exp` | Unix seconds; Side 2 fail-closes when expired |
| `tier` | One of `starter` \| `enterprise` \| `sovereign` |
| `max_nodes` | Enforced against Fabric peer / worker registration |
| `max_tenants` | Enforced on tenant create in ChorusControl |
| `features` | Feature flags; unknown flags ignored by older Side 2 builds |
| `license_id` | Unique id for support / revocation *records on Side 1* (Side 2 does not phone home to revoke) |

**Revocation note:** True online revocation requires phone-home or short `exp` + re-issue. Prefer short-lived renewals or documented air-gap policy; do not assume Side 2 can check a CRL at runtime.

### 3.3a Grace window (Side 2 — R02)

Side 2 applies a **grace window** after `exp` (default **14 days**):

- Platform stays up for **read** (observe fleet, caps, traces).
- **Mutations blocked** (policy, cascade, jobs, command dispatch).
- Loud UI banner; renew via Side 1 portal / deep link.
- Clock skew tolerance **±24 hours** on `exp`/`iat`.

Side 1 renewal UX should warn customers before grace ends and support short-`exp` re-issue for air-gap.

### 3.4 Tier → feature mapping (recommended default)

| Tier | Suggested features |
|------|--------------------|
| `starter` | Core UI, sleep, basic taxonomy |
| `enterprise` | + `trace.replay`, `guard.shadow`, `audit.export` |
| `sovereign` | All enterprise + air-gap support SLAs (commercial only) |

Side 1 billing products should map 1:1 to these tiers so Stripe plan changes produce correct JWTs.

---

## 4. What Side 2 delivers before handoff

The ChorusControl repo will ship:

- Offline verifier + middleware (fail-closed).
- Admin license status / upload UI.
- Deep link to support URL.
- Dev/test keypair workflow so Side 2 can be QA’d **before** the website issues production keys.
- This handoff brief kept in sync when claim schema changes (version bump + changelog entry).

---

## 5. Handoff checklist (when website work starts)

- [ ] Confirm Ed25519 key ceremony; publish public key into `chorusmesh.license` / Side 2 release.
- [ ] Implement issuer producing the claim schema in §3.3.
- [ ] Map Stripe products → `tier` / `max_nodes` / `features`.
- [ ] Customer “copy license key” UX.
- [ ] Support URL live at the configured default (or update Side 2 default).
- [ ] Cross-team test: key issued on insightits.com validates in ChorusControl with network disabled.
- [ ] Document renewal / upgrade re-issue flow for customers.

---

## 6. Non-goals / anti-patterns

- Do not put Stripe or ticket DB code into the ChorusControl container.
- Do not require ChorusControl to call insightits.com APIs to start.
- Do not change claim field names without a coordinated Side 2 version bump.
- Do not embed the **private** signing key in Side 2 images or this repo.

---

*Insight IT Solutions LLC — Side 1 handoff brief for www.insightits.com*
