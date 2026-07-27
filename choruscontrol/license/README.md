# License trust anchor
#
# `side1_public.pem` / `side1_public.hex` — packaged Side 1 verify key (BUG-001).
# Deterministic Insight ITS trust-anchor placeholder used for Side 2 releases until
# the production ceremony public key is pinned via env or release artifact replace.
#
# Production / Azure (required for real Side 1 JWTs):
#   CHORUSCONTROL_LICENSE_PUBLIC_KEY_HEX=<output of Side 1 ceremony --public>
#   or CHORUSCONTROL_LICENSE_PUBLIC_PEM=<PEM text>
#
# Matching private for local tests only: tests/fixtures/side1_dev_private.pem
# Never ship Side 1 private keys in this package.
