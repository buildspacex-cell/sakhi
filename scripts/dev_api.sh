#!/usr/bin/env bash
set -euo pipefail
ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT_DIR"

export PYTHONPATH=.

CANDIDATES=(
  "apps.api.main:app"
  "apps.api.main:api"
  "apps.api.server:app"
  "apps.api.app:app"
)

for mod in "${CANDIDATES[@]}"; do
  if python - <<PY 2>/dev/null
import importlib
import sys
sys.path.append('.')
mod, var = "$mod".split(':', 1)
m = importlib.import_module(mod)
assert hasattr(m, var)
print("OK")
PY
  then
    echo "Launching $mod"
    exec uvicorn "$mod" --reload --port 8000
  fi
done

echo "Could not find an ASGI app. Tried:"
printf ' - %s\n' "${CANDIDATES[@]}"
exit 1
