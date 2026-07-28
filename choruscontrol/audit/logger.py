from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

_log = logging.getLogger("choruscontrol.audit")


class AuditLogger:
    def __init__(
        self,
        private_key: ed25519.Ed25519PrivateKey,
        log_path: Path,
        kid: str = "audit-1",
        postgres: Any | None = None,
    ) -> None:
        self.private_key = private_key
        self.log_path = log_path
        self.kid = kid
        self.postgres = postgres
        self._queue: asyncio.Queue[dict[str, Any]] = asyncio.Queue()
        self._task: asyncio.Task[None] | None = None
        self.on_action: Callable[[dict[str, Any]], Awaitable[None]] | None = None

    @property
    def public_pem(self) -> str:
        return self.private_key.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        ).decode()

    def start(self) -> None:
        if self._task is None:
            self._task = asyncio.create_task(self._writer())

    async def stop(self) -> None:
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        if self.postgres:
            await self.postgres.close()

    async def log_action(
        self, admin_user: str, action: str, tenant_id: str, details: dict[str, Any]
    ) -> dict[str, Any]:
        envelope = {
            "timestamp": time.time(),
            "admin_user": admin_user,
            "action": action,
            "tenant_id": tenant_id,
            "details": details,
            "kid": self.kid,
            "event_id": str(uuid.uuid4()),
        }
        raw = json.dumps(envelope, sort_keys=True, default=str).encode("utf-8")
        envelope["signature"] = self.private_key.sign(raw).hex()
        await self._queue.put(envelope)
        if self.on_action is not None:
            try:
                await self.on_action(envelope)
            except Exception as exc:  # noqa: BLE001
                _log.warning("audit on_action hook failed: %s", exc)
        return envelope

    async def _writer(self) -> None:
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        while True:
            env = await self._queue.get()
            line = json.dumps(env, default=str) + "\n"
            await asyncio.to_thread(self._append, line)
            if self.postgres and self.postgres.ok:
                try:
                    await self.postgres.write_audit(env)
                except Exception:  # noqa: BLE001
                    # JSONL remains source of truth; Postgres is best-effort dual-write
                    pass

    def _append(self, line: str) -> None:
        with open(self.log_path, "a", encoding="utf-8") as f:
            f.write(line)


def verify_audit_line(line: str, public_pem: str) -> bool:
    from cryptography.exceptions import InvalidSignature

    env = json.loads(line)
    sig = bytes.fromhex(env.pop("signature"))
    raw = json.dumps(env, sort_keys=True, default=str).encode("utf-8")
    pub = serialization.load_pem_public_key(public_pem.encode())
    try:
        pub.verify(sig, raw)  # type: ignore[attr-defined]
        return True
    except InvalidSignature:
        return False


def load_or_create_audit_key(pem: str | None) -> ed25519.Ed25519PrivateKey:
    if pem:
        return serialization.load_pem_private_key(pem.encode(), password=None)  # type: ignore[return-value]
    return ed25519.Ed25519PrivateKey.generate()
