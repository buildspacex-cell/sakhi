"""
Sakhi v2 Test Suite

Run all tests: pytest sakhi/tests/v2/ -v
Run smoke tests: pytest sakhi/tests/v2/test_smoke.py -v
Run with DB: DATABASE_URL=... pytest sakhi/tests/v2/ -v

Test structure:
- test_smoke.py       - Quick health checks (imports, DB connection)
- test_turn_v2.py     - Turn endpoint and job enqueueing
- test_workers.py     - Turn workers and daily workers
- test_context_loader.py - Context loading for LLM
"""
