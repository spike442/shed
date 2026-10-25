# syntax=docker/dockerfile:1
FROM node:22-alpine@sha256:0a7108bf6c7bf5de370ffb1a3ed6be93d405b43ff159f681a8d18c0e2bc2e402 AS ui
WORKDIR /ui
COPY shed/shed/ui/package.json shed/shed/ui/package-lock.json ./
RUN npm ci
COPY shed/shed/ui ./
RUN npm run build

FROM ghcr.io/astral-sh/uv:0.12.20@sha256:100047e74f30778ab704942321a09750d6158739573ff58bf3924085cc6cd2d8 AS uv
FROM python:3.12-slim@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1 AS build
WORKDIR /app
ENV UV_PYTHON_DOWNLOADS=0
COPY shed/pyproject.toml shed/uv.lock ./
COPY shed/core ./core
COPY shed/knowledge/client ./knowledge/client
COPY shed/sentinel/core ./sentinel/core
COPY shed/shed/api/pyproject.toml ./shed/api/pyproject.toml
COPY shed/shed/api/src ./shed/api/src
ARG VERSION
RUN if [ -n "$VERSION" ]; then find . -name pyproject.toml -exec sed -i "s/^version = \"[^\"]*\"$/version = \"${VERSION}\"/" {} +; fi
RUN --mount=from=uv,source=/uv,target=/bin/uv UV_CACHE_DIR=/tmp/uv-cache uv sync --frozen --no-dev --package shed-api --no-editable

FROM python:3.12-slim@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1
WORKDIR /app
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH=/app/.venv/bin:$PATH
RUN apt-get update && apt-get install -y --no-install-recommends ca-certificates passwd \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --uid 65532 --create-home --shell /usr/sbin/nologin shed
COPY --from=build /app/.venv /app/.venv
COPY --from=ui /ui/dist /app/ui
EXPOSE 8070
USER 65532:65532
CMD ["uvicorn", "shed.api.server:app", "--host", "0.0.0.0", "--port", "8070"]
