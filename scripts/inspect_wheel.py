"""Assert release wheel includes UI assets and Side 1 trust anchors."""
from __future__ import annotations

import glob
import sys
import zipfile

REQUIRED = (
    "choruscontrol/ui/static/app.js",
    "choruscontrol/ui/static/app.css",
    "choruscontrol/ui/static/viz.js",
    "choruscontrol/ui/templates/shell.html",
    "choruscontrol/license/side1_public.pem",
    "choruscontrol/license/side1_public.hex",
)


def main() -> int:
    wheels = sorted(glob.glob("dist/*.whl"))
    if not wheels:
        print("FAIL: no wheel in dist/", file=sys.stderr)
        return 1
    path = wheels[-1]
    with zipfile.ZipFile(path) as z:
        names = set(z.namelist())
    missing = [r for r in REQUIRED if r not in names]
    if missing:
        print(f"FAIL: {path} missing:", *missing, sep="\n  ", file=sys.stderr)
        return 1
    print(f"OK: {path} includes UI + license trust anchors")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
