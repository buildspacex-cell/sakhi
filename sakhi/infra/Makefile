PYTHON ?= python3
POETRY ?= poetry

.PHONY: bootstrap dev worker test format lint db-migrate db-seed

bootstrap:
	$(POETRY) install

dev:
	$(POETRY) run uvicorn sakhi.apps.api.main:app --host 0.0.0.0 --port 8000 --reload

worker:
	$(POETRY) run python -m sakhi.apps.worker.main

format:
	$(POETRY) run black sakhi
	$(POETRY) run ruff format sakhi

lint:
	$(POETRY) run ruff check sakhi

test:
	$(POETRY) run pytest

db-migrate:
	$(POETRY) run python sakhi/infra/scripts/db_migrate.py

db-seed:
	$(POETRY) run python sakhi/infra/scripts/db_seed.py
