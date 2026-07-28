"""Automated compliance findings (not a SOC2 certification claim)."""

from __future__ import annotations

import json
import time
import uuid
from typing import Any


async def record_finding(
    store,
    *,
    severity: str,
    code: str,
    title: str,
    detail: dict[str, Any],
) -> dict[str, Any]:
    finding_id = f"cf-{uuid.uuid4().hex[:10]}"
    await store.execute(
        "INSERT INTO compliance_findings(finding_id, severity, code, title, detail_json, created_at, resolved) "
        "VALUES(?,?,?,?,?,?,0)",
        (finding_id, severity, code, title, json.dumps(detail), time.time()),
    )
    return {
        "finding_id": finding_id,
        "severity": severity,
        "code": code,
        "title": title,
        "detail": detail,
    }


async def list_findings(store, *, include_resolved: bool = False, limit: int = 100) -> list[dict[str, Any]]:
    if include_resolved:
        rows = await store.fetchall(
            "SELECT * FROM compliance_findings ORDER BY created_at DESC LIMIT ?", (limit,)
        )
    else:
        rows = await store.fetchall(
            "SELECT * FROM compliance_findings WHERE resolved=0 ORDER BY created_at DESC LIMIT ?",
            (limit,),
        )
    return [{**r, "detail": json.loads(r["detail_json"])} for r in rows]


async def run_compliance_scan(state) -> dict[str, Any]:
    """Doctor + license + audit integrity style checks → findings rows."""
    findings: list[dict[str, Any]] = []
    s = state

    # Clear prior open auto findings with same codes (replace scan)
    await s.store.execute(
        "UPDATE compliance_findings SET resolved=1 WHERE resolved=0 AND code LIKE 'auto.%'"
    )

    lic = s.license_status
    if lic.state == "grace":
        findings.append(
            await record_finding(
                s.store,
                severity="high",
                code="auto.license.grace",
                title="License in grace window",
                detail={"state": lic.state, "grace_remaining_seconds": lic.grace_remaining_seconds},
            )
        )
    elif lic.state not in ("valid", "grace"):
        findings.append(
            await record_finding(
                s.store,
                severity="critical",
                code="auto.license.invalid",
                title="License invalid",
                detail={"state": lic.state, "message": lic.message},
            )
        )

    if s.settings.database_url and s.postgres is not None:
        ok = await s.postgres.ping()
        if not ok:
            findings.append(
                await record_finding(
                    s.store,
                    severity="high",
                    code="auto.postgres.down",
                    title="Postgres control/audit sink unreachable",
                    detail={"error": s.postgres.last_error},
                )
            )

    if s.settings.allow_insecure_external:
        findings.append(
            await record_finding(
                s.store,
                severity="medium",
                code="auto.tls.insecure_external",
                title="Insecure external fleet joins allowed",
                detail={"env": "CHORUSCONTROL_ALLOW_INSECURE_EXTERNAL"},
            )
        )

    # Only flag core NullAdapters in non-demo (BUG-013). Optional fabric/mesh/lang null is OK.
    CORE_ADAPTERS = {"guard", "shine", "cortex", "graph", "rag", "cache"}
    nulls = [
        k
        for k, v in (s.adapter_sources or {}).items()
        if v == "null" and k in CORE_ADAPTERS
    ]
    if nulls and not s.settings.demo_mode:
        findings.append(
            await record_finding(
                s.store,
                severity="medium",
                code="auto.adapters.null",
                title="Core NullAdapters in non-demo deploy",
                detail={"adapters": nulls, "note": "optional fabric/mesh/lang null not flagged"},
            )
        )

    nodes = await s.fleet.list_nodes()
    without_mem = [n["node_id"] for n in nodes if n.get("role") in ("memory", "cortex") and not n.get("memory_endpoint")]
    if without_mem:
        findings.append(
            await record_finding(
                s.store,
                severity="low",
                code="auto.cortex.unaddressed",
                title="Memory-role nodes without memory_endpoint",
                detail={"nodes": without_mem},
            )
        )

    return {
        "ok": True,
        "findings": findings,
        "count": len(findings),
        "note": "Automated posture scan — not a formal SOC2 attestation",
    }
