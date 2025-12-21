from __future__ import annotations

from prometheus_client import Counter, Histogram

episodes_written = Counter("episodes_written_total", "Episodes recorded")
aw_events_written = Counter("aw_events_written_total", "Awareness events recorded")
derivatives_written = Counter("derivatives_written_total", "Derivatives (mi/es/en/insight) recorded")
ingest_latency = Histogram("aw_ingest_seconds", "Event to derivative processing latency in seconds")
