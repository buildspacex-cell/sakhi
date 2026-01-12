# Deploy TODO

- Reset lab-only STM eviction override: set `LAB_DISABLE_STM_EVICT=0` (or remove) for production so STM cleanup runs normally.
- Ensure turn jobs are queued (not inline): unset `SAKHI_DISABLE_QUEUE` so workers run asynchronously in production.
