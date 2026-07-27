# License trust anchor
#
# `side1_public.pem` / `side1_public.hex` — packaged Side 1 Ed25519 verify key
# (BUG-001 / BUG-007). Production Key Vault ceremony public (2026-07-27).
#
# Hex (raw 32-byte public):
#   5d78a9a4e654312c8ae5dd10792d46b53974868f8c8b5346cb3c5abef320e37c
#
# Override only if you must pin a different issuer (rare):
#   CHORUSCONTROL_LICENSE_PUBLIC_KEY_HEX=<32-byte hex>
#   or CHORUSCONTROL_LICENSE_PUBLIC_PEM=<PEM text>
#
# Local unit tests that need to *sign* JWTs use tests/fixtures/side1_dev_private.pem
# (dev keypair — not the ceremony private). Never ship Side 1 private keys.
