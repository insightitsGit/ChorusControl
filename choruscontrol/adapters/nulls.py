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
    """Stateful DEMO RAG so Taxonomy warm/reindex show visible version + health changes."""

    def __init__(self) -> None:
        # tenant_id -> mutable taxonomy state
        self._state: dict[str, dict[str, Any]] = {}

    def _ensure(self, tenant_id: str) -> dict[str, Any]:
        tid = tenant_id or "default"
        if tid in self._state:
            return self._state[tid]
        clinical = tid.startswith("aurora") or tid in ("aurora-health", "aurora-pharmacy")
        if clinical:
            categories = [
                {"slug": "clinical_guidelines", "label": "Clinical guidelines"},
                {"slug": "med_recon", "label": "Medication reconciliation"},
                {"slug": "discharge", "label": "Discharge"},
                {"slug": "allergy", "label": "Allergy"},
            ]
            partitions = [
                {"partition": "kb_clinical_guidelines", "version": 1, "tenant_id": tid, "status": "ready"},
                {"partition": "kb_med_recon", "version": 1, "tenant_id": tid, "status": "ready"},
                {"partition": "kb_discharge", "version": 1, "tenant_id": tid, "status": "ready"},
            ]
            decay = [
                {"slug": "clinical_guidelines", "staleness": 0.35},
                {"slug": "med_recon", "staleness": 0.55},
                {"slug": "discharge", "staleness": 0.22},
                {"slug": "allergy", "staleness": 0.1},
            ]
            docs = [
                {
                    "category_slug": "clinical_guidelines",
                    "chunk_ref": "guideline",
                    "text": "DEMO clinical guideline: med-recon before discharge (illustrative, no PHI).",
                },
                {
                    "category_slug": "med_recon",
                    "chunk_ref": "med_recon",
                    "text": "DEMO med-recon checklist: allergy cross-check, prior_auth flags.",
                },
                {
                    "category_slug": "discharge",
                    "chunk_ref": "discharge",
                    "text": "DEMO discharge partition: summary + follow-up tags.",
                },
            ]
        else:
            categories = [
                {"slug": "risk", "label": "Risk"},
                {"slug": "growth", "label": "Growth"},
            ]
            partitions = [
                {"partition": "kb_markdown", "version": 3, "tenant_id": tid, "status": "ready"},
            ]
            decay = [
                {"slug": "risk", "staleness": 0.12},
                {"slug": "growth", "staleness": 0.4},
            ]
            docs = [
                {
                    "category_slug": "risk",
                    "chunk_ref": "risk",
                    "text": "DEMO risk note for taxonomy search.",
                },
                {
                    "category_slug": "growth",
                    "chunk_ref": "growth",
                    "text": "DEMO growth note for taxonomy search.",
                },
            ]
        self._state[tid] = {
            "categories": categories,
            "partitions": partitions,
            "decay": decay,
            "docs": docs,
            "bleed_risk": 0.08 if not clinical else 0.18,
            "last_job": None,
        }
        return self._state[tid]

    async def tree(self, tenant_id: str) -> dict[str, Any]:
        st = self._ensure(tenant_id)
        return {
            "tenant_id": tenant_id,
            "categories": list(st["categories"]),
            "demo": True,
            "last_job": st.get("last_job"),
        }

    async def search(self, tenant_id: str, query: str) -> list[dict[str, Any]]:
        st = self._ensure(tenant_id)
        q = (query or "").lower().strip()
        hits = []
        for d in st["docs"]:
            if not q or q in d["text"].lower() or q in d["category_slug"].lower():
                hits.append(
                    {
                        **d,
                        "chunk_ref": d.get("chunk_ref") or d["category_slug"],
                        "chunk_text": d["text"],
                        "tenant_id": tenant_id,
                        "score": 0.9 if q else 0.5,
                    }
                )
        if not hits and q:
            hits.append(
                {
                    "category_slug": st["categories"][0]["slug"],
                    "chunk_ref": st["categories"][0]["slug"],
                    "chunk_text": f"DEMO no exact hit for '{query}' — closest category shown.",
                    "text": f"DEMO no exact hit for '{query}' — closest category shown.",
                    "tenant_id": tenant_id,
                    "score": 0.2,
                }
            )
        return hits

    async def partitions(self, tenant_id: str) -> list[dict[str, Any]]:
        st = self._ensure(tenant_id)
        return [dict(p) for p in st["partitions"]]

    async def chunks_health(self, tenant_id: str) -> dict[str, Any]:
        st = self._ensure(tenant_id)
        return {
            "tenant_id": tenant_id,
            "decay": [dict(d) for d in st["decay"]],
            "bleed_risk": st["bleed_risk"],
            "demo": True,
            "last_job": st.get("last_job"),
        }

    def warm_partition(self, tenant_id: str, partition: str) -> None:
        import time

        time.sleep(0.05)
        st = self._ensure(tenant_id)
        part = partition or (st["partitions"][0]["partition"] if st["partitions"] else "kb_markdown")
        found = False
        for p in st["partitions"]:
            if p["partition"] == part:
                p["version"] = int(p.get("version") or 0) + 1
                p["status"] = "warm"
                p["warmed_at"] = time.time()
                found = True
                break
        if not found:
            st["partitions"].append(
                {
                    "partition": part,
                    "version": 1,
                    "tenant_id": tenant_id,
                    "status": "warm",
                    "warmed_at": time.time(),
                }
            )
        # Warming reduces staleness across related categories
        for d in st["decay"]:
            d["staleness"] = round(max(0.0, float(d.get("staleness") or 0) * 0.45), 3)
        st["bleed_risk"] = round(max(0.01, float(st.get("bleed_risk") or 0.1) * 0.7), 3)
        st["last_job"] = {
            "type": "warm_partition",
            "partition": part,
            "tenant_id": tenant_id,
            "at": time.time(),
        }

    def reindex(self, tenant_id: str, category_id: str | None = None) -> None:
        import time

        time.sleep(0.05)
        st = self._ensure(tenant_id)
        for p in st["partitions"]:
            if category_id and category_id not in p["partition"] and category_id not in (
                c["slug"] for c in st["categories"]
            ):
                continue
            p["version"] = int(p.get("version") or 0) + 1
            p["status"] = "reindexed"
            p["reindexed_at"] = time.time()
        for d in st["decay"]:
            if category_id and d["slug"] != category_id and category_id not in d["slug"]:
                continue
            d["staleness"] = 0.05
        st["bleed_risk"] = 0.04
        st["last_job"] = {
            "type": "reindex",
            "category_id": category_id,
            "tenant_id": tenant_id,
            "at": time.time(),
        }

    def reindex_category(self, tenant_id: str, category_id: str | None = None) -> None:
        self.reindex(tenant_id, category_id)
