
FROM python:3.13.7-slim-bookworm

COPY --from=ghcr.io/astral-sh/uv:0.12.5 /uv /uvx /bin/

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    CC=/usr/bin/gcc \
    CXX=/usr/bin/g++

# Install compiler and runtime dependencies.
RUN apt-get update \
    && apt-get install --no-install-recommends -y \
        build-essential \
        ca-certificates \
        gcc \
        g++ \
    && gcc --version \
    && g++ --version \
    && rm -rf /var/lib/apt/lists/*

COPY pyproject.toml uv.lock ./

RUN uv sync --frozen --no-dev --no-install-project

COPY data/processed/articles.json ./data/processed/articles.json
COPY src ./src
COPY main.py ./main.py
COPY docker/index_if_changed.py ./docker/index_if_changed.py

EXPOSE 4000

VOLUME ["/var/lib/index-state"]

CMD ["uv", "run", "--no-sync", "uvicorn", "main:app", "--host", "0.0.0.0", "--port", "4000"]
