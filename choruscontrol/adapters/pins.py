"""Sibling package version floors (Shipping Gaps S04)."""

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

# Map logical adapter → distribution name(s) to probe
ADAPTER_PACKAGES: dict[str, list[str]] = {
    "graph": ["chorusgraph"],
    "guard": ["prismguard"],
    "cortex": ["prismcortex"],
    "rag": ["prismrag-patch", "prismrag"],
    "shine": ["prismshine"],
    "cache": ["prismlib-plus", "prismcache"],
    "fabric": ["chorus-fabric"],
    "driver": ["prismlib-plus"],
}


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


def check_pins() -> dict[str, Any]:
    """Doctor / S04 report: each pin floor vs installed."""
    rows: list[dict[str, Any]] = []
    for name, floor in PIN_FLOORS.items():
        ver = installed_version(name)
        ok = bool(ver and version_at_least(ver, floor))
        rows.append(
            {
                "package": name,
                "floor": floor,
                "installed": ver,
                "ok": ok,
                "status": "ok" if ok else ("missing" if ver is None else "below_floor"),
            }
        )
    return {
        "pins": rows,
        "all_ok": all(r["ok"] for r in rows),
        "any_live_candidate": any(r["ok"] for r in rows),
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
