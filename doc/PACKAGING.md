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

## Publish checklist (v0.1.2)

### Preflight

- [x] Version `0.1.2` in `pyproject.toml`
- [x] Packaged `side1_public.hex` = prod ceremony public (BUG-007)
- [x] Taxonomy LiveRag mapping + non-demo pack gate (HO-004/005)
- [x] Pin tiers + install_hint + reference `docker/Dockerfile.mother` (HO-006)
- [x] Apache-2.0 `LICENSE` + project classifiers
- [x] Wheel includes UI static/templates + `side1_public.pem` / `.hex`
- [x] `twine check` passes
- [x] CI on `main` (`.github/workflows/ci.yml`) + tag publish (`.github/workflows/publish.yml`)

### One-time: Trusted Publisher on PyPI

1. Sign in at [pypi.org](https://pypi.org) as the Insight ITS publisher account.
2. **Publishing → Add a new pending publisher** (or create project `choruscontrol` first).
3. Set:
   - **PyPI project name:** `choruscontrol`
   - **Owner:** `insightitsGit`
   - **Repository:** `ChorusControl`
   - **Workflow name:** `publish.yml`
   - **Environment name:** leave empty (unless you add a matching GitHub Environment)
4. Save. First tag upload creates the project via OIDC — no long-lived API token required.

Optional TestPyPI: same form on [test.pypi.org](https://test.pypi.org), then tag a dry-run or use manual `twine upload --repository testpypi dist/*`.

### Release command (after Trusted Publisher is saved)

```bash
# on main, clean tree
git pull
git tag v0.1.1
git push origin v0.1.1
```

GitHub Actions: **Publish** workflow → test → build → `pypa/gh-action-pypi-publish`.

Or local:

```bash
python -m build && twine check dist/* && twine upload dist/*
```

Verify:

```bash
pip install "choruscontrol[server,agent]==0.1.1"
choruscontrol doctor --mode mother
# Ceremony JWT verifies without CHORUSCONTROL_LICENSE_PUBLIC_KEY_HEX
```

### Manual fallback (API token)

```bash
twine upload dist/*          # or --repository testpypi
```

Prefer Trusted Publisher over long-lived tokens.

## Container worker (lightweight)

```dockerfile
FROM python:3.12-slim
RUN pip install --no-cache-dir "choruscontrol[agent]==0.1.1"
ENV CHORUSCONTROL_MOTHER_URL=http://mother:8443
CMD ["choruscontrol-agent"]
```

Until the first PyPI release is live, install from GitHub:

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
