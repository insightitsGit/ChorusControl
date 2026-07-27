"""OIDC role mapping + auth modes."""

from choruscontrol.auth.oidc import OIDCValidator
from choruscontrol.auth.rbac import parse_bearer
from choruscontrol.config import get_settings


def test_oidc_role_mapping():
    v = OIDCValidator.__new__(OIDCValidator)
    v.role_claim = "chorus_roles"
    assert v._map_role({"chorus_roles": ["operator"]}) == "operator"
    assert v._map_role({"chorus_roles": ["admin", "viewer"]}) == "admin"
    assert v._map_role({"realm_access": {"roles": ["chorus_security"]}}) == "security"
    assert v._map_role({}) == "viewer"


def test_local_token_still_works(monkeypatch):
    monkeypatch.setenv("CHORUSCONTROL_OIDC_ENABLED", "0")
    get_settings.cache_clear()
    from choruscontrol.auth.oidc import reset_oidc_cache

    reset_oidc_cache()
    p = parse_bearer("Bearer dev-admin-token", "dev-admin-token")
    assert p.role == "admin"
    assert p.auth == "token"
    p2 = parse_bearer("Bearer dev-admin-token|alice|operator", "dev-admin-token")
    assert p2.user == "alice"
    assert p2.role == "operator"
