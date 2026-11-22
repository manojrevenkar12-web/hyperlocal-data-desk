# The desk's command line, for n8n and cron. The web app is a static build served from S3 or any web server.
FROM python:3.12-slim
COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /usr/local/bin/uv
WORKDIR /app
COPY pyproject.toml uv.lock README.md ./
COPY src ./src
RUN uv sync --frozen --no-dev
COPY config ./config
COPY geo ./geo
COPY data/register.json ./data/register.json
ENV PATH="/app/.venv/bin:$PATH"
ENTRYPOINT ["desk"]
