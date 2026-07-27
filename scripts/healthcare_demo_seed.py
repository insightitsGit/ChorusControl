"""Seed a healthcare-domain scenario against a running mother.

Creates Aurora Health tenants, clinical Guard policy, PHI-labeled DEMO traces,
incident + cascade, lexicon, join tokens for clinical / pharmacy / edge agents.

Usage:
  python scripts/healthcare_demo_seed.py
"""

from __future__ import annotations

import json
import os
import sys
import time

import httpx

MOTHER = os.environ.get("CHORUSCONTROL_MOTHER_URL", "http://127.0.0.1:8443").rstrip("/")
TOKEN = os.environ.get("CHORUSCONTROL_ADMIN_TOKEN", "healthcare-demo-token")
OUT = os.environ.get("JOIN_TOKEN_FILE", "/shared/join_token")


def _client() -> httpx.Client:
    return httpx.Client(base_url=MOTHER, timeout=30.0, headers={"Authorization": f"Bearer {TOKEN}"})


def wait_ready(client: httpx.Client) -> None:
    for attempt in range(45):
        try:
            h = client.get("/healthz")
            if h.status_code == 200:
                r = client.get("/readyz")
                if r.status_code == 200 and r.json().get("ready", True):
                    return
        except Exception as exc:  # noqa: BLE001
            print(f"wait ({attempt}): {exc}", file=sys.stderr)
        time.sleep(2)
    raise SystemExit("mother not ready")


def main() -> int:
    with _client() as client:
        wait_ready(client)

        # --- Tenants (care delivery + pharmacy) ---
        for tid, name in (
            ("aurora-health", "Aurora Health System"),
            ("aurora-pharmacy", "Aurora Outpatient Pharmacy"),
        ):
            r = client.post(
                "/api/v1/admin/tenants",
                json={"tenant_id": tid, "name": name, "settings": {"domain": "healthcare"}},
            )
            if r.status_code not in (200, 400):
                print("tenant", tid, r.status_code, r.text)

        # --- Clinical Guard policy (hub path — never force law ONNX) ---
        clinical_policy = {
            "ingress_profile": "clinical_chat",
            "ingress_use_onnx": False,
            "shadow_profile": "clinical_shadow",
            "shadow_enabled": True,
            "enforce_shadow": False,
            "recommended_preset": "clinical_hub",
            "notes": "DEMO healthcare preset — PHI handling policies are illustrative only",
        }
        for tenant in ("aurora-health", "default"):
            client.put(
                "/api/v1/guard/policy",
                json={"tenant_id": tenant, "policy": clinical_policy},
            )

        # --- Clinical lexicon (DEMO terms, not real PHI) ---
        client.put(
            "/api/v1/guard/lexicon",
            json={
                "tenant_id": "aurora-health",
                "terms": [
                    "MRN",
                    "medication_reconciliation",
                    "discharge_summary",
                    "allergy_list",
                    "prior_auth",
                    "PHI_DEMO_LABEL",
                ],
            },
        )

        # --- Seed clinical execution traces ---
        for _ in range(3):
            client.post("/api/v1/traces/seed", json={"tenant_id": "aurora-health"})

        # Richer wire via ledger batch (clinical run)
        run_id = f"care-run-{int(time.time())}"
        stages = [
            {
                "stage": "guard",
                "ts": time.time(),
                "resolution_gate": "clinical_chat",
                "decision": "allow",
                "detail": {
                    "profile": "clinical_chat",
                    "demo": True,
                    "note": "DEMO — no real PHI",
                },
                "run_id": run_id,
            },
            {
                "stage": "graph",
                "ts": time.time() + 0.01,
                "hop": "route.cache_hit",
                "kind": "ledger",
                "detail": {
                    "rule_chain": ["cache", "taxonomy.clinical_guidelines"],
                    "partition": "kb_clinical_guidelines",
                },
                "run_id": run_id,
            },
            {
                "stage": "shine",
                "ts": time.time() + 0.02,
                "kind": "shine.verdict",
                "decision": "pass",
                "detail": {
                    "evidence_hash": "demo-clinical-abc",
                    "pass_means": "grounded_in_preload_not_world_true",
                    "domain": "healthcare",
                },
                "run_id": run_id,
            },
        ]
        client.post(
            "/api/v1/fleet/ledger-batch",
            json={
                "node_id": "seed",
                "tenant_id": "aurora-health",
                "run_ids": [run_id],
                "entries": stages,
            },
        )

        # --- Incident: medication reconciliation conflict ---
        inc = client.post(
            "/api/v1/incidents",
            json={
                "tenant_id": "aurora-health",
                "title": "DEMO: medication reconciliation conflict on discharge",
                "details": {
                    "domain": "healthcare",
                    "demo": True,
                    "conflict": "home_meds vs inpatient_meds diverge",
                    "severity": "high",
                },
            },
        )
        print("incident", inc.status_code, inc.json() if inc.status_code < 400 else inc.text)

        # --- Correction cascade (invalidate clinical cache tags) ---
        casc = client.post(
            "/api/v1/cascade",
            json={
                "tenant_id": "aurora-health",
                "tags": ["t:med_recon", "t:discharge", "partition:kb_clinical_guidelines"],
                "reason": "healthcare_demo_med_recon",
            },
        )
        print("cascade", casc.status_code, casc.json() if casc.status_code < 400 else casc.text)

        # --- Join token for compose agents ---
        tok = client.post(
            "/api/v1/fleet/join-tokens",
            json={"max_uses": 30, "ttl_seconds": 86400, "zone": None},
        )
        tok.raise_for_status()
        join = tok.json()["join_token"]
        os.makedirs(os.path.dirname(OUT) or ".", exist_ok=True)
        with open(OUT, "w", encoding="utf-8") as f:
            f.write(join)
        print(f"wrote join token to {OUT}")

        # Snapshot useful URLs
        doctor = client.get("/api/v1/admin/doctor")
        print(
            json.dumps(
                {
                    "mother": MOTHER,
                    "ui": f"{MOTHER}/overview",
                    "token": TOKEN,
                    "tenants": ["aurora-health", "aurora-pharmacy"],
                    "doctor_fleet": (doctor.json() or {}).get("fleet_nodes"),
                    "scenario": "Aurora Health — clinical Guard, med-recon cascade, DEMO traces",
                },
                indent=2,
            )
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
