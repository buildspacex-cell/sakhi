from collections import deque
from typing import Deque, Literal
import json
import os

import redis

Decision = Literal["ACK", "ASK", "DO"]
TARGET = {"ACK": 0.60, "ASK": 0.25, "DO": 0.15}
WINDOW = int(os.getenv("CONV_BALANCE_WINDOW", "20"))
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
r = redis.from_url(REDIS_URL)


def _key(user_id: str) -> str:
    return f"conv:balance:{user_id}"


def _load(user_id: str) -> Deque[str]:
    raw = r.get(_key(user_id))
    if not raw:
        return deque(maxlen=WINDOW)
    arr = json.loads(raw)
    dq: Deque[str] = deque(arr, maxlen=WINDOW)
    return dq


def _save(user_id: str, dq: Deque[str]) -> None:
    r.set(_key(user_id), json.dumps(list(dq)), ex=86400)


def push(user_id: str, decision: Decision) -> None:
    dq = _load(user_id)
    dq.append(decision)
    _save(user_id, dq)


def mix(user_id: str) -> tuple[float, float, float]:
    dq = _load(user_id)
    n = max(1, len(dq))
    ack = sum(1 for t in dq if t == "ACK") / n
    ask = sum(1 for t in dq if t == "ASK") / n
    do = sum(1 for t in dq if t == "DO") / n
    return ack, ask, do


def nudge(user_id: str, proposed: Decision) -> Decision:
    ack, ask, do = mix(user_id)
    deficits = {
        "ACK": TARGET["ACK"] - ack,
        "ASK": TARGET["ASK"] - ask,
        "DO": TARGET["DO"] - do,
    }
    if deficits[proposed] >= -0.05:
        return proposed
    return max(deficits, key=deficits.get)  # type: ignore[return-value]
