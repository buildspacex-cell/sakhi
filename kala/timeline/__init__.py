"""Timeline — generic temporal state containers.

The core Context OS primitive.  A ``Timeline[T]`` stores timestamped
snapshots of any state type and exposes temporal queries: state-at-time,
windowed retrieval, trend detection, and multi-source reconciliation.
"""

from kala.timeline.core import Snapshot, Timeline

__all__ = ["Snapshot", "Timeline"]
