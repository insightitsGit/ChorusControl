"""Local demo: boot mother in-process helpers to enroll two agents.

Usage (after `pip install -e ".[server,agent,dev]"` and mother running):

  python scripts/demo_enroll.py
"""

from __future__ import annotations

import asyncio
import os

import httpx

MOTHER = os.environ.get("CHORUSCONTROL_MOTHER_URL", "http://127.0.0.1:8443")
TOKEN = os.environ.get("CHORUSCONTROL_ADMIN_TOKEN", "dev-admin-token")


async def main() -> None:
    headers = {"Authorization": f"Bearer {TOKEN}"}
    async with httpx.AsyncClient(base_url=MOTHER, timeout=30) as client:
        r = await client.post("/api/v1/fleet/join-tokens", headers=headers)
        r.raise_for_status()
        join = r.json()["join_token"]
        print("JOIN_TOKEN=", join)
        for i, role in enumerate(["GREEN", "BLUE"], start=1):
            j = await client.post(
                "/api/v1/fleet/join",
                json={
                    "join_token": join if i == 1 else (await client.post("/api/v1/fleet/join-tokens", headers=headers)).json()["join_token"],
                    "node_id": f"demo-worker-{i}",
                    "tenant_id": "demo",
                    "role": role,
                    "products": {
                        "chorusgraph": "1.3.0",
                        "prismguard": "0.1.10",
                        "prismlib-plus": "0.8.0",
                        "prismcortex": "0.3.0",
                    },
                },
            )
            j.raise_for_status()
            print(role, j.json())


if __name__ == "__main__":
    asyncio.run(main())
