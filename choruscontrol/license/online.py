"""Optional Side 1 online license check (revocation / registry).

Primary path remains offline Ed25519. Connected installs SHOULD call
POST {base}/api/choruscontrol/validate about every 14 days. Air-gap:
set CHORUSCONTROL_LICENSE_ONLINE_CHECK=0.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any

log = logging.getLogger("choruscontrol.license.online")

PRODUCT_VERSION = "0.1.0"


def _state_path(settings) -> Path:
    base = Path(settings.sqlite_path).parent
    base.mkdir(parents=True, exist_ok=True)
    return base / "license_online_check.json"


def load_cached_check(settings) -> dict[str, Any] | None:
    path = _state_path(settings)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:  # noqa: BLE001
        return None


def save_cached_check(settings, payload: dict[str, Any]) -> None:
    path = _state_path(settings)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def due_for_check(settings, cached: dict[str, Any] | None) -> bool:
    if not getattr(settings, "license_online_check", True):
        return False
    if settings.demo_mode and not getattr(settings, "license_online_check_in_demo", False):
        return False
    interval = float(getattr(settings, "license_online_interval_days", 14) or 14) * 86400
    if not cached:
        return True
    last = float(cached.get("checked_at_unix") or 0)
    return (time.time() - last) >= interval


async def fetch_public_key(base_url: str, *, timeout: float = 10.0) -> dict[str, Any]:
    import httpx

    url = f"{base_url.rstrip('/')}/api/choruscontrol/public-key"
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.get(url)
        r.raise_for_status()
        return r.json()


async def validate_online(
    *,
    base_url: str,
    license_key: str,
    instance_id: str | None = None,
    product_version: str | None = None,
    timeout: float = 15.0,
) -> dict[str, Any]:
    import httpx

    url = f"{base_url.rstrip('/')}/api/choruscontrol/validate"
    body = {
        "licenseKey": license_key,
        "instanceId": instance_id,
        "productVersion": product_version or PRODUCT_VERSION,
    }
    async with httpx.AsyncClient(timeout=timeout) as client:
        r = await client.post(url, json=body)
        r.raise_for_status()
        data = r.json()
    # Never persist the key
    data.pop("licenseKey", None)
    data["checked_at_unix"] = time.time()
    data["base_url"] = base_url.rstrip("/")
    return data


async def run_online_check(state, *, force: bool = False) -> dict[str, Any]:
    """Run validate against Side 1 if enabled/due. Network failures keep last offline verdict."""
    settings = state.settings
    cached = load_cached_check(settings) or getattr(state, "online_license", None)

    if not getattr(settings, "license_online_check", True):
        return {
            "skipped": True,
            "reason": "CHORUSCONTROL_LICENSE_ONLINE_CHECK disabled (air-gap)",
            "cached": cached,
        }
    if settings.demo_mode and not getattr(settings, "license_online_check_in_demo", False):
        return {"skipped": True, "reason": "demo_mode", "cached": cached}
    if not force and not due_for_check(settings, cached):
        return {"skipped": True, "reason": "not_due", "cached": cached}

    from choruscontrol.license.store import resolve_license_key

    key = resolve_license_key(settings) or settings.license_key
    if not key:
        return {"skipped": True, "reason": "no_license_key"}

    base = (settings.insightits_portal_url or "https://www.insightits.com").rstrip("/")
    # Allow dedicated API base (local Side 1 often http://127.0.0.1:5000)
    api_base = getattr(settings, "side1_api_base_url", None) or base

    try:
        result = await validate_online(
            base_url=api_base,
            license_key=key,
            instance_id=settings.node_id or "mother",
            product_version=PRODUCT_VERSION,
        )
        save_cached_check(settings, result)
        state.online_license = result
        log.info(
            "side1 license check status=%s valid=%s registry=%s",
            result.get("status"),
            result.get("valid"),
            result.get("registryStatus"),
        )
        return {"ok": True, "result": result}
    except Exception as exc:  # noqa: BLE001
        log.warning("side1 license online check failed (keeping offline verdict): %s", exc)
        err = {
            "ok": False,
            "error": str(exc),
            "checked_at_unix": time.time(),
            "offlineOk": True,
            "phoneHomeRequired": False,
            "cached": cached,
        }
        # Keep prior successful cache; only stamp last attempt
        state.online_license = {**(cached or {}), "last_error": str(exc), "last_attempt_unix": time.time()}
        return err


def apply_online_to_status(offline_status, online: dict[str, Any] | None):
    """If Side 1 says revoked, fail-closed even when JWT still verifies."""
    from choruscontrol.license.verifier import LicenseStatus

    if not online or online.get("skipped"):
        return offline_status
    payload = online.get("result") if isinstance(online.get("result"), dict) else online
    status = str(payload.get("status") or "").lower()
    if status == "revoked":
        return LicenseStatus(
            "invalid",
            offline_status.claims,
            f"revoked by Side 1 registry ({payload.get('registryStatus') or payload.get('reason') or 'revoked'})",
            offline_status.seconds_to_exp,
            offline_status.grace_remaining_seconds,
        )
    return offline_status
