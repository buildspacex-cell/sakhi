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

RUN python - <<'EOF'
import sys, os
print("PYTHONPATH:", os.environ.get("PYTHONPATH"))
print("sys.path:", sys.path)
try:
    import sakhi
    print("import sakhi: OK")
except Exception as e:
    print("import sakhi: FAIL", e)
EOF

CMD ["python", "-m", "uvicorn", "sakhi.apps.api.main:app", "--host", "0.0.0.0", "--port", "8080"]
