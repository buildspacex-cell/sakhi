FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    POETRY_VIRTUALENVS_CREATE=false \
    POETRY_NO_INTERACTION=1

WORKDIR /app

# System deps (minimal)
RUN apt-get update && apt-get install -y --no-install-recommends build-essential curl \
  && rm -rf /var/lib/apt/lists/*

# Install Python deps via poetry (no venv)
COPY pyproject.toml poetry.lock* ./
RUN python -m pip install --no-cache-dir "poetry==1.8.3" \
  && poetry install --no-ansi --without dev

# Copy full code (monorepo)
COPY . .

# Expose API port
EXPOSE 8080

# Start FastAPI
CMD ["uvicorn", "sakhi.apps.api.main:app", "--host", "0.0.0.0", "--port", "8080"]
