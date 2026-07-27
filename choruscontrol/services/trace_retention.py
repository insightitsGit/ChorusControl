"""Trace retention purge (R03)."""

from __future__ import annotations

import time
from typing import Any


async def purge_traces(store, *, retention_days: int, max_rows: int) -> dict[str, Any]:
    cutoff = time.time() - max(1, retention_days) * 86400
    before_t = await store.fetchone("SELECT COUNT(*) AS c FROM traces")
    before_l = await store.fetchone("SELECT COUNT(*) AS c FROM ledger_entries")
    await store.execute("DELETE FROM traces WHERE created_at < ?", (cutoff,))
    await store.execute("DELETE FROM ledger_entries WHERE created_at < ?", (cutoff,))
    # Enforce row-count quota on traces (oldest first)
    count_row = await store.fetchone("SELECT COUNT(*) AS c FROM traces")
    count = int((count_row or {}).get("c") or 0)
    excess = max(0, count - max_rows)
    if excess > 0:
        old = await store.fetchall(
            "SELECT run_id FROM traces ORDER BY created_at ASC LIMIT ?", (excess,)
        )
        for r in old:
            rid = r["run_id"]
            await store.execute("DELETE FROM ledger_entries WHERE run_id=?", (rid,))
            await store.execute("DELETE FROM traces WHERE run_id=?", (rid,))
    after_t = await store.fetchone("SELECT COUNT(*) AS c FROM traces")
    after_l = await store.fetchone("SELECT COUNT(*) AS c FROM ledger_entries")
    return {
        "traces_before": int((before_t or {}).get("c") or 0),
        "traces_after": int((after_t or {}).get("c") or 0),
        "ledger_before": int((before_l or {}).get("c") or 0),
        "ledger_after": int((after_l or {}).get("c") or 0),
        "cutoff": cutoff,
    }
