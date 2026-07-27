from __future__ import annotations

import argparse
import json
import sys


def _doctor_exit_code(payload: dict) -> int:
    """Exit 1 on hard failures (license invalid non-demo, pin floor, unwritable store)."""
    if payload.get("mode") == "agent":
        pins = payload.get("pins") or {}
        pin_list = pins.get("pins") if isinstance(pins, dict) else pins
        if isinstance(pin_list, list) and any(not p.get("ok", True) for p in pin_list if isinstance(p, dict)):
            # agent pins missing packages are informational unless explicitly hard-fail flagged
            if any(p.get("hard_fail") for p in pin_list if isinstance(p, dict)):
                return 1
        return 0
    if payload.get("demo_mode"):
        return 0
    lic = (payload.get("license") or {}).get("state")
    if lic in ("invalid", "missing"):
        return 1
    if payload.get("store_writable") is False:
        return 1
    pins = payload.get("pins") or {}
    pin_list = pins.get("pins") if isinstance(pins, dict) else None
    if isinstance(pin_list, list):
        for p in pin_list:
            if (
                isinstance(p, dict)
                and p.get("tier", "core") == "core"
                and p.get("installed")
                and not p.get("ok", True)
            ):
                return 1
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(prog="choruscontrol")
    sub = parser.add_subparsers(dest="cmd", required=True)

    serve = sub.add_parser("serve", help="Run mother AI Operations Platform")
    serve.add_argument("--host", default=None)
    serve.add_argument("--port", type=int, default=None)

    doctor = sub.add_parser("doctor", help="Doctor snapshot (mother or agent mode)")
    doctor.add_argument(
        "--mode",
        choices=["auto", "mother", "agent"],
        default="auto",
        help="auto: agent if MOTHER_URL set else mother",
    )

    av = sub.add_parser("audit-verify", help="Verify audit JSONL with public key (R06)")
    av.add_argument("path")
    av.add_argument("--pubkey", required=True)

    args = parser.parse_args()
    if args.cmd == "serve":
        import uvicorn

        from choruscontrol.config import get_settings
        from choruscontrol.config_security import admin_token_is_weak

        s = get_settings()
        if not s.demo_mode and admin_token_is_weak(s.admin_token):
            print(
                "Refusing to serve: set a strong CHORUSCONTROL_ADMIN_TOKEN "
                "(≥16 chars, not the legacy default) or enable CHORUSCONTROL_DEMO_MODE=1 "
                "for local demos only.",
                file=sys.stderr,
            )
            raise SystemExit(2)
        if not s.demo_mode and not (s.license_key or "").strip():
            # Soft warning — middleware fail-closes APIs; allow boot so Admin can install a key
            print(
                "WARNING: CHORUSCONTROL_LICENSE_KEY unset — APIs will 503 until a Side 1 JWT is installed.",
                file=sys.stderr,
            )
        uvicorn.run(
            "choruscontrol.server:app",
            host=args.host or s.host,
            port=args.port or s.port,
            reload=False,
        )
    elif args.cmd == "doctor":
        from choruscontrol.config import get_settings

        settings = get_settings()
        mode = args.mode
        if mode == "auto":
            mode = "agent" if settings.mother_url else "mother"
        if mode == "agent":
            from choruscontrol.services.doctor import doctor_agent

            reachable = None
            if settings.mother_url:
                try:
                    import httpx

                    r = httpx.get(f"{settings.mother_url.rstrip('/')}/healthz", timeout=2.0)
                    reachable = r.status_code == 200
                except Exception:  # noqa: BLE001
                    reachable = False
            payload = doctor_agent(mother_url=settings.mother_url, mother_reachable=reachable)
            print(json.dumps(payload, indent=2))
            raise SystemExit(_doctor_exit_code(payload))
        else:
            import asyncio

            from choruscontrol.app_state import build_state
            from choruscontrol.services.doctor import doctor_mother

            async def _run():
                state = await build_state(settings)
                try:
                    # probe store writability
                    try:
                        await state.store.execute(
                            "CREATE TABLE IF NOT EXISTS _doctor_ping(x INTEGER)"
                        )
                        store_writable = True
                    except Exception:  # noqa: BLE001
                        store_writable = False
                    doc = await doctor_mother(state)
                    doc["store_writable"] = store_writable
                    print(json.dumps(doc, indent=2, default=str))
                    hint = doc.get("install_hint")
                    if hint:
                        print(f"\n# install_hint: {hint}", file=sys.stderr)
                    missing = (doc.get("pins") or {}).get("missing_core") or []
                    if missing and not doc.get("demo_mode"):
                        print(f"# missing_core: {', '.join(missing)}", file=sys.stderr)
                    return _doctor_exit_code(doc)
                finally:
                    if state.metrics_sampler:
                        await state.metrics_sampler.stop()
                    await state.audit.stop()

            code = asyncio.run(_run())
            raise SystemExit(code)
    elif args.cmd == "audit-verify":
        from pathlib import Path

        from choruscontrol.audit.logger import verify_audit_line

        pem = Path(args.pubkey).read_text(encoding="utf-8")
        ok = bad = 0
        for line in Path(args.path).read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            if verify_audit_line(line, pem):
                ok += 1
            else:
                bad += 1
        print({"verified": ok, "failed": bad})
        raise SystemExit(1 if bad else 0)


if __name__ == "__main__":
    main()
