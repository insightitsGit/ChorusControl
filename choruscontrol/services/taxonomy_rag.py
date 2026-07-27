"""Taxonomy PrismRAG service — search, related terms (embed/graph), online overwrite.

Uses public prismrag-patch APIs only:
  PrismRAG.ingest / .search / .list_communities / .append_chunks / .export_chunks
"""

from __future__ import annotations

import logging
import re
import threading
import time
from typing import Any

log = logging.getLogger("choruscontrol.taxonomy_rag")

_lock = threading.Lock()
_clients: dict[str, Any] = {}
_seeded: set[str] = set()


def _clinical_mapping() -> dict[str, Any]:
    return {
        "categories": [
            {"slug": "clinical_guidelines", "label": "Clinical guidelines"},
            {"slug": "med_recon", "label": "Medication reconciliation"},
            {"slug": "discharge", "label": "Discharge"},
            {"slug": "allergy", "label": "Allergy"},
        ],
        "rules": [
            {"word": "guideline", "category_slug": "clinical_guidelines", "weight": 1.0},
            {"word": "clinical", "category_slug": "clinical_guidelines", "weight": 0.8},
            {"word": "med", "category_slug": "med_recon", "weight": 1.0},
            {"word": "recon", "category_slug": "med_recon", "weight": 1.0},
            {"word": "medication", "category_slug": "med_recon", "weight": 1.0},
            {"word": "insulin", "category_slug": "med_recon", "weight": 0.9},
            {"word": "prior_auth", "category_slug": "med_recon", "weight": 0.9},
            {"word": "discharge", "category_slug": "discharge", "weight": 1.0},
            {"word": "allergy", "category_slug": "allergy", "weight": 1.0},
            {"word": "allergies", "category_slug": "allergy", "weight": 1.0},
        ],
    }


def _default_mapping() -> dict[str, Any]:
    return {
        "categories": [
            {"slug": "risk", "label": "Risk"},
            {"slug": "growth", "label": "Growth"},
        ],
        "rules": [
            {"word": "risk", "category_slug": "risk", "weight": 1.0},
            {"word": "growth", "category_slug": "growth", "weight": 1.0},
        ],
    }


def _seed_records(tenant_id: str) -> list[dict[str, str]]:
    if tenant_id.startswith("aurora") or tenant_id in ("aurora-health", "aurora-pharmacy"):
        return [
            {
                "word": "med_recon",
                "text": (
                    "Medication reconciliation checks allergies and prior_auth before discharge. "
                    "DEMO illustrative — no PHI."
                ),
            },
            {
                "word": "guideline",
                "text": (
                    "Clinical guideline: complete med recon against the allergy list and "
                    "document insulin interactions when present."
                ),
            },
            {
                "word": "discharge",
                "text": (
                    "Discharge summary includes med recon status, follow-up tags, and "
                    "allergy cross-check confirmation."
                ),
            },
            {
                "word": "insulin",
                "text": (
                    "Insulin dose review during med recon for diabetic patients (DEMO). "
                    "Relate to allergy and prior_auth flags."
                ),
            },
            {
                "word": "allergy",
                "text": (
                    "Allergy lexicon entry: cross-check drug allergies during medication "
                    "reconciliation and discharge."
                ),
            },
            {
                "word": "prior_auth",
                "text": (
                    "Prior authorization (prior_auth) flags surface during med recon when "
                    "high-cost meds need approval."
                ),
            },
        ]
    return [
        {"word": "risk", "text": "DEMO risk note for taxonomy search and embedding relations."},
        {"word": "growth", "text": "DEMO growth note for taxonomy search and embedding relations."},
    ]


def prismrag_available() -> bool:
    try:
        from prismrag_patch import PrismRAG  # noqa: F401

        return True
    except Exception:  # noqa: BLE001
        return False


def mapping_for_tenant(tenant_id: str) -> dict[str, Any]:
    tid = tenant_id or "default"
    if tid.startswith("aurora") or tid in ("aurora-health", "aurora-pharmacy"):
        return _clinical_mapping()
    return _default_mapping()


def construct_prismrag(tenant_id: str = "default") -> Any | None:
    """Build PrismRAG(mapping=…) for LiveRag / per-tenant clients (BUG-009)."""
    if not prismrag_available():
        return None
    from prismrag_patch import PrismRAG

    tid = tenant_id or "default"
    return PrismRAG(mapping=mapping_for_tenant(tid), tenant_id=tid)


def get_client(tenant_id: str) -> Any | None:
    """Lazy per-tenant PrismRAG client (MemoryStore). Returns None if package missing."""
    tid = tenant_id or "default"
    if not prismrag_available():
        return None
    with _lock:
        if tid in _clients:
            return _clients[tid]
        client = construct_prismrag(tid)
        if client is None:
            return None
        _clients[tid] = client
        return client


def taxonomy_tree(tenant_id: str) -> dict[str, Any]:
    """Category tree from mapping + live communities (non-demo when PrismRAG present)."""
    tid = tenant_id or "default"
    ensure_seeded(tid)
    client = get_client(tid)
    mapping = mapping_for_tenant(tid)
    categories = list(mapping.get("categories") or [])
    if client is None:
        return {
            "tenant_id": tid,
            "categories": categories,
            "communities": [],
            "engine": "null",
            "demo": True,
        }
    communities = []
    try:
        communities = list(client.list_communities() or [])
    except Exception as exc:  # noqa: BLE001
        log.warning("list_communities failed: %s", exc)
    return {
        "tenant_id": tid,
        "categories": categories,
        "communities": communities,
        "engine": "prismrag-patch",
        "demo": False,
    }


def taxonomy_partitions(tenant_id: str) -> dict[str, Any]:
    """Partition list derived from mapping categories + chunk counts."""
    tid = tenant_id or "default"
    ensure_seeded(tid)
    client = get_client(tid)
    mapping = mapping_for_tenant(tid)
    cats = list(mapping.get("categories") or [])
    if client is None:
        partitions = [
            {
                "partition": f"kb_{c.get('slug')}",
                "version": 1,
                "tenant_id": tid,
                "status": "demo",
                "label": c.get("label"),
            }
            for c in cats
        ]
        return {"partitions": partitions, "engine": "null", "demo": True, "tenant_id": tid}
    counts: dict[str, int] = {}
    try:
        for ch in client.export_chunks() or []:
            slug = ch.get("category_slug") or "markdown"
            counts[slug] = counts.get(slug, 0) + 1
    except Exception as exc:  # noqa: BLE001
        log.warning("export_chunks failed: %s", exc)
    partitions = []
    for c in cats:
        slug = c.get("slug") or "markdown"
        partitions.append(
            {
                "partition": f"kb_{slug}",
                "version": 1 + counts.get(slug, 0),
                "tenant_id": tid,
                "status": "ready",
                "label": c.get("label"),
                "chunk_count": counts.get(slug, 0),
            }
        )
    if not partitions:
        partitions.append(
            {
                "partition": "kb_markdown",
                "version": 1 + sum(counts.values()),
                "tenant_id": tid,
                "status": "ready",
                "chunk_count": sum(counts.values()),
            }
        )
    return {
        "partitions": partitions,
        "engine": "prismrag-patch",
        "demo": False,
        "tenant_id": tid,
    }


def taxonomy_chunks_health(tenant_id: str) -> dict[str, Any]:
    tid = tenant_id or "default"
    ensure_seeded(tid)
    client = get_client(tid)
    if client is None:
        return {"tenant_id": tid, "decay": [], "engine": "null", "demo": True}
    decay = []
    try:
        for ch in client.export_chunks() or []:
            decay.append(
                {
                    "chunk_ref": ch.get("chunk_ref"),
                    "category_slug": ch.get("category_slug"),
                    "age_hint": "fresh",
                    "embedding_dim": len(ch.get("embedding") or []),
                }
            )
    except Exception as exc:  # noqa: BLE001
        log.warning("chunks_health export failed: %s", exc)
    return {
        "tenant_id": tid,
        "decay": decay[:100],
        "engine": "prismrag-patch",
        "demo": False,
        "count": len(decay),
    }


def ensure_seeded(tenant_id: str) -> dict[str, Any]:
    tid = tenant_id or "default"
    client = get_client(tid)
    if client is None:
        return {"ok": False, "engine": "null", "seeded": False}
    with _lock:
        if tid in _seeded:
            return {
                "ok": True,
                "engine": "prismrag-patch",
                "seeded": True,
                "chunks": len(client.export_chunks()),
            }
        job = client.ingest(records=_seed_records(tid))
        _seeded.add(tid)
        log.info("taxonomy prismrag seeded tenant=%s status=%s", tid, job.get("status"))
        return {
            "ok": True,
            "engine": "prismrag-patch",
            "seeded": True,
            "ingest": {"status": job.get("status"), "community_count": job.get("community_count")},
            "chunks": len(client.export_chunks()),
        }


def _tokenize(text: str) -> list[str]:
    return [t for t in re.findall(r"[a-z0-9_]+", (text or "").lower()) if len(t) > 1]


def _related_from_communities(client: Any, query: str, hits: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Related words via community top_words + hit refs (PrismRAG graph RAG)."""
    q_tokens = set(_tokenize(query))
    related: dict[str, dict[str, Any]] = {}
    for comm in client.list_communities() or []:
        top = list(comm.get("top_words") or [])
        label = comm.get("label") or ""
        cid = comm.get("community_id")
        for w in top:
            wl = str(w).lower()
            if wl in q_tokens:
                continue
            related[wl] = {
                "term": wl,
                "source": "community",
                "community_id": cid,
                "community_label": label,
                "relation": "co-occurs in same PrismRAG community as search seeds",
            }
    for h in hits:
        ref = str(h.get("chunk_ref") or "").lower()
        if ref and ref not in q_tokens:
            related.setdefault(
                ref,
                {
                    "term": ref,
                    "source": "hit_ref",
                    "community_id": h.get("community_id"),
                    "community_label": h.get("community_label"),
                    "relation": "chunk ref retrieved for this embed search",
                },
            )
        for tok in _tokenize(h.get("chunk_text") or h.get("text") or ""):
            if tok in q_tokens or tok in related:
                continue
            if tok in {"demo", "the", "and", "for", "with", "from", "this", "that", "when"}:
                continue
            related[tok] = {
                "term": tok,
                "source": "chunk_token",
                "community_id": h.get("community_id"),
                "relation": "appears in retrieved chunk text near the query embedding",
            }
    # Prefer community terms first
    ordered = sorted(
        related.values(),
        key=lambda r: (0 if r["source"] == "community" else 1 if r["source"] == "hit_ref" else 2, r["term"]),
    )
    return ordered[:24]


def search_term(
    tenant_id: str,
    query: str,
    *,
    top_k: int = 8,
    category_filter: str | None = None,
    fallback_search=None,
) -> dict[str, Any]:
    """Search + related-term map. Uses PrismRAG when available."""
    tid = tenant_id or "default"
    q = (query or "").strip()
    seed = ensure_seeded(tid)
    client = get_client(tid)
    if client is None:
        # Null / demo fallback
        hits = []
        if fallback_search is not None:
            raw = fallback_search(tid, q)
            if hasattr(raw, "__await__"):
                raise TypeError("fallback_search must be sync or pre-awaited list")
            hits = list(raw or [])
        related = []
        for h in hits:
            for tok in _tokenize(h.get("text") or ""):
                if tok not in _tokenize(q):
                    related.append(
                        {
                            "term": tok,
                            "source": "chunk_token",
                            "relation": "token co-occurrence (NullRAG fallback — install prismrag-patch)",
                        }
                    )
        # dedupe
        seen = set()
        rel_out = []
        for r in related:
            if r["term"] in seen:
                continue
            seen.add(r["term"])
            rel_out.append(r)
        return {
            "query": q,
            "tenant_id": tid,
            "engine": "null",
            "retrieval_mode": "keyword",
            "results": [
                {
                    "chunk_ref": h.get("chunk_ref") or h.get("category_slug"),
                    "chunk_text": h.get("text") or h.get("chunk_text"),
                    "category_slug": h.get("category_slug"),
                    "score": h.get("score"),
                    "text": h.get("text") or h.get("chunk_text"),
                }
                for h in hits
            ],
            "related_terms": rel_out[:24],
            "communities": [],
            "demo": True,
            "seed": seed,
        }

    out = client.search(q or " ", top_k=top_k, category_filter=category_filter)
    hits = list(out.get("results") or out.get("hits") or [])
    # Normalize scores if missing
    for i, h in enumerate(hits):
        if h.get("score") in (None, 0.0):
            h["score"] = round(1.0 - (i * 0.08), 3)
        h["text"] = h.get("chunk_text") or h.get("text")
    related = _related_from_communities(client, q, hits)
    return {
        "query": q,
        "tenant_id": tid,
        "engine": "prismrag-patch",
        "retrieval_mode": out.get("retrieval_mode"),
        "mapping_id": out.get("mapping_id"),
        "results": hits,
        "related_terms": related,
        "communities": out.get("communities") or [],
        "demo": False,
        "seed": seed,
    }


def list_chunks(tenant_id: str) -> dict[str, Any]:
    tid = tenant_id or "default"
    ensure_seeded(tid)
    client = get_client(tid)
    if client is None:
        return {"tenant_id": tid, "chunks": [], "engine": "null", "demo": True}
    chunks = []
    for c in client.export_chunks():
        chunks.append(
            {
                "chunk_ref": c.get("chunk_ref"),
                "chunk_text": c.get("chunk_text"),
                "category_slug": c.get("category_slug"),
                "community_id": c.get("community_id"),
                "embedding_dim": len(c.get("embedding") or []),
            }
        )
    return {
        "tenant_id": tid,
        "chunks": chunks,
        "engine": "prismrag-patch",
        "demo": False,
        "count": len(chunks),
    }


def overwrite_chunk(
    tenant_id: str,
    *,
    chunk_ref: str,
    text: str,
    category_slug: str | None = None,
    new_rules: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """Online overwrite via PrismRAG.append_chunks (upsert by ref)."""
    tid = tenant_id or "default"
    ref = (chunk_ref or "").strip()
    body = (text or "").strip()
    if not ref:
        raise ValueError("chunk_ref required")
    if not body:
        raise ValueError("text required")
    ensure_seeded(tid)
    client = get_client(tid)
    if client is None:
        raise RuntimeError(
            "prismrag-patch not installed — cannot overwrite online. "
            'pip install "prismrag-patch==0.2.1"'
        )
    rules = list(new_rules or [])
    if category_slug:
        # Reinforce mapping so the rewritten text stays in the intended category
        for tok in _tokenize(body)[:8]:
            rules.append({"word": tok, "category_slug": category_slug, "weight": 0.7})
    results = client.append_chunks(
        [{"ref": ref, "text": body}],
        new_rules=rules or None,
        include_vectors=True,
    )
    row = results[0] if results else {}
    emb = row.get("embedding") or []
    return {
        "ok": True,
        "tenant_id": tid,
        "engine": "prismrag-patch",
        "chunk_ref": row.get("chunk_ref") or ref,
        "chunk_text": row.get("chunk_text") or body,
        "category_slug": row.get("category_slug") or category_slug,
        "confidence": row.get("confidence"),
        "quality_score": row.get("quality_score"),
        "flagged": row.get("flagged"),
        "embedding_dim": len(emb) if isinstance(emb, list) else 0,
        "embedding_preview": (emb[:8] if isinstance(emb, list) else []),
        "overwritten_at": time.time(),
    }


def related_terms(tenant_id: str, query: str) -> dict[str, Any]:
    """Dedicated related-term view (same engine as search)."""
    packed = search_term(tenant_id, query, top_k=5)
    return {
        "query": packed["query"],
        "tenant_id": packed["tenant_id"],
        "engine": packed["engine"],
        "related_terms": packed["related_terms"],
        "communities": packed.get("communities") or [],
        "retrieval_mode": packed.get("retrieval_mode"),
    }
