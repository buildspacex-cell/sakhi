import datetime as dt
import os

STM_TTL_DAYS = int(os.getenv("STM_TTL_DAYS", "14") or "14")


def compute_expires_at(created_at: dt.datetime | None = None) -> dt.datetime:
    """
    Return expiry timestamp for a short-term memory row using STM_TTL_DAYS.
    Defaults to UTC now when created_at is absent.
    """
    base = created_at or dt.datetime.utcnow()
    return base + dt.timedelta(days=STM_TTL_DAYS)
