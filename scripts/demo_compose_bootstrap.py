"""Create a multi-use join token for compose agents and write to JOIN_TOKEN_FILE."""

from __future__ import annotations

import os
import sys
import time

import httpx

MOTHER = os.environ.get("CHORUSCONTROL_MOTHER_URL", "http://127.0.0.1:8443").rstrip("/")
TOKEN = os.environ.get("CHORUSCONTROL_ADMIN_TOKEN", "dev-admin-token")
OUT = os.environ.get("JOIN_TOKEN_FILE", "/shared/join_token")


def main() -> int:
    headers = {"Authorization": f"Bearer {TOKEN}"}
    for attempt in range(30):
        try:
            with httpx.Client(base_url=MOTHER, timeout=5.0) as client:
                h = client.get("/healthz")
                if h.status_code != 200:
                    raise RuntimeError("not healthy")
                r = client.post(
                    "/api/v1/fleet/join-tokens",
                    headers=headers,
                    json={"max_uses": 20, "ttl_seconds": 86400},
                )
                r.raise_for_status()
                join = r.json()["join_token"]
                os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
                with open(OUT, "w", encoding="utf-8") as f:
                    f.write(join)
                print(f"wrote join token to {OUT}")
                return 0
        except Exception as exc:  # noqa: BLE001
            print(f"wait mother ({attempt}): {exc}", file=sys.stderr)
            time.sleep(2)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
