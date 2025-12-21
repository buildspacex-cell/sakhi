#!/usr/bin/env bash

set -euo pipefail

ENV_FILE="${ENV_FILE:-.env.worker}"
if [ -f "$ENV_FILE" ]; then
  set -a
  # shellcheck disable=SC1090
  source "$ENV_FILE"
  set +a
else
  echo "Warning: $ENV_FILE not found; proceeding with current environment." >&2
fi

PYTHONPATH=. python sakhi/apps/worker/main.py "$@"
