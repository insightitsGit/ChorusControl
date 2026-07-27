from __future__ import annotations

from typing import Any


class NullCache:
    def __init__(self) -> None:
        self._store: dict[str, Any] = {}
        self.evicted_by_tags = 0
        self.evicted_by_vector = 0

    async def get_metrics(self) -> dict[str, Any]:
        return {
            "hit_rate": 0.92,
            "tokens_saved": 125000,
            "cost_saved_usd": 18.5,
            "evicted_by_tags": self.evicted_by_tags,
            "evicted_by_vector": self.evicted_by_vector,
            "demo": True,
        }

    async def invalidate_tags(self, tags: list[str]) -> int:
        self.evicted_by_tags += len(tags)
        return len(tags)

    async def invalidate_where(self, probe: list[float], threshold: float) -> int:
        self.evicted_by_vector += 1
        return 1


class NullFabric:
    def __init__(self) -> None:
        self.signals: list[dict[str, Any]] = []

    async def broadcast_signal(self, payload: dict[str, Any]) -> None:
        self.signals.append(payload)

    async def peer_count(self) -> int:
        return len({s.get("node_id") for s in self.signals}) or 0


class NullGuard:
    def __init__(self) -> None:
        self._lexicon: dict[str, list[str]] = {"default": ["fx", "rate", "budget"]}

    async def caps(self, profile: str) -> dict[str, Any]:
        return {
            "profile": profile,
            "onnx_tier": None if profile == "web_chat" else "light",
            "onnx_ready": profile != "web_chat",
            "prismrag_taxonomy": profile == "domain_pilot",
            "shadow_onnx": True,
            "demo": True,
        }

    async def recent_logs(self, limit: int = 50) -> list[dict[str, Any]]:
        return [
            {
                "decision": "allow",
                "resolution_gate": "structural",
                "prompt_preview": "What is FX rate?",
            }
        ][:limit]

    async def shadow_compare(self, profile: str, shadow: str) -> dict[str, Any]:
        return {
            "profile": profile,
            "shadow": shadow,
            "agree_rate": 0.97,
            "divergences": [{"prompt": "edge case", "ingress": "allow", "shadow": "flag"}],
            "demo": True,
        }

    async def get_lexicon(self, tenant_id: str) -> list[str]:
        return list(self._lexicon.get(tenant_id, self._lexicon["default"]))

    async def put_lexicon(self, tenant_id: str, terms: list[str]) -> list[str]:
        self._lexicon[tenant_id] = list(terms)
        return self._lexicon[tenant_id]


class NullShine:
    async def capabilities(self) -> dict[str, Any]:
        return {
            "span_backend": "lexical",
            "threshold_status": "proposal",
            "pass_means": "grounded_in_preload_not_world_true",
            "demo": True,
        }


class NullCortex:
    def __init__(self) -> None:
        self._conflicts = [
            {
                "id": "c1",
                "tenant_hint": "default",
                "fact": "deploy_budget",
                "old": "$40,000",
                "new": "$55,000",
            }
        ]
        self.sleep_calls: list[str] = []

    async def facts(self, tenant_id: str) -> list[dict[str, Any]]:
        return [
            {"fact": "deploy_budget", "value": "$55,000", "status": "active", "tenant_id": tenant_id},
            {
                "fact": "deploy_budget",
                "value": "$40,000",
                "status": "superseded",
                "tenant_id": tenant_id,
            },
        ]

    async def conflicts(self, tenant_id: str) -> list[dict[str, Any]]:
        return [c for c in self._conflicts if c.get("tenant_hint") in (tenant_id, "default")]

    async def resolve_conflict(
        self, tenant_id: str, conflict_id: str, resolution: dict[str, Any]
    ) -> dict[str, Any]:
        self._conflicts = [c for c in self._conflicts if c["id"] != conflict_id]
        return {"resolved": conflict_id, "tenant_id": tenant_id, "resolution": resolution}

    def sleep(self, tenant_id: str) -> None:
        import time

        time.sleep(0.05)
        self.sleep_calls.append(tenant_id)

    async def explain(self, tenant_id: str, query: str) -> dict[str, Any]:
        return {
            "tenant_id": tenant_id,
            "query": query,
            "path": ["fact:deploy_budget", "supersession"],
            "demo": True,
        }

    async def recall_at(self, tenant_id: str, ts: float, query: str) -> dict[str, Any]:
        return {
            "tenant_id": tenant_id,
            "ts": ts,
            "query": query,
            "facts": [{"fact": "deploy_budget", "value": "$40,000"}],
            "demo": True,
        }


class NullGraph:
    async def dogfood(self) -> dict[str, Any]:
        return {"ok": True, "workers": 2, "demo": True}

    async def mark_revalidate(self, tenant_id: str, tags: list[str]) -> None:
        return None

    async def driver_latency(self) -> dict[str, Any]:
        return {"p50_ms": 12.4, "p99_ms": 48.0, "qps": 120, "demo": True}


class NullRag:
    async def tree(self, tenant_id: str) -> dict[str, Any]:
        return {
            "tenant_id": tenant_id,
            "categories": [
                {"slug": "risk", "label": "Risk"},
                {"slug": "growth", "label": "Growth"},
            ],
        }

    async def search(self, tenant_id: str, query: str) -> list[dict[str, Any]]:
        return [{"category_slug": "risk", "text": f"Hit for {query}", "tenant_id": tenant_id}]

    async def partitions(self, tenant_id: str) -> list[dict[str, Any]]:
        return [{"partition": "kb_markdown", "version": 3, "tenant_id": tenant_id}]

    async def chunks_health(self, tenant_id: str) -> dict[str, Any]:
        return {
            "tenant_id": tenant_id,
            "decay": [{"slug": "risk", "staleness": 0.12}, {"slug": "growth", "staleness": 0.4}],
            "bleed_risk": 0.08,
            "demo": True,
        }

    def warm_partition(self, tenant_id: str, partition: str) -> None:
        import time

        time.sleep(0.05)
