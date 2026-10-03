# Stage 1: build the UI bundle
FROM node:24-slim AS ui
WORKDIR /app/ui
RUN corepack enable && corepack prepare pnpm@9.12.0 --activate
COPY ui/package.json ui/pnpm-lock.yaml ./
RUN pnpm install --frozen-lockfile
COPY ui/ ./
RUN pnpm exec vite build --outDir /app/static --emptyOutDir

# Stage 2: build the wheel with the UI inside, and the locked requirements
FROM python:3.12-slim AS build
WORKDIR /app
RUN pip install --no-cache-dir uv==0.12.21
COPY pyproject.toml uv.lock README.md LICENSE ./
COPY src ./src
COPY --from=ui /app/static ./src/flight_recorder/static
RUN uv build --wheel --out-dir /dist \
 && uv export --frozen --no-dev --no-emit-project --no-hashes -o /dist/requirements.txt

# Stage 3: runtime
FROM python:3.12-slim
COPY --from=build /dist /tmp/dist
RUN pip install --no-cache-dir -r /tmp/dist/requirements.txt \
 && pip install --no-cache-dir --no-deps /tmp/dist/*.whl \
 && rm -rf /tmp/dist \
 && useradd --create-home app
USER app
WORKDIR /home/app
EXPOSE 5320
HEALTHCHECK --interval=10s --timeout=3s --retries=5 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:5320/api/health')"
# 0.0.0.0 inside the container only; compose publishes it on the host loopback (ADR 0007)
CMD ["flight-recorder", "demo", "--dir", "/home/app/demo", "--port", "5320", "--host", "0.0.0.0", "--i-know-this-is-unauthenticated", "--no-browser"]
