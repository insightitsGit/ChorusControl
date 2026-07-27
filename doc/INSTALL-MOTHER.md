# Install mother (production)

## Profiles

| Profile | Install | Mode |
|---------|---------|------|
| **Demo / local** | `pip install "choruscontrol[server]"` | `CHORUSCONTROL_DEMO_MODE=1` — NullAdapters OK |
| **Production mother** | `pip install "choruscontrol[server,postgres,prism]"` | `DEMO_MODE=0` — live Guard, Taxonomy, Cortex, Shine, Graph |
| **Fleet agent** | `pip install "choruscontrol[agent]"` | Join mother; background-only |
| **+ Fabric** | add `[fabric]` | Optional wire |

Production one-liner (current release):

```bash
pip install "choruscontrol[server,postgres,prism]==0.1.2"
```

Taxonomy in non-demo **requires** PrismRAG + PrismGuard (both in `[prism]`). Without them, Taxonomy APIs return **503** with an install hint — not silent DEMO.

## Run

```bash
export CHORUSCONTROL_DEMO_MODE=0
export CHORUSCONTROL_ADMIN_TOKEN="<strong-secret-16+>"
export CHORUSCONTROL_LICENSE_KEY="<jwt-from-portal>"
# optional: export DATABASE_URL=postgresql://...
choruscontrol serve --host 0.0.0.0 --port 8443
choruscontrol doctor --mode mother
```

Doctor prints `version`, `pins` (core vs optional), `taxonomy_packs`, and `install_hint` when core packs are missing.

## Reference container

```bash
docker build -f docker/Dockerfile.mother -t choruscontrol-mother:0.1.2 .
```

Root `Dockerfile` also installs `[server,agent,postgres,prism]` for production images. Use `Dockerfile.demo` / healthcare compose for DEMO.

## Pin tiers

- **core** (from `[prism]`): chorusgraph, prismguard, prismrag-patch, prismshine, prismcortex  
- **optional**: prismlib-plus, chorus-fabric, prismlang, prismresonance, chorusmesh  

Optional missing packs are informational — not the same severity as missing Guard.
