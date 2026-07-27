from __future__ import annotations

import asyncio
import json

from cryptography.hazmat.primitives.asymmetric import ed25519

from choruscontrol.audit.logger import AuditLogger, verify_audit_line


def test_audit_roundtrip(tmp_path):
    key = ed25519.Ed25519PrivateKey.generate()
    path = tmp_path / "a.jsonl"
    logger = AuditLogger(key, path)

    async def run():
        logger.start()
        await logger.log_action("admin", "test", "t1", {"x": 1})
        await asyncio.sleep(0.1)
        await logger.stop()

    asyncio.run(run())
    lines = path.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    assert verify_audit_line(lines[0], logger.public_pem)
    env = json.loads(lines[0])
    env["signature"] = "00" * 64
    assert not verify_audit_line(json.dumps(env), logger.public_pem)
