"""Shim to execute Sakhi migration script."""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure project root is on sys.path
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from sakhi.infra.scripts.migrate import main


if __name__ == "__main__":
    main()
