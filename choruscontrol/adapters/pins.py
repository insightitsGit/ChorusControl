"""Sibling package version floors, pin tiers, and Taxonomy pack readiness."""

from __future__ import annotations

from importlib import metadata
from typing import Any

# Minimum versions for live adapter activation
PIN_FLOORS: dict[str, str] = {
    "chorusgraph": "1.3.0",
    "prismguard": "0.1.10",
    "prismcortex": "0.3.0",
    "prismrag-patch": "0.2.1",
    "prismshine": "0.2.2",
    "prismlib-plus": "0.8.0",
    "chorus-fabric": "0.2.0",
    "prismlang": "0.1.2",
    "prismresonance": "0.3.0",
    "chorusmesh": "0.1.0",
}

# Core = pulled by choruscontrol[prism]; optional = fabric/mesh/lang extras
PIN_TIERS: dict[str, str] = {
    "chorusgraph": "core",
    "prismguard": "core",
    "prismcortex": "core",
    "prismrag-patch": "core",
    "prismshine": "core",
    "prismlib-plus": "optional",
    "chorus-fabric": "optional",
    "prismlang": "optional",
    "prismresonance": "optional",
    "chorusmesh": "optional",
}

# Map logical adapter → distribution name(s) to probe
ADAPTER_PACKAGES: dict[str, list[str]] = {
    "graph": ["chorusgraph"],
    "guard": ["prismguard"],
    "cortex": ["prismcortex"],
    "rag": ["prismrag-patch", "prismrag"],
    "shine": ["prismshine"],
    "cache": ["prismlib-plus", "prism"],
    "fabric": ["chorus-fabric"],
    "driver": ["prismlib-plus", "prism"],
}

PRODUCTION_INSTALL = 'pip install "choruscontrol[server,postgres,prism]"'
TAXONOMY_INSTALL = (
    'pip install "choruscontrol[server,prism]"  '
    "# requires prismrag-patch==0.2.1 + prismguard==0.1.10"
)


def _parse_version(v: str) -> tuple[int, ...]:
    parts: list[int] = []
    for chunk in v.replace("-", ".").split("."):
        digits = "".join(c for c in chunk if c.isdigit())
        if digits:
            parts.append(int(digits))
    return tuple(parts) if parts else (0,)


def version_at_least(installed: str, floor: str) -> bool:
    return _parse_version(installed) >= _parse_version(floor)


def installed_version(dist_name: str) -> str | None:
    try:
        return metadata.version(dist_name)
    except metadata.PackageNotFoundError:
        return None


def package_version() -> str:
    """Installed choruscontrol distribution version (doctor / FastAPI)."""
    ver = installed_version("choruscontrol")
    if ver:
        return ver
    try:
        from choruscontrol import __version__

        return __version__
    except Exception:  # noqa: BLE001
        return "0.0.0"


def check_pins() -> dict[str, Any]:
    """Doctor / S04 report: each pin floor vs installed, with tier + install hint."""
    rows: list[dict[str, Any]] = []
    for name, floor in PIN_FLOORS.items():
        ver = installed_version(name)
        ok = bool(ver and version_at_least(ver, floor))
        tier = PIN_TIERS.get(name, "optional")
        status = "ok" if ok else ("missing" if ver is None else "below_floor")
        rows.append(
            {
                "package": name,
                "floor": floor,
                "installed": ver,
                "ok": ok,
                "status": status,
                "tier": tier,
                "severity": "error" if (not ok and tier == "core") else ("info" if not ok else "ok"),
            }
        )
    core = [r for r in rows if r["tier"] == "core"]
    missing_core = [r["package"] for r in core if not r["ok"]]
    return {
        "pins": rows,
        "all_ok": all(r["ok"] for r in rows),
        "core_ok": all(r["ok"] for r in core),
        "any_live_candidate": any(r["ok"] for r in rows),
        "missing_core": missing_core,
        "install_hint": PRODUCTION_INSTALL if missing_core else None,
    }


def package_ready(logical: str) -> tuple[bool, str | None, str | None]:
    """Return (ready, dist_name, version) for an adapter family."""
    for dist in ADAPTER_PACKAGES.get(logical, []):
        ver = installed_version(dist)
        floor = PIN_FLOORS.get(dist, "0.0.0")
        if ver and version_at_least(ver, floor):
            return True, dist, ver
        # Also accept installed without floor entry (alt name)
        if ver and dist not in PIN_FLOORS:
            return True, dist, ver
    return False, None, None


def taxonomy_packs_ready() -> dict[str, Any]:
    """PrismRAG + PrismGuard required for Taxonomy in non-demo (ARCH-002 / HO-005)."""
    rag_ok, rag_dist, rag_ver = package_ready("rag")
    guard_ok, guard_dist, guard_ver = package_ready("guard")
    ready = bool(rag_ok and guard_ok)
    messages: list[str] = []
    if not rag_ok:
        messages.append("prismrag-patch (or prismrag) missing or below pin floor")
    if not guard_ok:
        messages.append("prismguard missing or below pin floor")
    return {
        "rag": {"ok": rag_ok, "package": rag_dist, "version": rag_ver},
        "guard": {"ok": guard_ok, "package": guard_dist, "version": guard_ver},
        "ready": ready,
        "messages": messages,
        "install_hint": TAXONOMY_INSTALL if not ready else None,
    }
