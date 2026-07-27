# Packaging & container installs

ChorusControl ships as **one PyPI package** with extras so mother and workers stay thin.

## Extras

| Extra | Purpose |
|-------|---------|
| *(none)* | Core libs only |
| `[agent]` | Lightweight fleet agent (`choruscontrol-agent`) |
| `[server]` | Mother UI/API |
| `[postgres]` | `asyncpg` for audit dual-write |
| `[fabric]` | Optional Fabric transport |
| `[all]` | server + agent + postgres |
| `[dev]` | tests / lint |

## Local / CI build

```bash
pip install build twine
python -m build
# artifacts: dist/choruscontrol-*.whl dist/choruscontrol-*.tar.gz
```

PowerShell: `pwsh scripts/build_release.ps1`

## Publish (manual)

```bash
# TestPyPI
twine upload --repository testpypi dist/*

# PyPI (requires API token)
twine upload dist/*
```

GitHub Actions: `.github/workflows/publish.yml` (publish on tag `v*`).

## Container worker (lightweight)

```dockerfile
FROM python:3.12-slim
RUN pip install --no-cache-dir "choruscontrol[agent]==0.1.0"
ENV CHORUSCONTROL_MOTHER_URL=http://mother:8443
CMD ["choruscontrol-agent"]
```

Until the package is on public PyPI, install from GitHub:

```bash
pip install "choruscontrol[server,agent] @ git+https://github.com/insightitsGit/ChorusControl.git@main"
# or from a clone:
pip install ".[agent]"
```

or install a wheel from your private index:

```bash
pip install "choruscontrol[agent]==0.1.0" --index-url https://pypi.company.internal/simple
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
