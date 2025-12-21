POETRY ?= poetry

.PHONY: dev worker intel test seed check-env migrate-personal-model decay-themes

dev:
	$(POETRY) run uvicorn sakhi.apps.api.main:app --host 0.0.0.0 --port 8000 --reload

worker:
	python -m apps.worker.worker

intel:
	python -m apps.worker.intel_orchestrator

consolidator:
	python -m apps.worker.jobs.runner

test:
	$(POETRY) run pytest

seed:
	$(POETRY) run python sakhi/infra/scripts/seed_local.py

check-env:
	$(POETRY) run python sakhi/infra/scripts/check_env.py

migrate-personal-model:
	psql "$$DATABASE_URL" -f infra/sql/20251104_personal_model.sql

decay-themes:
	$(POETRY) run python -c "import asyncio; from sakhi.apps.api.services.consolidate import decay_themes; asyncio.run(decay_themes())"
