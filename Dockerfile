FROM python:3.12-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PLAYWRIGHT_BROWSERS_PATH=/ms-playwright \
    DATABASE_URL=sqlite:////data/afran.db \
    DATABASE_AUTO_CREATE=false \
    WEB_CONCURRENCY=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt \
    && python -m playwright install --with-deps chromium \
    && apt-get update \
    && apt-get install -y --no-install-recommends libcap2-bin \
    && setcap 'cap_net_bind_service=+ep' "$(readlink -f "$(command -v python)")" \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd --system afran \
    && useradd --system --gid afran --home-dir /app afran \
    && mkdir -p /data /ms-playwright \
    && chown -R afran:afran /app /data /ms-playwright

COPY --chown=afran:afran app ./app
COPY --chown=afran:afran migrations ./migrations
COPY --chown=afran:afran alembic.ini ./alembic.ini
COPY --chown=afran:afran scripts ./scripts

USER afran

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s --start-period=60s --retries=3 \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:80/health', timeout=4)" || exit 1

CMD ["sh", "scripts/start.sh"]
