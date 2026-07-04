FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev gcc \
    && rm -rf /var/lib/apt/lists/*

COPY packages/ /tmp/packages/
RUN pip install --no-cache-dir \
    /tmp/packages/db/ \
    /tmp/packages/infra/ \
    /tmp/packages/retrieval/ \
    /tmp/packages/llm_gateway/ \
    /tmp/packages/agent_runtime/ \
    /tmp/packages/cost_analysis/ \
    /tmp/packages/observability/ \
    /tmp/packages/memory/ \
    /tmp/packages/evaluation/ \
    && rm -rf /tmp/packages

COPY backend/pyproject.toml ./
COPY backend/src/ src/
COPY backend/alembic/ alembic/
COPY backend/alembic.ini ./

RUN pip install --no-cache-dir .

RUN mkdir -p /app/uploads

EXPOSE 8000

# 1. Alembic: create/upgrade all tables
# 2. Bootstrap: seed default data
# 3. Uvicorn: start the API server
CMD ["sh", "-c", "PYTHONPATH=/app/src alembic upgrade head && PYTHONPATH=/app/src python -m bootstrap && uvicorn main:create_app --factory --host 0.0.0.0 --port 8000"]
