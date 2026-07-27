"""Multi-domain enterprise policies (beyond Guard studio)."""

from __future__ import annotations

import json
import time
import uuid
from typing import Any

DOMAINS = ("memory.write", "model.allowlist", "deployment.approval")


async def upsert_policy(
    store,
    *,
    domain: str,
    tenant_id: str,
    name: str,
    body: dict[str, Any],
) -> dict[str, Any]:
    if domain not in DOMAINS:
        raise ValueError(f"unsupported domain {domain}; allowed={DOMAINS}")
    existing = await store.fetchone(
        "SELECT * FROM enterprise_policies WHERE domain=? AND tenant_id=? AND name=?",
        (domain, tenant_id, name),
    )
    now = time.time()
    if existing:
        version = int(existing["version"]) + 1
        await store.execute(
            "UPDATE enterprise_policies SET body_json=?, version=?, updated_at=? WHERE policy_id=?",
            (json.dumps(body), version, now, existing["policy_id"]),
        )
        pid = existing["policy_id"]
    else:
        version = 1
        pid = f"ep-{uuid.uuid4().hex[:10]}"
        await store.execute(
            "INSERT INTO enterprise_policies(policy_id, domain, tenant_id, name, body_json, version, updated_at) "
            "VALUES(?,?,?,?,?,?,?)",
            (pid, domain, tenant_id, name, json.dumps(body), version, now),
        )
    return {
        "policy_id": pid,
        "domain": domain,
        "tenant_id": tenant_id,
        "name": name,
        "body": body,
        "version": version,
        "updated_at": now,
    }


async def list_policies(store, tenant_id: str | None = None) -> list[dict[str, Any]]:
    if tenant_id:
        rows = await store.fetchall(
            "SELECT * FROM enterprise_policies WHERE tenant_id=? ORDER BY domain, name",
            (tenant_id,),
        )
    else:
        rows = await store.fetchall("SELECT * FROM enterprise_policies ORDER BY domain, name")
    return [{**r, "body": json.loads(r["body_json"])} for r in rows]


async def get_policy(store, policy_id: str) -> dict[str, Any] | None:
    row = await store.fetchone("SELECT * FROM enterprise_policies WHERE policy_id=?", (policy_id,))
    if not row:
        return None
    return {**row, "body": json.loads(row["body_json"])}


async def check_allowed(
    store,
    *,
    domain: str,
    tenant_id: str,
    action: str,
    context: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Enforce domain policy. Missing policy = allow (fail-open with note) for pilot; deny if explicit."""
    ctx = context or {}
    rows = await store.fetchall(
        "SELECT * FROM enterprise_policies WHERE domain=? AND tenant_id=?",
        (domain, tenant_id),
    )
    if not rows:
        rows = await store.fetchall(
            "SELECT * FROM enterprise_policies WHERE domain=? AND tenant_id='*'",
            (domain,),
        )
    if not rows:
        return {"allowed": True, "reason": "no_policy", "domain": domain, "action": action}

    for r in rows:
        body = json.loads(r["body_json"])
        mode = (body.get("mode") or "allowlist").lower()
        if domain == "memory.write":
            if body.get("deny_all"):
                return {"allowed": False, "reason": "deny_all", "policy_id": r["policy_id"]}
            writers = body.get("allowed_roles") or body.get("allow") or []
            role = ctx.get("role") or "operator"
            if mode == "allowlist" and writers and role not in writers:
                return {
                    "allowed": False,
                    "reason": "role_not_allowlisted",
                    "policy_id": r["policy_id"],
                    "role": role,
                }
        elif domain == "model.allowlist":
            allowed = body.get("models") or body.get("allow") or []
            model = ctx.get("model")
            if allowed and model and model not in allowed:
                return {
                    "allowed": False,
                    "reason": "model_not_allowlisted",
                    "policy_id": r["policy_id"],
                    "model": model,
                }
        elif domain == "deployment.approval":
            if body.get("require_approval") and not ctx.get("approved"):
                return {
                    "allowed": False,
                    "reason": "approval_required",
                    "policy_id": r["policy_id"],
                }
    return {"allowed": True, "reason": "policy_ok", "domain": domain, "action": action}
