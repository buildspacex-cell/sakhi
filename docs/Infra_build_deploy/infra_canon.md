Sakhi — Infrastructure Canon

Repo Structure, Build Nuances, Deployment Discipline

This document captures non-obvious but critical infrastructure truths of the Sakhi codebase.

It exists to:

prevent circular debugging

preserve hard-won context

align humans, Codex, and CI/CD

keep product work unblocked

If something here feels overly explicit, that is intentional.

1. Repository Structure (Canonical)

Sakhi is a monorepo with a shared top-level Python package.

Required Root Layout
.
├── Dockerfile                 ← MUST live at repo root
├── pyproject.toml
├── poetry.lock
├── sakhi/                      ← Top-level Python package (non-negotiable)
│   ├── __init__.py
│   ├── apps/
│   │   ├── api/
│   │   │   ├── main.py         ← FastAPI entrypoint
│   │   │   └── routes/
│   │   ├── worker/
│   │   │   └── jobs.py
│   ├── libs/
│   │   ├── embeddings.py
│   │   └── retrieval.py
│   └── schemas/
├── docs/
│   └── infra-canon.md          ← this document
└── ...

Invariants

sakhi/ must exist at repo root

sakhi/ must be a real Python package (__init__.py)

All imports assume sakhi as the top-level namespace

Any container that does not contain /app/sakhi is invalid.

2. FastAPI Entrypoint (Authoritative)

The only valid FastAPI app is:

sakhi/apps/api/main.py


The application object is:

app = FastAPI(...)

Correct Uvicorn Target
sakhi.apps.api.main:app

Known Silent Failure

Using:

uvicorn main:app


will:

start successfully

expose zero routes

return endless 404s

This is the single most misleading failure mode in the system.

3. Dockerfile (Final, Canonical)
Location

Must live at repo root

Railway build context = Dockerfile directory

Canonical Dockerfile
FROM python:3.11-slim

WORKDIR /app

# Dependency metadata
COPY pyproject.toml poetry.lock* ./

# Disable Poetry virtualenvs inside container
ENV POETRY_VIRTUALENVS_CREATE=false

RUN python -m pip install --no-cache-dir poetry==1.8.3 \
 && poetry install --no-ansi --without dev

# Copy full repo (must include /sakhi)
COPY . .

# Make repo root importable
ENV PYTHONPATH=/app

# Start API
CMD ["python", "-m", "uvicorn", "sakhi.apps.api.main:app", "--host", "0.0.0.0", "--port", "8080"]

4. Why These Choices Matter (Hard Lessons)
4.1 Build Context

Railway only builds what’s under the Dockerfile directory.

If Dockerfile is in apps/api/, the container will not include sakhi/, causing:

ModuleNotFoundError: No module named 'sakhi'

4.2 PYTHONPATH

Even with correct files copied, Python cannot resolve sakhi unless:

ENV PYTHONPATH=/app


is set.

4.3 Poetry Virtualenvs

Poetry defaults to isolated venvs, which breaks runtime execution:

python -m uvicorn → No module named uvicorn


Solution (mandatory):

ENV POETRY_VIRTUALENVS_CREATE=false

5. Dependency Boundary Reality

The API process imports shared modules that workers also use.

Example chain:

api.main
 → sakhi.apps
   → sakhi.apps.worker.jobs
     → sakhi.libs.embeddings
       → openai.AsyncOpenAI

Implication

API image must include all transitive dependencies

openai must be in [tool.poetry.dependencies]

This is intentional until API/worker images are fully split.

6. Poetry Lock Discipline (Non-Optional)

Any change to pyproject.toml requires syncing the lock file.

Correct Procedure
poetry lock --no-update
git add poetry.lock
git commit -m "chore(deps): sync poetry.lock"


Never:

delete poetry.lock

bypass Poetry

pip-install around Poetry

Poetry failures are signals, not noise.

7. Canonical Smoke Test

After every deploy:

curl -X POST https://<api-url>/v2/turn \
  -H "Content-Type: application/json" \
  -d '{"text":"test"}'


Valid:

200

422

Invalid:

404 → wrong app target

502 → crash on import

ModuleNotFoundError → build context / deps broken

8. Debugging Order (Never Skip Levels)

Build context (does container include /sakhi?)

Import path (sakhi.apps.api.main:app)

PYTHONPATH

Poetry virtualenv behavior

Missing transitive deps (e.g. openai)

Do not debug product logic before these pass.

9. Codex System Prompt — Infra Tasks (Authoritative)

Use this as the SYSTEM prompt for any Codex session touching infra.

You are operating under the Sakhi Infrastructure Canon.

Your job is to preserve deployment correctness, not to optimize or redesign.

Non-negotiable rules:
- The Dockerfile lives at repo root.
- The build context must include the full repo, including /sakhi.
- The FastAPI app is sakhi.apps.api.main:app.
- PYTHONPATH must include the repo root.
- Poetry virtualenvs must be disabled inside containers.
- poetry.lock must be kept in sync with pyproject.toml.
- Transitive runtime dependencies (e.g. openai) must be installed if imported at startup.

Forbidden actions:
- Moving the Dockerfile into subdirectories
- Using uvicorn main:app
- Bypassing Poetry with pip
- Installing deps ad-hoc in Docker
- Guessing import paths without filesystem verification

If a change risks violating these rules, stop and ask for clarification.

Infrastructure correctness overrides convenience.

10. Deploy Checklist — Railway (API) vs Vercel (Web)
Railway — API Service

Before Deploy

Dockerfile is at repo root

Build context = repo root

sakhi/ exists at root

poetry.lock is up to date

openai in runtime dependencies

Start Command

None (use Docker CMD)

After Deploy

Container stays up

/v2/turn responds (200 / 422)

No import errors in logs

Vercel — Web App

Environment Variables

NEXT_PUBLIC_API_BASE_URL → Railway API URL

No backend secrets exposed

Routing

/api/turn-v2 is a pure proxy

No rewriting of backend paths

After Deploy

Browser → /api/turn-v2 → Railway /v2/turn

No 404s, no CORS errors

11. Local Development (Production Parity)

Local parity rules
- Same Dockerfile, same entrypoint. No local-only code paths or alternate targets.
- Removing .env.local should fail loudly; do not add defaults in code.

.env.local (values only)
- Gitignored. Example at repo root: .env.local.example
  - DATABASE_URL=postgresql://user:pass@localhost:5432/sakhi
  - REDIS_URL=redis://localhost:6379/0
  - OPENAI_API_KEY=sk-...
  - NEXT_PUBLIC_API_BASE_URL=http://localhost:8080

Run the API locally (Docker only)
- Build the exact Railway image: docker build -t sakhi-api .
- Run it with your .env.local: docker run --env-file .env.local -p 8080:8080 sakhi-api
- This is the same image and command path Railway uses; if it fails locally, it will fail in prod.
- Never use uvicorn main:app or python main.py directly; the container is the source of truth.

Optional infra helper (no API)
- docker-compose.local.yml starts Postgres + Redis only. Bring it up with:
  - docker compose -f docker-compose.local.yml up -d
- The API still runs via docker run ... against the image built from the repo root Dockerfile.

Web app (Vercel parity)
- From repo root: pnpm --filter web dev (workspace target for the Vercel build).
- Switch API targets only through NEXT_PUBLIC_API_BASE_URL (local Docker: http://localhost:8080; Railway: deployed URL). No proxy rewrites or conditional logic.

Validation loop
- With the container running and env loaded: curl -X POST http://localhost:8080/v2/turn -H "Content-Type: application/json" -d '{"text":"test"}' → 200/422 is valid.
- No code may branch on “local” vs “prod”; parity issues are build/run problems, not product logic.

12. Change Policy

Any change to:

Dockerfile

repo layout

entrypoints

dependency boundaries

build contexts

must update this document.

This file is part of system stability.

Final Rule (Memorize This)

If everything looks right but nothing works,
assume build context or import path first — not product logic.
