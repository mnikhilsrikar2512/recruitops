# syntax=docker/dockerfile:1.7
# RecruitOps web tier: static pages + /api reverse proxy. Build from the repo root:
#   docker build -f frontend/Dockerfile -t recruitops-web .
# The compiled CSS, fonts and asset versions are committed (CI's "built
# assets are up to date" gate), so the image only copies them.
FROM nginxinc/nginx-unprivileged:1.27-alpine
ARG APP_VERSION=dev
ARG GIT_SHA=unknown
LABEL org.opencontainers.image.title="recruitops-web" \
      org.opencontainers.image.version="$APP_VERSION" \
      org.opencontainers.image.revision="$GIT_SHA"
ENV API_UPSTREAM=api:8000 \
    NGINX_ENVSUBST_FILTER=^API_UPSTREAM$
USER root
RUN rm -f /etc/nginx/conf.d/default.conf && mkdir -p /etc/nginx/snippets
COPY deploy/nginx/security-headers.conf /etc/nginx/snippets/security-headers.conf
COPY deploy/nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY frontend/index.html /usr/share/nginx/html/index.html
COPY frontend/pages /usr/share/nginx/html/pages
COPY frontend/shared /usr/share/nginx/html/shared
RUN chown -R root:root /usr/share/nginx/html /etc/nginx/snippets /etc/nginx/templates \
    && chmod -R a+rX,go-w /usr/share/nginx/html /etc/nginx/snippets /etc/nginx/templates \
    && find /usr/share/nginx/html -type f -exec chmod 0444 {} + \
    && rm -f /usr/share/nginx/html/shared/tailwind.input.css /usr/share/nginx/html/shared/tailwind.config.js
USER 101
EXPOSE 8080
HEALTHCHECK --interval=15s --timeout=3s --retries=3 CMD wget -qO- http://127.0.0.1:8080/healthz >/dev/null || exit 1
