"""Doctor snapshots — mother and agent modes."""

from __future__ import annotations

from typing import Any

from choruscontrol.adapters.pins import check_pins, package_version, taxonomy_packs_ready
from choruscontrol.agent.probe import probe_products


def doctor_agent(*, mother_url: str | None, mother_reachable: bool | None = None) -> dict[str, Any]:
    products = probe_products()
    pins = check_pins()
    return {
        "mode": "agent",
        "version": package_version(),
        "product": "ChorusControl — AI Operations Platform",
        "mother_url": mother_url,
        "mother_reachable": mother_reachable,
        "products": products,
        "pins": pins,
        "install_hint": pins.get("install_hint"),
        "hot_path": "attach_agent is background-only; never await mother on invoke/digest/recall",
    }


async def doctor_mother(state) -> dict[str, Any]:
    await state.refresh_license()
    nodes = await state.fleet.list_nodes()
    audit_ok = state.settings.audit_log_path.parent.exists() or True
    adapter_health = {}
    for name in ("cache", "guard", "shine", "cortex", "graph", "rag", "fabric"):
        src = state.adapter_sources.get(name, "unknown")
        adapter_health[name] = {
            "source": src,
            "live": src.startswith("live"),
            "demo": src == "null",
        }
    dogfood = await state.graph.dogfood()
    pg = None
    if state.postgres is not None:
        pg = {"ok": state.postgres.ok, "error": state.postgres.last_error}
    elif state.settings.database_url:
        pg = {"ok": False, "error": "not connected"}
    # Always re-probe pins (HO-006) — do not trust startup-only snapshot
    pins = check_pins()
    state.adapter_pins = pins
    tax = taxonomy_packs_ready()
    return {
        "mode": "mother",
        "version": package_version(),
        "product": "ChorusControl — AI Operations Platform",
        "demo_mode": state.settings.demo_mode,
        "transport_primary": state.settings.transport_primary,
        "license": {
            "state": state.license_status.state,
            "message": state.license_status.message,
            "grace_days": state.settings.license_grace_days,
        },
        "sqlite": str(state.settings.sqlite_path),
        "audit_log": str(state.settings.audit_log_path),
        "audit_ok": audit_ok,
        "postgres": pg,
        "oidc_enabled": state.settings.oidc_enabled,
        "fleet_nodes": len(nodes),
        "adapters": adapter_health,
        "pins": pins,
        "taxonomy_packs": tax,
        "install_hint": pins.get("install_hint") or tax.get("install_hint"),
        "dogfood": dogfood,
        "portal_url": state.settings.insightits_portal_url,
        "support_url": state.settings.insightits_support_url,
    }
