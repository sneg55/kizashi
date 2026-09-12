FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.9.7 /uv /usr/local/bin/uv

ENV UV_LINK_MODE=copy \
    UV_PROJECT_ENVIRONMENT=/app/.venv \
    PATH=/app/.venv/bin:$PATH \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-dev --no-install-project

COPY src ./src
COPY scripts ./scripts
COPY data/demo/portfolio-nj-086.csv ./data/demo/portfolio-nj-086.csv
COPY data/runs/backtest.json data/runs/silence.json ./data/runs/

RUN uv sync --frozen --no-dev && chmod +x scripts/scheduled-run.sh

ENTRYPOINT ["scripts/scheduled-run.sh"]
