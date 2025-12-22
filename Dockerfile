FROM python:3.11-slim

WORKDIR /app

COPY pyproject.toml poetry.lock* ./
RUN python -m pip install --no-cache-dir poetry==1.8.3 \
 && poetry install --no-ansi --without dev

COPY . .

ENV PYTHONPATH=/app

CMD ["uvicorn", "sakhi.apps.api.main:app", "--host", "0.0.0.0", "--port", "8080"]
