"""Trace wire: Guard → Ledger → Shine stitch + zero-token replay."""

from __future__ import annotations

import json
import time
import uuid
from typing import Any


async def seed_demo_trace(store, tenant_id: str = "default") -> str:
    run_id = f"run-{uuid.uuid4().hex[:10]}"
    wire = {
        "v": 1,
        "run_id": run_id,
        "tenant_id": tenant_id,
        "stages": [
            {
                "stage": "guard",
                "ts": time.time(),
                "resolution_gate": "structural",
                "decision": "allow",
                "detail": {"profile": "web_chat"},
            },
            {
                "stage": "graph",
                "ts": time.time() + 0.01,
                "hop": "route.cache_hit",
                "kind": "ledger",
                "detail": {"rule_chain": ["cache", "taxonomy"]},
            },
            {
                "stage": "shine",
                "ts": time.time() + 0.02,
                "kind": "shine.verdict",
                "decision": "pass",
                "detail": {"evidence_hash": "abc123", "pass_means": "grounded_in_preload_not_world_true"},
            },
        ],
    }
    await store.execute(
        "INSERT INTO traces(run_id, tenant_id, wire_json, created_at) VALUES(?,?,?,?)",
        (run_id, tenant_id, json.dumps(wire), time.time()),
    )
    for stage in wire["stages"]:
        await store.execute(
            "INSERT INTO ledger_entries(tenant_id, node_id, run_id, payload_json, sampled, created_at) "
            "VALUES(?,?,?,?,0,?)",
            (tenant_id, "mother", run_id, json.dumps(stage), time.time()),
        )
    return run_id


async def list_traces(store, tenant_id: str, limit: int = 50) -> list[dict[str, Any]]:
    rows = await store.fetchall(
        "SELECT run_id, tenant_id, created_at FROM traces WHERE tenant_id=? ORDER BY created_at DESC LIMIT ?",
        (tenant_id, limit),
    )
    if not rows:
        await seed_demo_trace(store, tenant_id)
        rows = await store.fetchall(
            "SELECT run_id, tenant_id, created_at FROM traces WHERE tenant_id=? ORDER BY created_at DESC LIMIT ?",
            (tenant_id, limit),
        )
    return rows


async def get_trace(store, run_id: str) -> dict[str, Any] | None:
    row = await store.fetchone("SELECT * FROM traces WHERE run_id=?", (run_id,))
    if not row:
        return None
    return {
        "run_id": row["run_id"],
        "tenant_id": row["tenant_id"],
        "created_at": row["created_at"],
        "wire": json.loads(row["wire_json"]),
    }


async def get_ledger(store, run_id: str) -> list[dict[str, Any]]:
    rows = await store.fetchall(
        "SELECT * FROM ledger_entries WHERE run_id=? ORDER BY id ASC", (run_id,)
    )
    return [{**r, "payload": json.loads(r["payload_json"])} for r in rows]


async def replay_trace(store, run_id: str) -> dict[str, Any]:
    """Zero-token replay — cache/ledger only; assert no LLM provider calls."""
    tr = await get_trace(store, run_id)
    if not tr:
        raise KeyError(run_id)
    ledger = await get_ledger(store, run_id)
    steps = []
    llm_calls = 0
    warnings: list[str] = []
    cascade_row = await store.fetchone(
        "SELECT cascade_id, created_at, details_json FROM cascades WHERE tenant_id=? "
        "ORDER BY created_at DESC LIMIT 1",
        (tr["tenant_id"],),
    )
    for entry in ledger:
        payload = entry["payload"]
        if payload.get("kind") == "call_llm" or payload.get("stage") == "llm":
            llm_calls += 1
        cached_ts = payload.get("ts") or entry.get("created_at") or 0
        if cascade_row and float(cascade_row["created_at"]) > float(cached_ts or 0):
            if "CACHE_PREDATES_FACT_UPDATE" not in warnings:
                warnings.append("CACHE_PREDATES_FACT_UPDATE")
        steps.append(
            {
                "stage": payload.get("stage"),
                "decision": payload.get("decision"),
                "from_cache": True,
            }
        )
    return {
        "run_id": run_id,
        "mode": "zero_token_replay",
        "steps": steps,
        "llm_calls": llm_calls,
        "ok": llm_calls == 0,
        "assert": "no call_llm / provider on replay path",
        "warnings": warnings,
        "CACHE_PREDATES_FACT_UPDATE": "CACHE_PREDATES_FACT_UPDATE" in warnings,
    }


def stitch_from_entries(entries: list[dict[str, Any]]) -> dict[str, Any]:
    stages = []
    for e in entries:
        p = e.get("payload") or e
        stages.append(
            {
                "stage": p.get("stage"),
                "ts": p.get("ts") or e.get("created_at"),
                "resolution_gate": p.get("resolution_gate"),
                "hop": p.get("hop"),
                "kind": p.get("kind"),
                "decision": p.get("decision"),
                "detail": p.get("detail") or {},
            }
        )
    return {"v": 1, "wire": "guard -> ledger -> shine", "stages": stages}
