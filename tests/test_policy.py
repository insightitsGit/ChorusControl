"""Guard Policy Studio validation."""

import pytest

from choruscontrol.services.policy import PolicyValidationError, validate_guard_policy


def test_blocks_hub_onnx():
    with pytest.raises(PolicyValidationError):
        validate_guard_policy({"ingress_profile": "web_chat", "ingress_use_onnx": True})


def test_domain_pilot_needs_artifact():
    with pytest.raises(PolicyValidationError):
        validate_guard_policy({"ingress_profile": "domain_pilot"})


def test_finance_hub_ok():
    pol = validate_guard_policy(
        {"ingress_profile": "web_chat", "ingress_use_onnx": False, "recommended_preset": "finance_hub"}
    )
    assert pol["ingress_use_onnx"] is False
