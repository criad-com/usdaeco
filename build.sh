#!/usr/bin/env bash
set -euo pipefail
cd -- "$(dirname -- "${BASH_SOURCE[0]}")"
export PYTHON="${PYTHON:-python3}"
echo "== stage: suite source verification"
env -u PYTHONPATH "$PYTHON" tools/usdaeco_suite/pins.py --check
env -u PYTHONPATH "$PYTHON" check.py
echo "== stage: integrated stage"
env -u PYTHONPATH "$PYTHON" stage/build.py "$@"
