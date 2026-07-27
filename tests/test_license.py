from __future__ import annotations

import time

from cryptography.hazmat.primitives.asymmetric import ed25519

from choruscontrol.license import LicenseClaims, LicenseVerifier, set_dev_private_for_tests


def test_license_valid_and_grace():
    private = ed25519.Ed25519PrivateKey.generate()
    set_dev_private_for_tests(private)
    from choruscontrol.license import verifier as vmod

    v = LicenseVerifier(public_pem=vmod.DEV_PUBLIC_PEM, grace_days=14, clock_skew_seconds=86400)
    now = int(time.time())
    claims = LicenseClaims(sub="acme", iat=now - 10, exp=now + 3600, license_id="lic1")
    token = v.issue_dev_token(claims, private)
    st = v.verify(token, now=float(now))
    assert st.state == "valid"

    expired = LicenseClaims(sub="acme", iat=now - 100000, exp=now - 100_000, license_id="lic2")
    token2 = v.issue_dev_token(expired, private)
    st2 = v.verify(token2, now=float(now))
    assert st2.state == "grace"

    ancient = LicenseClaims(sub="acme", iat=now - 10_000_000, exp=now - 2_000_000, license_id="lic3")
    token3 = v.issue_dev_token(ancient, private)
    st3 = v.verify(token3, now=float(now))
    assert st3.state == "invalid"
