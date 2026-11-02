# syntax=docker/dockerfile:1.7
# RecruitOps API. Build from the repo root:
#   docker build -f backend/Dockerfile -t recruitops-api .
#   docker build -f backend/Dockerfile --target ops -t recruitops-ops .
# The runtime image runs the API (default) and migrations (scripts/migrate.py).
# The ops image adds sqlpackage and runs the scheduler, backups and restore
# drills (scripts/scheduler.py, backup_db.py, restore_drill.py).

FROM python:3.12-slim-bookworm AS base
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    VIRTUAL_ENV=/opt/venv \
    PATH=/opt/venv/bin:$PATH

# Optional build-only CA (corporate TLS-inspecting proxies):
#   docker build --secret id=build_ca,src=/path/to/proxy-ca.pem ...
# It is trusted during these RUN steps only and never written into the image.
# Microsoft ODBC Driver 18 for SQL Server (pyodbc talks to SQL Server / Azure SQL through it).
RUN --mount=type=secret,id=build_ca,required=false set -eux; \
    if [ -s /run/secrets/build_ca ]; then \
      cat /etc/ssl/certs/ca-certificates.crt /run/secrets/build_ca > /tmp/build-ca.pem; \
      export CURL_CA_BUNDLE=/tmp/build-ca.pem; \
      echo 'Acquire::https::CAInfo "/tmp/build-ca.pem";' > /etc/apt/apt.conf.d/99build-ca; \
    fi; \
    apt-get update; \
    apt-get upgrade -y --no-install-recommends; \
    apt-get install -y --no-install-recommends ca-certificates curl gnupg unixodbc; \
    curl -fsSL https://packages.microsoft.com/keys/microsoft.asc | gpg --dearmor -o /usr/share/keyrings/microsoft-prod.gpg; \
    echo "deb [arch=amd64,arm64 signed-by=/usr/share/keyrings/microsoft-prod.gpg] https://packages.microsoft.com/debian/12/prod bookworm main" \
      > /etc/apt/sources.list.d/mssql-release.list; \
    apt-get update; \
    ACCEPT_EULA=Y apt-get install -y --no-install-recommends msodbcsql18; \
    apt-get purge -y --auto-remove curl gnupg; \
    rm -rf /var/lib/apt/lists/* /tmp/build-ca.pem /etc/apt/apt.conf.d/99build-ca

FROM base AS deps
COPY backend/requirements.txt /tmp/requirements.txt
RUN --mount=type=secret,id=build_ca,required=false set -eu; \
    if [ -s /run/secrets/build_ca ]; then \
      cat /etc/ssl/certs/ca-certificates.crt /run/secrets/build_ca > /tmp/build-ca.pem; \
      export PIP_CERT=/tmp/build-ca.pem; \
    fi; \
    python -m venv "$VIRTUAL_ENV" && pip install -r /tmp/requirements.txt; \
    rm -f /tmp/build-ca.pem

FROM base AS runtime
ARG APP_VERSION=dev
ARG GIT_SHA=unknown
LABEL org.opencontainers.image.title="recruitops-api" \
      org.opencontainers.image.version="$APP_VERSION" \
      org.opencontainers.image.revision="$GIT_SHA"
ENV APP_VERSION=$APP_VERSION \
    GIT_SHA=$GIT_SHA \
    APP_ENV=production \
    LOG_FORMAT=json \
    WEB_CONCURRENCY=2 \
    PORT=8000 \
    PROMETHEUS_MULTIPROC_DIR=/tmp/recruitops/metrics

RUN groupadd --system --gid 10001 app && useradd --system --uid 10001 --gid app --home-dir /app --shell /usr/sbin/nologin app
COPY --from=deps /opt/venv /opt/venv
WORKDIR /app/backend
COPY --chown=root:root backend/app ./app
COPY --chown=root:root backend/db ./db
COPY --chown=root:root backend/scripts ./scripts
COPY --chown=root:root backend/docker ./docker
# Numbered migrations live at the repo root (scripts/NNN_*.sql).
COPY --chown=root:root scripts/*.sql /app/scripts/
# Code is readable but not writable by the app user, whatever the permissions
# were in the build context; only uploads/ (local dev storage) and /tmp are writable.
RUN chmod -R a+rX,go-w /app && chmod 0555 docker/*.sh \
    && mkdir -p /app/backend/uploads /tmp/recruitops && chown app:app /app/backend/uploads /tmp/recruitops

USER app
EXPOSE 8000
HEALTHCHECK --interval=15s --timeout=3s --start-period=20s --retries=3 \
  CMD python -c "import os,urllib.request,sys; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\",\"8000\")}/livez', timeout=2); sys.exit(0)" || exit 1
ENTRYPOINT ["/app/backend/docker/entrypoint.sh"]
CMD ["api"]

# ---- ops: runtime + sqlpackage (portable .bacpac export/import) --------------
FROM runtime AS ops
ARG SQLPACKAGE_URL=https://aka.ms/sqlpackage-linux
USER root
RUN --mount=type=secret,id=build_ca,required=false set -eux; \
    if [ -s /run/secrets/build_ca ]; then \
      cat /etc/ssl/certs/ca-certificates.crt /run/secrets/build_ca > /tmp/build-ca.pem; \
      export CURL_CA_BUNDLE=/tmp/build-ca.pem; \
    fi; \
    apt-get update; \
    apt-get install -y --no-install-recommends curl unzip libicu72; \
    curl -fsSL -o /tmp/sqlpackage.zip "$SQLPACKAGE_URL"; \
    mkdir -p /opt/sqlpackage; unzip -q /tmp/sqlpackage.zip -d /opt/sqlpackage; chmod +x /opt/sqlpackage/sqlpackage; \
    ln -s /opt/sqlpackage/sqlpackage /usr/local/bin/sqlpackage; \
    apt-get purge -y --auto-remove curl unzip; \
    rm -rf /var/lib/apt/lists/* /tmp/sqlpackage.zip /tmp/build-ca.pem; \
    DOTNET_CLI_TELEMETRY_OPTOUT=1 sqlpackage /version
ENV DOTNET_CLI_TELEMETRY_OPTOUT=1 \
    DOTNET_SYSTEM_GLOBALIZATION_INVARIANT=0 \
    HOME=/tmp
USER app
CMD ["scheduler"]

