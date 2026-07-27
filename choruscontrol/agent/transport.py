from __future__ import annotations

"""HTTP primary transport (R01). Fabric is optional secondary."""

from typing import Any

import httpx


class HttpControlTransport:
    """Agent → mother control channel over HTTP (PrismAPI-shaped)."""

    def __init__(self, mother_url: str, timeout: float = 10.0) -> None:
        self.mother_url = mother_url.rstrip("/")
        self.timeout = timeout

    async def join(self, payload: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.post(f"{self.mother_url}/api/v1/fleet/join", json=payload)
            r.raise_for_status()
            return r.json()

    async def heartbeat(self, payload: dict[str, Any]) -> dict[str, Any]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.post(f"{self.mother_url}/api/v1/fleet/heartbeat", json=payload)
            r.raise_for_status()
            return r.json()

    async def poll_commands(self, node_id: str, session_secret: str) -> list[dict[str, Any]]:
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.get(
                f"{self.mother_url}/api/v1/fleet/nodes/{node_id}/commands",
                headers={"X-Node-Session": session_secret},
            )
            if r.status_code == 404:
                return []
            r.raise_for_status()
            return r.json().get("commands", [])

    async def ack(self, payload: dict[str, Any]) -> None:
        session = payload.get("session_secret") or ""
        headers = {"X-Node-Session": session} if session else {}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.post(
                f"{self.mother_url}/api/v1/fleet/ack", json=payload, headers=headers
            )
            r.raise_for_status()

    async def ledger_batch(self, payload: dict[str, Any]) -> None:
        session = payload.get("session_secret") or ""
        headers = {"X-Node-Session": session} if session else {}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.post(
                f"{self.mother_url}/api/v1/fleet/ledger-batch",
                json=payload,
                headers=headers,
            )
            r.raise_for_status()


class FabricControlTransport:
    """Optional Fabric backend — degrades if chorus-fabric not installed."""

    def __init__(self, endpoint: str | None) -> None:
        self.endpoint = endpoint
        self._ok = False
        try:
            import chorus_fabric  # noqa: F401

            self._ok = True
        except ImportError:
            self._ok = False

    @property
    def available(self) -> bool:
        return self._ok and bool(self.endpoint)

    async def broadcast_signal(self, payload: dict[str, Any]) -> None:
        if not self.available:
            return
        # Placeholder: real CHORUSPublisher wiring when fabric extra installed
        return
