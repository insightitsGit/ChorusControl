#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
python -m pip install -q build
python -m build
ls -la dist
echo "Upload with: twine upload dist/*"
