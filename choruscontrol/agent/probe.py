from __future__ import annotations

import importlib.metadata
import json
from typing import Any


CANDIDATES = [
    "chorusgraph",
    "prismguard",
    "prismshine",
    "prismcortex",
    "prismrag-patch",
    "prismlib-plus",
    "prismlib",
    "prismlang",
    "prismresonance",
    "chorus-fabric",
    "chorusmesh",
]


def probe_products() -> dict[str, str]:
    found: dict[str, str] = {}
    for name in CANDIDATES:
        try:
            found[name.replace("-", "_") if name == "prismrag-patch" else name] = (
                importlib.metadata.version(name)
            )
        except importlib.metadata.PackageNotFoundError:
            # try alternate import name
            alt = name.replace("-", "_")
            try:
                found[alt] = importlib.metadata.version(alt)
            except importlib.metadata.PackageNotFoundError:
                continue
    if not found:
        found = {"choruscontrol-agent": "0.1.0", "demo": "1"}
    return found


def caps_digest(products: dict[str, str]) -> str:
    return str(abs(hash(json.dumps(products, sort_keys=True))))
