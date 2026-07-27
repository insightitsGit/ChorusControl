"""Guard Policy Studio validation — block unsafe hub/domain_pilot configs."""

from __future__ import annotations

from typing import Any


class PolicyValidationError(ValueError):
    def __init__(self, message: str, code: str = "POLICY_INVALID") -> None:
        super().__init__(message)
        self.code = code


def validate_guard_policy(policy: dict[str, Any]) -> dict[str, Any]:
    """Return normalized policy or raise PolicyValidationError."""
    pol = dict(policy)
    ingress = pol.get("ingress_profile") or "web_chat"
    pol["ingress_profile"] = ingress

    # Hub paths must never silently force law ONNX
    hub_profiles = ("web_chat", "finance_hub", "clinical_chat", "clinical_hub")
    if ingress in hub_profiles and pol.get("ingress_use_onnx") is True:
        raise PolicyValidationError(
            "ingress_use_onnx cannot be true for hub profiles (no silent law ONNX)",
            "UNSAFE_HUB_ONNX",
        )

    if ingress == "domain_pilot" and not pol.get("artifact_id"):
        raise PolicyValidationError(
            "domain_pilot requires artifact_id",
            "DOMAIN_PILOT_ARTIFACT",
        )

    if pol.get("enforce_shadow") and not pol.get("shadow_enabled"):
        raise PolicyValidationError(
            "enforce_shadow requires shadow_enabled",
            "SHADOW_ENFORCE_PRECONDITION",
        )

    # Recommended presets
    preset = pol.get("recommended_preset")
    if preset == "finance_hub":
        pol.setdefault("ingress_profile", "web_chat")
        pol.setdefault("ingress_use_onnx", False)
        pol.setdefault("shadow_profile", "light")
        pol.setdefault("shadow_enabled", True)
    if preset == "clinical_hub":
        pol.setdefault("ingress_profile", "clinical_chat")
        pol.setdefault("ingress_use_onnx", False)
        pol.setdefault("shadow_profile", "clinical_shadow")
        pol.setdefault("shadow_enabled", True)

    return pol


def shadow_promote_checklist(policy: dict[str, Any], compare: dict[str, Any]) -> dict[str, Any]:
    agree = float(compare.get("agree_rate") or 0)
    hub = ("web_chat", "finance_hub", "clinical_chat", "clinical_hub")
    checks = {
        "shadow_enabled": bool(policy.get("shadow_enabled")),
        "agree_rate_ge_95": agree >= 0.95,
        "not_hub_onnx": not (
            policy.get("ingress_profile") in hub and policy.get("ingress_use_onnx")
        ),
    }
    return {"ready": all(checks.values()), "checks": checks, "agree_rate": agree}
