from __future__ import annotations

import json
import secrets
import time
import uuid
from typing import Any

from choruscontrol.persistence import Store


class FleetRegistry:
    def __init__(self, store: Store, postgres: Any | None = None) -> None:
        self.store = store
        self.postgres = postgres

    async def _mirror_token(self, token: str) -> None:
        if not self.postgres or not getattr(self.postgres, "control_plane", False):
            return
        row = await self.store.fetchone("SELECT * FROM join_tokens WHERE token=?", (token,))
        if row:
            await self.postgres.upsert_join_token(dict(row))

    async def _mirror_node(self, node_id: str) -> None:
        if not self.postgres or not getattr(self.postgres, "control_plane", False):
            return
        row = await self.store.fetchone("SELECT * FROM nodes WHERE node_id=?", (node_id,))
        if row:
            await self.postgres.upsert_node(dict(row))

    async def create_join_token(
        self,
        *,
        ttl_seconds: int = 3600,
        max_uses: int = 1,
        zone: str | None = None,
        node_id_bind: str | None = None,
    ) -> str:
        token = secrets.token_urlsafe(24)
        await self.store.execute(
            "INSERT INTO join_tokens(token, max_uses, uses, expires_at, zone, node_id_bind, created_at) "
            "VALUES(?,?,?,?,?,?,?)",
            (token, max_uses, 0, time.time() + ttl_seconds, zone, node_id_bind, time.time()),
        )
        await self._mirror_token(token)
        return token

    async def join(
        self,
        *,
        join_token: str,
        node_id: str | None,
        tenant_id: str,
        role: str,
        network_zone: str,
        products: dict[str, str],
        caps_digest: str | None,
        memory_endpoint: str | None,
        max_nodes: int,
    ) -> dict[str, Any]:
        row = await self.store.fetchone("SELECT * FROM join_tokens WHERE token=?", (join_token,))
        if not row:
            raise ValueError("invalid join token")
        if row["expires_at"] < time.time():
            raise ValueError("join token expired")
        if row["uses"] >= row["max_uses"]:
            raise ValueError("join token exhausted")
        if row["node_id_bind"] and node_id and row["node_id_bind"] != node_id:
            raise ValueError("node_id does not match bind")
        if row["zone"] and row["zone"] != network_zone:
            raise ValueError("network_zone mismatch")

        active = await self.store.fetchone(
            "SELECT COUNT(*) AS c FROM nodes WHERE revoked=0"
        )
        count = int(active["c"]) if active else 0
        nid = node_id or f"node-{uuid.uuid4().hex[:8]}"
        existing = await self.store.fetchone("SELECT node_id FROM nodes WHERE node_id=?", (nid,))
        if not existing and count >= max_nodes:
            raise ValueError("max_nodes exceeded")

        session_secret = secrets.token_urlsafe(32)
        await self.store.execute(
            "INSERT INTO nodes(node_id, tenant_id, role, network_zone, products_json, caps_digest, "
            "last_seen, memory_endpoint, session_secret, revoked) VALUES(?,?,?,?,?,?,?,?,?,0) "
            "ON CONFLICT(node_id) DO UPDATE SET tenant_id=excluded.tenant_id, role=excluded.role, "
            "network_zone=excluded.network_zone, products_json=excluded.products_json, "
            "caps_digest=excluded.caps_digest, last_seen=excluded.last_seen, "
            "memory_endpoint=excluded.memory_endpoint, session_secret=excluded.session_secret, revoked=0",
            (
                nid,
                tenant_id,
                role,
                network_zone,
                json.dumps(products),
                caps_digest,
                time.time(),
                memory_endpoint,
                session_secret,
            ),
        )
        await self.store.execute(
            "UPDATE join_tokens SET uses = uses + 1 WHERE token=?", (join_token,)
        )
        await self._mirror_token(join_token)
        await self._mirror_node(nid)
        return {"node_id": nid, "session_secret": session_secret}

    async def require_session(self, node_id: str, session_secret: str | None) -> dict[str, Any]:
        """Authenticate agent write paths (BUG-004). Uses secrets.compare_digest."""
        import secrets

        row = await self.store.fetchone("SELECT * FROM nodes WHERE node_id=?", (node_id,))
        if not row or row["revoked"]:
            raise ValueError("unknown or revoked node")
        expected = row["session_secret"] or ""
        provided = session_secret or ""
        if not expected or not provided or not secrets.compare_digest(expected, provided):
            raise ValueError("invalid session")
        return dict(row)

    async def heartbeat(
        self,
        *,
        node_id: str,
        session_secret: str,
        products: dict[str, str],
        caps_digest: str | None,
        role: str | None = None,
        memory_endpoint: str | None = None,
    ) -> None:
        row = await self.require_session(node_id, session_secret)
        _ = row
        day = time.strftime("%Y-%m-%d", time.gmtime())
        if memory_endpoint is not None:
            await self.store.execute(
                "UPDATE nodes SET products_json=?, caps_digest=?, last_seen=?, "
                "role=COALESCE(?, role), memory_endpoint=? WHERE node_id=?",
                (json.dumps(products), caps_digest, time.time(), role, memory_endpoint, node_id),
            )
        else:
            await self.store.execute(
                "UPDATE nodes SET products_json=?, caps_digest=?, last_seen=?, role=COALESCE(?, role) WHERE node_id=?",
                (json.dumps(products), caps_digest, time.time(), role, node_id),
            )
        await self.store.execute(
            "INSERT INTO version_snapshots(node_id, day, products_json, caps_digest) VALUES(?,?,?,?) "
            "ON CONFLICT(node_id, day) DO UPDATE SET products_json=excluded.products_json, "
            "caps_digest=excluded.caps_digest",
            (node_id, day, json.dumps(products), caps_digest),
        )
        await self._mirror_node(node_id)

    async def list_nodes(self) -> list[dict[str, Any]]:
        rows = await self.store.fetchall("SELECT * FROM nodes WHERE revoked=0 ORDER BY last_seen DESC")
        out = []
        for r in rows:
            item = {
                **r,
                "products": json.loads(r["products_json"]),
                "online": (time.time() - r["last_seen"]) < 30,
            }
            # BUG-008 — never expose session secrets on list/topology APIs
            item.pop("session_secret", None)
            out.append(item)
        return out

    async def revoke(self, node_id: str) -> None:
        await self.store.execute("UPDATE nodes SET revoked=1 WHERE node_id=?", (node_id,))
        await self._mirror_node(node_id)

    async def memory_endpoint_for_tenant(self, tenant_id: str) -> str | None:
        row = await self.store.fetchone(
            "SELECT memory_endpoint, node_id, role FROM nodes WHERE tenant_id=? AND revoked=0 "
            "AND memory_endpoint IS NOT NULL AND memory_endpoint != '' "
            "ORDER BY CASE WHEN lower(role) IN ('memory','cortex') THEN 0 ELSE 1 END, last_seen DESC",
            (tenant_id,),
        )
        if not row:
            row = await self.store.fetchone(
                "SELECT node_id FROM nodes WHERE tenant_id=? AND lower(role) IN ('memory','cortex') "
                "AND revoked=0",
                (tenant_id,),
            )
            return f"local://{row['node_id']}" if row else None
        return row["memory_endpoint"] or f"local://{row['node_id']}"

    def features_for_products(self, products: dict[str, str]) -> set[str]:
        """R07 version negotiation."""
        feats: set[str] = {"heartbeat", "caps"}
        cg = products.get("chorusgraph", "0")
        pl = products.get("prismlib-plus") or products.get("prismlib") or "0"
        if _ver_at_least(pl, "0.8.0"):
            feats.update({"invalidate_tags", "invalidate_where"})
        elif _ver_at_least(pl, "0.5.0"):
            feats.add("invalidate_tags")
        if _ver_at_least(cg, "1.1.0"):
            feats.add("warm_partition")
        if _ver_at_least(cg, "1.3.0"):
            feats.add("mark_revalidate")
        if "prismcortex" in products:
            feats.add("cortex.sleep")
        if "prismrag_patch" in products or "prismrag-patch" in products:
            feats.add("taxonomy.reindex")
        if "prismguard" in products:
            feats.add("guard.policy")
        return feats


def _ver_at_least(current: str, need: str) -> bool:
    def parts(v: str) -> list[int]:
        out: list[int] = []
        for p in v.split("."):
            digits = "".join(c for c in p if c.isdigit())
            out.append(int(digits or 0))
        return out

    a, b = parts(current), parts(need)
    n = max(len(a), len(b))
    a += [0] * (n - len(a))
    b += [0] * (n - len(b))
    return a >= b
