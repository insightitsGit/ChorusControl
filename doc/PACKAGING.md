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

## Publish checklist (v0.1.4)

### What’s new vs 0.1.3 (mother)

- HO-010: safe Assistant `data-exec` encoding (apostrophes)
- Grace allows non-mutating Assistant executes (`chats.list`, `logs.search`, …)
- Taxonomy chunk health key (`category_slug`) — no `undefined`
- Compliance: optional fabric null not medium-flagged as core NullAdapter
- AG-001 documented: Memory UI → Cortex

### Preflight

- [x] Version `0.1.4` in `pyproject.toml` + `choruscontrol.__version__`
- [x] Wheel includes UI static/templates + license trust anchors
- [x] `python -m build` → `choruscontrol-0.1.4-*.whl`
- [x] `twine check` passes
- [ ] Upload + tag `v0.1.4`

### Release command

```bash
Remove-Item -Recurse -Force dist -ErrorAction SilentlyContinue
python -m build && twine check dist/*
twine upload dist/choruscontrol-0.1.4-py3-none-any.whl dist/choruscontrol-0.1.4.tar.gz

git tag v0.1.4
git push origin v0.1.4
```

Verify:

```bash
pip install "choruscontrol[server,postgres,prism]==0.1.4"
choruscontrol doctor --mode mother
```

## Publish checklist (v0.1.3) — shipped

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
- [x] Published to PyPI as 0.1.3

### Container worker (lightweight)

```dockerfile
FROM python:3.12-slim
RUN pip install --no-cache-dir "choruscontrol[agent]==0.1.4"
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
