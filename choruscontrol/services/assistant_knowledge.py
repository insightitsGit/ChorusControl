"""Ops Assistant knowledge: fleet roles, zones, and known agents (plain English)."""

from __future__ import annotations

from typing import Any

# PrismLib Micro cluster roles (design section 3.14) + what that means for ops.
ROLE_PLAIN: dict[str, dict[str, str]] = {
    "GREEN": {
        "label": "GREEN  -  active master",
        "means": (
            "Primary healthy worker. Handles live heartbeats, product probes, and cascade acks "
            "for its tenant/zone. On Overview, GREEN means the node is the active master color."
        ),
        "does": (
            "Runs as the main enrolled agent beside app/worker containers; mother trusts it for "
            "fleet topology, version snapshots, and invalidation coverage."
        ),
        "when_bad": "If GREEN goes offline, Operational health drops and cascade ack coverage may stall.",
    },
    "BLUE": {
        "label": "BLUE  -  warm standby",
        "means": (
            "Healthy standby worker that can auto-promote. Same heartbeat/product contract as GREEN, "
            "but topology paints it as warm standby."
        ),
        "does": (
            "Keeps a second tenant or standby path warm (e.g. pharmacy). Ready to take traffic/"
            "commands if the master path is disrupted."
        ),
        "when_bad": "A stale BLUE weakens standby coverage; Overview may show ORANGE for that node.",
    },
    "ORANGE": {
        "label": "ORANGE  -  syncing reserve / edge",
        "means": (
            "Reserve or edge node. Also the color Overview uses when a worker looks stale. "
            "Intentional ORANGE role = syncing reserve (often external/clinic edge)."
        ),
        "does": (
            "Joins from a satellite or reserve path; still heartbeats and acks cascades, but is not "
            "the active master. Useful for blast-radius and multi-site demos."
        ),
        "when_bad": "Stale ORANGE is expected if the edge clinic is offline  -  check TLS join and heartbeat.",
    },
    "WORKER": {
        "label": "WORKER  -  generic agent",
        "means": "Enrolled fleet agent without a GREEN/BLUE/ORANGE topology paint.",
        "does": "Heartbeats products, receives commands, acks correction cascades.",
        "when_bad": "Offline workers shrink Operational health (60 + 5 per enrolled node).",
    },
}

ZONE_PLAIN: dict[str, str] = {
    "in_vpc": (
        "Inside the customer VPC/on-prem network next to mother. Normal join; HTTP to mother is fine."
    ),
    "external": (
        "Outside the VPC (clinic edge, partner site). External agents need TLS-capable mother URL "
        "and a join token; spoofed joins are rejected."
    ),
}

# Known demo / named agents  -  full job descriptions Ops Assistant should recite.
AGENT_CATALOG: dict[str, dict[str, Any]] = {
    "aurora-clinical-green": {
        "title": "Aurora Clinical (GREEN master)",
        "aliases": ["clinical", "clinical green", "clinical agent", "green agent", "hospital"],
        "tenant": "aurora-health",
        "role": "GREEN",
        "zone": "in_vpc",
        "mission": (
            "Primary clinical hospital worker for Aurora Health System. Sits beside clinical chat / "
            "med-recon / discharge pathways under tenant aurora-health."
        ),
        "does": [
            "Heartbeats as the GREEN active master so Overview fleet topology stays healthy.",
            "Reports product inventory (ChorusGraph / Prism pack versions) for Doctor pin floors.",
            "Receives correction cascades for tags like t:med_recon, t:discharge, and "
            "partition:kb_clinical_guidelines after the DEMO med-recon incident.",
            "Accepts operator commands (warm/reindex-related jobs) scoped through mother.",
            "Grounds clinical Guard policy (clinical_hub / clinical_chat ingress) for this site.",
        ],
        "does_not": [
            "Does not run the six UI tabs  -  mother owns Overview/Trace/Taxonomy/Memory/Guard/Admin.",
            "Does not hold real PHI in this DEMO (lexicon/traces are labeled illustrative).",
            "Does not issue licenses or call insightits.com (Side 1 is out of band).",
        ],
        "related": [
            "Tenant aurora-health",
            "Guard preset clinical_hub",
            "DEMO incident: medication reconciliation conflict",
            "Partners with aurora-pharmacy-blue (pharmacy tenant) and aurora-edge-orange (clinic edge)",
        ],
    },
    "aurora-pharmacy-blue": {
        "title": "Aurora Outpatient Pharmacy (BLUE standby)",
        "aliases": ["pharmacy", "pharmacy blue", "pharmacy agent", "blue agent", "outpatient"],
        "tenant": "aurora-pharmacy",
        "role": "BLUE",
        "zone": "in_vpc",
        "mission": (
            "Warm-standby pharmacy domain worker for Aurora Outpatient Pharmacy. Isolated tenant "
            "aurora-pharmacy so clinical and pharmacy blast radii stay separate in the demo."
        ),
        "does": [
            "Heartbeats as BLUE warm standby (auto-promote semantics in topology).",
            "Keeps pharmacy-side product versions visible in fleet inventory.",
            "Participates in cascade ack coverage from the pharmacy network zone.",
            "Shows multi-tenant fleet: mother can operate clinical + pharmacy without mixing tenants.",
        ],
        "does_not": [
            "Does not replace the clinical GREEN master for hospital chat wires.",
            "Does not store real prescriptions  -  DEMO NullAdapters only.",
        ],
        "related": [
            "Tenant aurora-pharmacy",
            "Standby to aurora-clinical-green for topology storytelling",
            "Same mother, separate Policy Studio / incident scoping by tenant_id",
        ],
    },
    "aurora-edge-orange": {
        "title": "Aurora Edge Clinic (ORANGE reserve)",
        "aliases": ["edge", "edge orange", "edge agent", "orange agent", "clinic", "satellite"],
        "tenant": "aurora-health",
        "role": "ORANGE",
        "zone": "external",
        "mission": (
            "Satellite / clinic-edge reserve agent for Aurora Health. Same clinical tenant, but "
            "network_zone=external to show out-of-VPC join + TLS-aware enrollment."
        ),
        "does": [
            "Joins mother with an external-zone join path (edge clinic pattern).",
            "Heartbeats as ORANGE syncing reserve on the Overview topology strip.",
            "Still acks cascades for clinical tags so edge sites invalidate stale cache/knowledge.",
            "Demonstrates multi-site blast radius: hospital GREEN + edge ORANGE under one tenant.",
        ],
        "does_not": [
            "Is not the active master  -  GREEN remains primary inside the VPC.",
            "Should not be mistaken for 'broken' just because the color is orange; role ORANGE is intentional.",
        ],
        "related": [
            "Tenant aurora-health (shared with clinical GREEN)",
            "Zone external vs clinical/pharmacy in_vpc",
            "Useful when asking about TLS agents or edge clinics",
        ],
    },
}

PLATFORM_BRIEF = """\
ChorusControl is mother + fleet agents (Side 2 only):

- **Mother**  -  AI Ops control plane: six tabs, license verify, Policy Studio, cascade publisher, \
audit, jobs, Ops Assistant, Asset Graph. One mother per deployment.
- **Agent** (`choruscontrol[agent]`)  -  thin worker on every app/container: join with a token, \
heartbeat products/caps, pull commands, ack correction cascades. Agents do **not** host the UI.
- **Join**  -  Admin issues a join token; agent presents it once. External zone may require TLS.
- **Heartbeat**  -  keeps node online on Overview; carries role, zone, tenant, product versions.
- **Cascade**  -  mother publishes invalidation tags; workers ack. Coverage shows who is pending.
- **Honest caps**  -  Shine PASS / Guard ALLOW are preload/policy grounded, never world-truth.
- **DEMO**  -  NullAdapters are labeled DEMO until live Prism packs pass Doctor pin floors.
"""


def role_key(role: str | None) -> str:
    r = (role or "WORKER").upper()
    if r in ROLE_PLAIN:
        return r
    if "GREEN" in r:
        return "GREEN"
    if "BLUE" in r:
        return "BLUE"
    if "ORANGE" in r:
        return "ORANGE"
    return "WORKER"


def catalog_for(node_id: str | None) -> dict[str, Any] | None:
    if not node_id:
        return None
    nid = node_id.lower()
    if nid in AGENT_CATALOG:
        return AGENT_CATALOG[nid]
    for key, meta in AGENT_CATALOG.items():
        if key in nid or nid in key:
            return meta
        for alias in meta.get("aliases") or []:
            if alias in nid:
                return meta
    return None


def match_catalog_from_question(q: str) -> tuple[str, dict[str, Any]] | None:
    """Return (catalog_id, meta) if the question names a known agent or alias."""
    ql = q.lower()
    # Prefer exact id hits
    for key, meta in AGENT_CATALOG.items():
        if key in ql:
            return key, meta
    # Alias hits (longer first)
    scored: list[tuple[int, str, dict[str, Any]]] = []
    for key, meta in AGENT_CATALOG.items():
        for alias in meta.get("aliases") or []:
            if alias in ql:
                scored.append((len(alias), key, meta))
    if scored:
        scored.sort(reverse=True)
        return scored[0][1], scored[0][2]
    return None


def enrich_node(n: dict[str, Any]) -> dict[str, Any]:
    """Attach plain-English role/zone/catalog fields to a live fleet row."""
    nid = n.get("id") or n.get("node_id") or ""
    role = role_key(n.get("role"))
    zone = n.get("zone") or n.get("network_zone") or "in_vpc"
    cat = catalog_for(nid)
    products = n.get("products") or {}
    if isinstance(products, dict):
        product_list = [f"{k}@{v}" for k, v in list(products.items())[:8]]
    else:
        product_list = list(products)[:8]
    return {
        "id": nid,
        "role": role,
        "role_label": ROLE_PLAIN[role]["label"],
        "zone": zone,
        "zone_means": ZONE_PLAIN.get(zone, f"Network zone `{zone}`."),
        "online": bool(n.get("online")),
        "tenant_id": n.get("tenant_id"),
        "products": product_list,
        "catalog_id": next((k for k, v in AGENT_CATALOG.items() if v is cat), None) if cat else None,
        "title": (cat or {}).get("title") or nid,
        "mission": (cat or {}).get("mission")
        or ROLE_PLAIN[role]["does"],
    }


def explain_role(role: str | None) -> str:
    meta = ROLE_PLAIN[role_key(role)]
    return (
        f"**{meta['label']}**\n"
        f"{meta['means']}\n"
        f"What it does: {meta['does']}\n"
        f"If unhealthy: {meta['when_bad']}"
    )


def explain_agent(
    node: dict[str, Any] | None,
    *,
    catalog_id: str | None = None,
    catalog: dict[str, Any] | None = None,
) -> str:
    """Full plain-English card for one agent (live node + catalog)."""
    cat = catalog
    cid = catalog_id
    if cat is None and cid:
        cat = AGENT_CATALOG.get(cid)
    if cat is None and node:
        cat = catalog_for(node.get("id") or node.get("node_id"))
        cid = (node or {}).get("catalog_id") or cid

    lines: list[str] = []
    if cat:
        title = cat["title"]
        lines.append(f"**{title}**" + (f" (`{cid}`)" if cid else ""))
        lines.append(cat["mission"])
        lines.append("")
        lines.append("What this agent does:")
        for item in cat.get("does") or []:
            lines.append(f"- {item}")
        if cat.get("does_not"):
            lines.append("")
            lines.append("What it does **not** do:")
            for item in cat["does_not"]:
                lines.append(f"- {item}")
        if cat.get("related"):
            lines.append("")
            lines.append("Related context:")
            for item in cat["related"]:
                lines.append(f"- {item}")
    elif node:
        lines.append(f"**{node.get('title') or node.get('id')}**")
        lines.append(node.get("mission") or explain_role(node.get("role")))
    else:
        return "I do not have a catalog entry for that agent yet. Ask 'who are the agents?' for the live fleet."

    if node:
        lines.append("")
        lines.append("Live status right now:")
        lines.append(
            f"- Online: **{'yes' if node.get('online') else 'no / stale'}**; "
            f"role **{node.get('role')}**; zone **{node.get('zone')}**; "
            f"tenant **{node.get('tenant_id') or 'n/a'}**."
        )
        if node.get("zone_means"):
            lines.append(f"- Zone meaning: {node['zone_means']}")
        if node.get("products"):
            lines.append(f"- Products reporting: {', '.join(node['products'])}")
        else:
            lines.append("- Products: none reported on last heartbeat yet.")
        lines.append(f"- Topology: {ROLE_PLAIN[role_key(node.get('role'))]['label']}")
    elif cat:
        lines.append("")
        lines.append(
            f"Catalog defaults: role {cat.get('role')}, zone {cat.get('zone')}, "
            f"tenant {cat.get('tenant')} (may differ once enrolled)."
        )
    return "\n".join(lines)


def explain_fleet(nodes: list[dict[str, Any]], *, online: int, total: int) -> str:
    lines = [
        f"Fleet right now: **{online}/{total}** agents online.",
        "",
        PLATFORM_BRIEF.strip(),
        "",
        "Topology colors (GREEN / BLUE / ORANGE):",
        f"- {ROLE_PLAIN['GREEN']['label']}: {ROLE_PLAIN['GREEN']['means']}",
        f"- {ROLE_PLAIN['BLUE']['label']}: {ROLE_PLAIN['BLUE']['means']}",
        f"- {ROLE_PLAIN['ORANGE']['label']}: {ROLE_PLAIN['ORANGE']['means']}",
        "",
        "Enrolled agents:",
    ]
    if not nodes:
        lines.append("- None yet  -  issue a join token from Admin and start agents.")
    for n in nodes:
        status = "online" if n.get("online") else "stale"
        lines.append(
            f"- **{n.get('title') or n['id']}** (`{n['id']}`)  -  {n.get('role_label') or n.get('role')}, "
            f"{status}, zone={n.get('zone')}, tenant={n.get('tenant_id')}. "
            f"{(n.get('mission') or '')[:160]}"
        )
    lines.append("")
    lines.append(
        "Ask 'what does the clinical agent do?', 'explain pharmacy blue', or "
        "'what is GREEN vs ORANGE?' for full detail."
    )
    return "\n".join(lines)


def find_live_node(nodes: list[dict[str, Any]], catalog_id: str | None, q: str) -> dict[str, Any] | None:
    ql = q.lower()
    if catalog_id:
        for n in nodes:
            if n.get("id") == catalog_id or n.get("catalog_id") == catalog_id:
                return n
            if catalog_id in (n.get("id") or ""):
                return n
    for n in nodes:
        nid = (n.get("id") or "").lower()
        if nid and nid in ql:
            return n
        title = (n.get("title") or "").lower()
        if title and title in ql:
            return n
    return None
