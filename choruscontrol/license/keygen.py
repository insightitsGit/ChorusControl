from __future__ import annotations

import argparse

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519

from choruscontrol.license.verifier import LicenseClaims, LicenseVerifier


def main() -> None:
    parser = argparse.ArgumentParser(description="Issue a ChorusControl DEV license (not for production)")
    parser.add_argument("--sub", default="dev-org")
    parser.add_argument("--days", type=int, default=365)
    parser.add_argument("--tier", default="enterprise")
    parser.add_argument("--max-nodes", type=int, default=32)
    parser.add_argument("--write-keys", action="store_true")
    args = parser.parse_args()

    private = ed25519.Ed25519PrivateKey.generate()
    if args.write_keys:
        priv_pem = private.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )
        pub_pem = private.public_key().public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        open("choruscontrol_dev_private.pem", "wb").write(priv_pem)
        open("choruscontrol_dev_public.pem", "wb").write(pub_pem)
        print("Wrote choruscontrol_dev_private.pem / choruscontrol_dev_public.pem")

    import time

    now = int(time.time())
    claims = LicenseClaims(
        sub=args.sub,
        iat=now,
        exp=now + args.days * 86400,
        tier=args.tier,  # type: ignore[arg-type]
        max_nodes=args.max_nodes,
        license_id=f"lic_dev_{args.sub}",
    )
    # Temporarily use generated key for encode via jwt + cryptography
    from choruscontrol.license import verifier as vmod

    vmod.set_dev_private_for_tests(private)
    token = LicenseVerifier(public_pem=vmod.DEV_PUBLIC_PEM).issue_dev_token(claims, private)
    print(token)


if __name__ == "__main__":
    main()
