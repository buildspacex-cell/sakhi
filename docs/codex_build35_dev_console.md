# Build 35 – Dev Console & Testing Harness

## Summary
- Added `system_events` table + logger to capture every journaling, reflection, rhythm, analytics, and breath update.
- Introduced `/events/stream/{person_id}` SSE endpoint and upgraded the front-end Debug Panel to display live events.
- Created a mock user simulator to push 100 messages and exercise workers, caches, and event streams.

## Testing Steps
1. Apply migration `V035__system_events.sql` to the database.
2. Run API + workers, then execute `scripts/mock_user_stream.py` to send 100 synthetic messages.
3. Manually trigger workers:
   ```bash
   python -m sakhi.apps.worker enqueue run_reflection_jobs
   python -m sakhi.apps.worker enqueue run_rhythm_forecast
   python -m sakhi.apps.worker enqueue sync_analytics_cache
   python -m sakhi.apps.worker enqueue update_system_tempo
   ```
4. Visit `/journal` in the web app, toggle the Debug panel, and confirm color-coded events stream in real time.

## SQL Checks
```sql
SELECT layer, COUNT(*) FROM system_events GROUP BY layer;
SELECT * FROM system_events ORDER BY id DESC LIMIT 10;
SELECT * FROM rhythm_forecasts ORDER BY created_at DESC LIMIT 3;
SELECT * FROM analytics_cache ORDER BY computed_at DESC LIMIT 3;
```

## Expected Outcomes
- Each `/memory/observe` call emits a `journal` event.
- `run_daily_reflection` / `run_weekly_summary` log `reflection` events.
- Rhythm forecasts and breath sync emit `rhythm` / `breath` updates.
- Nightly cache sync logs `analytics` events.
- Dev Console displays new events within ~1 second.
