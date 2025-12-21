from __future__ import annotations

import json
import uuid
from datetime import date, datetime, time
from decimal import Decimal
from typing import Any


class EnhancedJSONEncoder(json.JSONEncoder):
    """JSON encoder that supports UUID, datetime, Decimal, etc."""

    def default(self, obj: Any) -> Any:
        if isinstance(obj, uuid.UUID):
            return str(obj)
        if isinstance(obj, (datetime, date, time)):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return float(obj)
        return super().default(obj)

