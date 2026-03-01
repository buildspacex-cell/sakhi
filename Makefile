POETRY ?= poetry

.PHONY: bootstrap dev worker test format lint lint-changed db-migrate db-seed seed check-env decay-themes \
        quick-test watch-test typecheck new-route new-service status pre-commit-install \
        docs-api docs-schema verify build-check integration-test pre-commit-run \
        test-coverage test-workers test-routes test-unit test-status pre-deploy ready-to-commit \
        changelog

# ─────────────────────────────────────────────────────────────────────────────
# Development
# ─────────────────────────────────────────────────────────────────────────────

bootstrap:
	$(POETRY) install
	@echo "Installing pre-commit hooks..."
	pip install pre-commit
	pre-commit install

dev:
	$(POETRY) run uvicorn sakhi.apps.api.main:app --host 0.0.0.0 --port 8000 --reload

worker:
	$(POETRY) run python -m sakhi.apps.worker.main

status:
	@chmod +x scripts/dev-status.sh
	@./scripts/dev-status.sh

# ─────────────────────────────────────────────────────────────────────────────
# Code Quality
# ─────────────────────────────────────────────────────────────────────────────

format:
	$(POETRY) run black sakhi kala
	$(POETRY) run ruff format sakhi kala

lint:
	$(POETRY) run ruff check sakhi kala

lint-changed:
	@echo "Running ruff (critical rules) on changed Python files..."
	@CHANGED_FILES="$$( \
		{ \
			git diff --name-only --diff-filter=ACMRTUXB -- '*.py'; \
			git ls-files --others --exclude-standard -- '*.py'; \
		} | sort -u \
	)"; \
	if [ -z "$$CHANGED_FILES" ]; then \
		echo "No changed Python files to lint."; \
	else \
		printf "%s\n" "$$CHANGED_FILES" | xargs $(POETRY) run ruff check --select E9,F63,F7,F82,F821; \
	fi

typecheck:
	@echo "Checking Python imports..."
	@python -c "from sakhi.apps.api.main import app; print('Python imports OK')"
	@echo "Checking TypeScript..."
	@cd apps/web && pnpm tsc --noEmit
	@echo "TypeScript OK"

# ─────────────────────────────────────────────────────────────────────────────
# Testing
# ─────────────────────────────────────────────────────────────────────────────

test:
	$(POETRY) run pytest sakhi/tests/unit kala/tests -v --tb=short

quick-test:
	$(POETRY) run pytest \
		sakhi/tests/unit/services/test_simulation_profile_updater.py \
		sakhi/tests/unit/services/test_crystallization_engine.py \
		sakhi/tests/unit/workers/test_ayurvedic_pipeline_worker.py \
		sakhi/tests/unit/workers/test_state_workers.py \
		sakhi/tests/unit/workers/test_pattern_workers.py \
		-v --tb=short

watch-test:
	$(POETRY) run ptw sakhi/tests -- -v --tb=short

integration-test:
	$(POETRY) run pytest sakhi/tests/integration -v --tb=short

test-unit:
	$(POETRY) run pytest -m "not integration and not e2e" -v --tb=short

test-workers:
	$(POETRY) run pytest sakhi/tests/unit/workers sakhi/tests/integration/workers -v --tb=short

test-routes:
	$(POETRY) run pytest sakhi/tests/integration/routes -v --tb=short

test-coverage:
	@echo "Running tests with coverage..."
	$(POETRY) run pytest --cov=sakhi --cov-report=term-missing --cov-report=html
	@echo ""
	@echo "Coverage report generated: htmlcov/index.html"

test-status:
	@echo ""
	@echo "═══════════════════════════════════════════════════════════════"
	@echo "                    TEST STATUS SUMMARY                         "
	@echo "═══════════════════════════════════════════════════════════════"
	@echo ""
	@echo "Worker tests:"
	@find sakhi/tests -name "test_*worker*.py" -o -name "test_*_workers.py" | wc -l | xargs echo "  Files:"
	@echo ""
	@echo "Route tests:"
	@find sakhi/tests -path "*/routes/*" -name "test_*.py" | wc -l | xargs echo "  Files:"
	@echo ""
	@echo "Integration tests:"
	@find sakhi/tests/integration -name "test_*.py" 2>/dev/null | wc -l | xargs echo "  Files:"
	@echo ""
	@echo "Total test files:"
	@find sakhi/tests -name "test_*.py" -not -path "*/_archive/*" | wc -l | xargs echo "  Files:"
	@echo ""
	@echo "See docs/TEST_STATUS.md for detailed coverage tracking."
	@echo "═══════════════════════════════════════════════════════════════"

# ─────────────────────────────────────────────────────────────────────────────
# Pre-Deploy Verification
# ─────────────────────────────────────────────────────────────────────────────

pre-deploy: verify test integration-test
	@echo ""
	@echo "═══════════════════════════════════════════════════════════════"
	@echo "              PRE-DEPLOY VERIFICATION PASSED                   "
	@echo "═══════════════════════════════════════════════════════════════"
	@echo ""
	@echo "✓ Linting passed"
	@echo "✓ Type checking passed"
	@echo "✓ Unit tests passed"
	@echo "✓ Integration tests passed"
	@echo ""
	@echo "Ready to deploy!"
	@echo "═══════════════════════════════════════════════════════════════"

# ─────────────────────────────────────────────────────────────────────────────
# Code Generation
# ─────────────────────────────────────────────────────────────────────────────

new-route:
	@if [ -z "$(name)" ]; then \
		echo "Usage: make new-route name=<route_name>"; \
		echo "Example: make new-route name=wellness"; \
		exit 1; \
	fi
	@chmod +x scripts/new-route.sh
	@./scripts/new-route.sh $(name)

new-service:
	@if [ -z "$(name)" ]; then \
		echo "Usage: make new-service name=<service_name>"; \
		echo "Example: make new-service name=wellness_tracker"; \
		exit 1; \
	fi
	@chmod +x scripts/new-service.sh
	@./scripts/new-service.sh $(name)

# ─────────────────────────────────────────────────────────────────────────────
# Pre-commit
# ─────────────────────────────────────────────────────────────────────────────

pre-commit-install:
	pip install pre-commit
	pre-commit install

pre-commit-run:
	pre-commit run --all-files

# Full verification before commit (what Claude runs)
ready-to-commit: verify
	@echo ""
	@echo "Checking API imports (catches Railway errors)..."
	@$(POETRY) run python -c "from sakhi.apps.api.main import app; print('API imports OK')"
	@echo ""
	@echo "Building web app (catches Vercel errors)..."
	@cd apps/web && pnpm build
	@echo ""
	@echo "═══════════════════════════════════════════════════════════════"
	@echo "                    READY TO COMMIT                            "
	@echo "═══════════════════════════════════════════════════════════════"
	@echo ""
	@echo "✓ Linting passed"
	@echo "✓ Type checking passed"
	@echo "✓ Quick tests passed"
	@echo "✓ API imports OK (Railway)"
	@echo "✓ Web build passed (Vercel)"
	@echo ""
	@echo "Run: git add <files> && git commit -m 'type: message'"
	@echo "═══════════════════════════════════════════════════════════════"

# ─────────────────────────────────────────────────────────────────────────────
# Database
# ─────────────────────────────────────────────────────────────────────────────

db-migrate:
	$(POETRY) run python sakhi/infra/scripts/db_migrate.py

db-seed:
	$(POETRY) run python sakhi/infra/scripts/db_seed.py

seed:
	$(POETRY) run python sakhi/infra/scripts/seed_local.py

check-env:
	$(POETRY) run python sakhi/infra/scripts/check_env.py

decay-themes:
	$(POETRY) run python -c "import asyncio; from sakhi.apps.api.services.consolidate import decay_themes; asyncio.run(decay_themes())"

# ─────────────────────────────────────────────────────────────────────────────
# Documentation
# ─────────────────────────────────────────────────────────────────────────────

docs-api:
	@echo "Generating API documentation from routes..."
	@echo "# API Routes (Auto-Generated)" > docs/API_ROUTES_GENERATED.md
	@echo "" >> docs/API_ROUTES_GENERATED.md
	@echo "> Generated on $$(date)" >> docs/API_ROUTES_GENERATED.md
	@echo "" >> docs/API_ROUTES_GENERATED.md
	@find sakhi/apps/api/routes -name "*.py" -not -name "__*" | sort | while read f; do \
		echo "## $$(basename $$f .py)" >> docs/API_ROUTES_GENERATED.md; \
		echo '```python' >> docs/API_ROUTES_GENERATED.md; \
		grep -E "^@router\.(get|post|put|delete|patch)" "$$f" 2>/dev/null | head -10 >> docs/API_ROUTES_GENERATED.md || true; \
		echo '```' >> docs/API_ROUTES_GENERATED.md; \
		echo "" >> docs/API_ROUTES_GENERATED.md; \
	done
	@echo "Generated: docs/API_ROUTES_GENERATED.md"

docs-schema:
	@echo "Listing database tables..."
	@psql $$DATABASE_URL -c "\dt" > docs/TABLES_GENERATED.txt 2>/dev/null || echo "Database not available"
	@echo "Generated: docs/TABLES_GENERATED.txt"

changelog:
	@chmod +x scripts/changelog.sh
	@./scripts/changelog.sh

# ─────────────────────────────────────────────────────────────────────────────
# Build Verification
# ─────────────────────────────────────────────────────────────────────────────

verify: lint-changed typecheck quick-test
	@echo ""
	@echo "✓ All quick checks passed!"

build-check:
	@echo "Running full build verification..."
	@make lint
	@make typecheck
	@make test
	@cd apps/web && pnpm build
	@echo ""
	@echo "✓ Full build verification passed!"
