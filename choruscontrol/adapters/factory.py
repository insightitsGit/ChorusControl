"""Build adapter bundle: live when sibling pkgs ready, else NullAdapters (demo=true)."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from choruscontrol.adapters.live import try_construct
from choruscontrol.adapters.nulls import (
    NullCache,
    NullCortex,
    NullFabric,
    NullGraph,
    NullGuard,
    NullRag,
    NullShine,
)
from choruscontrol.adapters.pins import check_pins, package_ready


@dataclass
class AdapterBundle:
    cache: Any
    fabric: Any
    guard: Any
    shine: Any
    cortex: Any
    graph: Any
    rag: Any
    sources: dict[str, str]
    pins: dict[str, Any]


def _pick(logical: str, null_factory, force_demo: bool) -> tuple[Any, str]:
    if force_demo:
        return null_factory(), "null"
    live = try_construct(logical)
    if live is not None:
        ready, dist, ver = package_ready(logical)
        return live, f"live:{dist}@{ver}" if ready else "live"
    return null_factory(), "null"


def build_adapters(*, force_demo: bool = False) -> AdapterBundle:
    sources: dict[str, str] = {}
    cache, sources["cache"] = _pick("cache", NullCache, force_demo)
    fabric, sources["fabric"] = _pick("fabric", NullFabric, force_demo)
    guard, sources["guard"] = _pick("guard", NullGuard, force_demo)
    shine, sources["shine"] = _pick("shine", NullShine, force_demo)
    cortex, sources["cortex"] = _pick("cortex", NullCortex, force_demo)
    graph, sources["graph"] = _pick("graph", NullGraph, force_demo)
    rag, sources["rag"] = _pick("rag", NullRag, force_demo)
    return AdapterBundle(
        cache=cache,
        fabric=fabric,
        guard=guard,
        shine=shine,
        cortex=cortex,
        graph=graph,
        rag=rag,
        sources=sources,
        pins=check_pins(),
    )
