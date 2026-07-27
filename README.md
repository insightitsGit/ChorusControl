# ChorusControl

**ChorusControl — AI Operations Platform** for the Prism / Chorus stack  
(Enterprise AI Operating System architecture — mother + fleet agents)

## Install

**From GitHub (current — until public PyPI tag):**

```bash
pip install "choruscontrol[server,agent] @ git+https://github.com/insightitsGit/ChorusControl.git@main"
```

Editable / from a clone:

```bash
git clone https://github.com/insightitsGit/ChorusControl.git
cd ChorusControl
pip install -e ".[server,agent,dev]"
```

**After a `v*` tag publish to PyPI:**

```bash
pip install "choruscontrol[server,agent]==0.1.0"
```

Prism live packs (private/extra index as needed):

```bash
pip install "choruscontrol[server,agent,prism]"
```

## Run mother (local demo)

```bash
set CHORUSCONTROL_DEMO_MODE=1
set CHORUSCONTROL_ADMIN_TOKEN=healthcare-demo-token
choruscontrol serve --host 127.0.0.1 --port 8443
```

Open http://127.0.0.1:8443/overview  
API auth: `Authorization: Bearer healthcare-demo-token`

Production Azure env: see [doc/Azure-Mother-Env.md](doc/Azure-Mother-Env.md) (`DEMO_MODE=0`, strong admin token, Side 1 JWT + public key hex).

```bash
choruscontrol doctor --mode mother
```

## Demo compose (mother + 2 agents)

```bash
docker compose up --build
```

Boots mother, creates a join token, enrolls `demo-green` and `demo-blue`.

## Healthcare full-stack demo (Aurora Health)

```bash
docker compose -f docker-compose.healthcare.yml up --build
```

Clinical + pharmacy + edge agents, seeded tenants/policy/cascade/traces.  
UI: http://127.0.0.1:8443/overview · Bearer `healthcare-demo-token`  
See [doc/Healthcare-Demo.md](doc/Healthcare-Demo.md).

## Fleet agent (other hosts)

```bash
set CHORUSCONTROL_MOTHER_URL=http://mother:8443
set CHORUSCONTROL_JOIN_TOKEN=<from Admin / POST /api/v1/fleet/join-tokens>
set CHORUSCONTROL_NODE_ID=worker-1
choruscontrol-agent
# or: choruscontrol doctor --mode agent
```

Or `from choruscontrol.agent import attach_agent` — **background only; never await on invoke/digest/recall**.

## Design decisions (from review)

| Item | Choice |
|------|--------|
| Control transport | **HTTP primary**; Fabric optional |
| Mother persistence | **SQLite default** (+ WAL); Postgres audit via `DATABASE_URL` |
| License | Offline verify + **14-day grace** read-only |
| Auth | Local admin token **+ optional OIDC/SSO** |
| Observability | **Coexists with OTel** — OTel watches; ChorusControl acts |
| Live Prism packs | Used when installed at pin floors; otherwise **NullAdapters** labeled DEMO |

## Packaging (pip / containers)

See [doc/PACKAGING.md](doc/PACKAGING.md). Lightweight workers:

```bash
pip install "choruscontrol[agent]"
# or from source: pip install ".[agent]"
choruscontrol-agent
```

Build wheels: `pwsh scripts/build_release.ps1` (tag `v*` publishes via GitHub Actions).

## Side 1 (website)

License issuance / Stripe / portal UX is **not** in this repo. See [doc/Side1-insightits-com-Handoff.md](doc/Side1-insightits-com-Handoff.md).

## Docs

See `doc/ChorusControl-COMPLETE-DESIGN.md` and `doc/ChorusControl-Implementation-Plan.md`.

## Tests

```bash
pytest -q
```

Includes hot-path latency (S03) and restart soak.

## License

Apache-2.0 — Insight IT Solutions LLC
