# Packaging & container installs

ChorusControl ships as **one PyPI package** with extras so mother and workers stay thin.

## Extras

| Extra | Purpose |
|-------|---------|
| *(none)* | Core libs only |
| `[agent]` | Lightweight fleet agent (`choruscontrol-agent`) |
| `[server]` | Mother UI/API |
| `[postgres]` | `asyncpg` for audit dual-write |
| `[prism]` | Live Prism pack pins (ChorusGraph, Guard, Shine, RAG, Cortex) |
| `[fabric]` | Optional Fabric transport |
| `[all]` | server + agent + postgres + prism |
| `[dev]` | tests / lint (+ server, agent, prism) |
| `[packaging]` | `build` + `twine` |

## Local / CI build

```bash
pip install build twine
python -m build
twine check dist/*
python scripts/inspect_wheel.py
# artifacts: dist/choruscontrol-*.whl dist/choruscontrol-*.tar.gz
```

PowerShell: `pwsh scripts/build_release.ps1`

## Publish checklist (v0.1.3)

### What’s new vs 0.1.2 (mother)

- Ops Logs tab + fleet `logs-batch` + live WS  
- Admin **Client AI chats** + PrismCortex compact (`/chats/*`, `fleet/chat-batch`)  
- Ops Assistant literacy + **per-tab actionable catalog** (`assistant_actions.py`)  
- Design docs v1.8.1  

No new extras — still one package; features ship in `[server]` (PrismCortex compact needs `[prism]` / installed prismcortex for live digest).

### Preflight

- [x] Version `0.1.3` in `pyproject.toml` + `choruscontrol.__version__`
- [x] Packaged `side1_public.hex` = prod ceremony public (BUG-007)
- [x] Taxonomy LiveRag mapping + non-demo pack gate (HO-004/005)
- [x] Pin tiers + install_hint + reference `docker/Dockerfile.mother` (HO-006)
- [x] Apache-2.0 `LICENSE` + project classifiers
- [x] Wheel includes UI static/templates + `side1_public.pem` / `.hex`
- [ ] `python -m build` → `choruscontrol-0.1.3-*.whl`
- [ ] `twine check` passes
- [ ] CI on `main` + tag publish (`.github/workflows/publish.yml`)

### One-time: Trusted Publisher on PyPI (optional)

Local **twine upload** is the primary release path today. GitHub **Publish** on tags always runs tests + build; PyPI upload via Actions only succeeds when one of these is configured:

1. Sign in at [pypi.org](https://pypi.org) → project `choruscontrol` → **Publishing** → Trusted Publisher:
   - **Owner:** `insightitsGit`
   - **Repository:** `ChorusControl`
   - **Workflow name:** `publish.yml`
   - **Environment name:** leave empty
2. **Or** add repo secret `PYPI_API_TOKEN` (`pypi-…`) for token upload from Actions.

Without either, the OIDC publish step is **non-blocking** (`continue-on-error`) so tag CI stays green after you already uploaded with twine.

### Release command

```bash
# on main, clean tree — build + upload locally (primary)
# remove old dist first so twine does not pick 0.1.2 artifacts
Remove-Item -Recurse -Force dist -ErrorAction SilentlyContinue   # PowerShell
# rm -rf dist                                                    # bash
python -m build && twine upload dist/*

# optional: tag for GitHub verify workflow
git tag v0.1.3
git push origin v0.1.3
```

Verify:

```bash
pip install "choruscontrol[server,postgres,prism]==0.1.3"
choruscontrol doctor --mode mother
# expect version 0.1.3; Admin → Client AI chats; Ops Assistant “What can you do on taxonomy?”
```

## Container worker (lightweight)

```dockerfile
FROM python:3.12-slim
RUN pip install --no-cache-dir "choruscontrol[agent]==0.1.3"
ENV CHORUSCONTROL_MOTHER_URL=http://mother:8443
CMD ["choruscontrol-agent"]
```

Until the release is on PyPI, install from GitHub:

```bash
pip install "choruscontrol[server,agent] @ git+https://github.com/insightitsGit/ChorusControl.git@main"
# or from a clone:
pip install ".[agent]"
```

## Mother with Postgres audit

```bash
pip install "choruscontrol[server,postgres]"
export DATABASE_URL=postgresql://cc:cc@postgres:5432/choruscontrol
choruscontrol serve
```

## OIDC

```bash
export CHORUSCONTROL_OIDC_ENABLED=1
export CHORUSCONTROL_OIDC_ISSUER=https://idp.example.com/realms/chorus
export CHORUSCONTROL_OIDC_AUDIENCE=choruscontrol
export CHORUSCONTROL_OIDC_JWKS_URL=https://idp.example.com/realms/chorus/protocol/openid-connect/certs
```

Map IdP roles via claim `chorus_roles` (or `CHORUSCONTROL_OIDC_ROLE_CLAIM`): `admin|security|operator|viewer`.

## Still Side 1 (other agent)

License **issuance**, Stripe, customer portal — not this package.
