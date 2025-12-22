FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml poetry.lock* ./
ENV POETRY_VIRTUALENVS_CREATE=false
RUN python -m pip install --no-cache-dir poetry==1.8.3 \
 && poetry install --no-ansi --without dev

COPY . .

ENV PYTHONPATH=/app

RUN echo "=== /app directory ===" \
 && ls -la /app \
 && echo "=== /app depth-2 ===" \
 && find /app -maxdepth 2 -type d \
 && echo "=== /app depth-3 ===" \
 && find /app -maxdepth 3 -type d

RUN python - <<'EOF'\nimport sys, os\nprint(\"PYTHONPATH:\", os.environ.get(\"PYTHONPATH\"))\nprint(\"sys.path:\", sys.path)\ntry:\n    import sakhi\n    print(\"import sakhi: OK\")\nexcept Exception as e:\n    print(\"import sakhi: FAIL\", e)\nEOF

CMD ["python", "-m", "uvicorn", "sakhi.apps.api.main:app", "--host", "0.0.0.0", "--port", "8080"]
