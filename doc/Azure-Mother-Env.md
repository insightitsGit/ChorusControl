# Azure / production env checklist (Side 2)

Set these for non-demo mother (fail-closed):

```bash
CHORUSCONTROL_DEMO_MODE=0
CHORUSCONTROL_ADMIN_TOKEN=<strong random ≥16 chars>
CHORUSCONTROL_LICENSE_KEY=<Side 1 issued JWT>
# Optional on choruscontrol>=0.1.1 — packaged side1_public.hex is the 2026-07-27 ceremony public.
# Set only for key rotation / emergency override:
# CHORUSCONTROL_LICENSE_PUBLIC_KEY_HEX=<Side 1 ceremony --public>
# CHORUSCONTROL_LICENSE_PUBLIC_PEM="-----BEGIN PUBLIC KEY-----..."

CHORUSCONTROL_AUDIT_PRIVATE_KEY_PEM=<or let mother generate once on volume>
CHORUSCONTROL_SQLITE_PATH=/data/mother.db
# optional durability:
# DATABASE_URL=postgresql://...

# optional online revoke check (air-gap: set 0)
CHORUSCONTROL_LICENSE_ONLINE_CHECK=1
CHORUSCONTROL_SIDE1_API_BASE_URL=https://www.insightits.com
```

Demo / healthcare compose: use `Dockerfile.demo` + explicit `CHORUSCONTROL_DEMO_MODE=1` and a compose-only admin token (e.g. `healthcare-demo-token`).
