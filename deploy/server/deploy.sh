#!/usr/bin/env bash
# Deploy one image tag on this host. Run by the release pipeline over SSH;
# safe to run by hand too.
#
#   ./deploy.sh <image-tag>      migrate, roll out, verify; roll back on failure
#   ./deploy.sh --rollback       go back to the previously deployed tag
#   ./deploy.sh --status         what is running
#
# Order, and why:
#   1. pull every image first, so a registry outage changes nothing
#   2. migrate (gate): a failed migration stops here with the old version
#      still serving. Migrations are expand-only (docs/runbooks/deploy.md),
#      so the old version keeps working against the migrated schema.
#   3. roll out api, scheduler, web
#   4. verify: /readyz inside, then the public health URL through TLS
#   5. on failure, put the previous tag back and exit non-zero
set -Eeuo pipefail
cd "$(dirname "$0")"

ENV_FILE="${ENV_FILE:-production.env}"
STATE_DIR="${STATE_DIR:-.deploy}"
# Docker Compose reads COMPOSE_FILE itself (colon-separated, later files override).
export COMPOSE_FILE="${COMPOSE_FILE:-docker-compose.yml}"
READY_TIMEOUT="${READY_TIMEOUT:-180}"
mkdir -p "$STATE_DIR"

[ -f "$ENV_FILE" ] || { echo "✗ $ENV_FILE is missing (copy production.env.example)" >&2; exit 2; }
: "${IMAGE_REPO:?set IMAGE_REPO, e.g. ghcr.io/acme}"

compose() { docker compose --env-file "$ENV_FILE" "$@"; }
log() { printf '%s %s\n' "$(date -u +%FT%TZ)" "$*" | tee -a "$STATE_DIR/history.log"; }
env_value() { grep -E "^$1=" "$ENV_FILE" | tail -1 | cut -d= -f2-; }

current_tag() { cat "$STATE_DIR/current" 2>/dev/null || true; }

wait_ready() {
  local deadline=$((SECONDS + READY_TIMEOUT)) public_url
  until IMAGE_TAG="$1" compose exec -T api python -c \
      "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/readyz', timeout=3).status == 200 else 1)" \
      >/dev/null 2>&1; do
    [ $SECONDS -lt $deadline ] || { echo "✗ /readyz did not pass within ${READY_TIMEOUT}s" >&2; return 1; }
    sleep 3
  done
  public_url="${PUBLIC_URL:-https://$(env_value DOMAIN)}"
  until curl -fsS --max-time 5 ${CURL_INSECURE:+-k} "$public_url/api/v1/health" 2>/dev/null | grep -q '"database_status":"ok"'; do
    [ $SECONDS -lt $deadline ] || { echo "✗ $public_url/api/v1/health did not pass within ${READY_TIMEOUT}s" >&2; return 1; }
    sleep 3
  done
}

roll_out() {
  IMAGE_TAG="$1" compose up -d --remove-orphans clamav api scheduler web edge
}

case "${1:-}" in
  --status)
    echo "current:  $(current_tag)"
    echo "previous: $(cat "$STATE_DIR/previous" 2>/dev/null || true)"
    IMAGE_TAG="$(current_tag)" compose ps
    exit 0 ;;
  --rollback)
    target="$(cat "$STATE_DIR/previous" 2>/dev/null || true)"
    [ -n "$target" ] || { echo "✗ no previous tag recorded" >&2; exit 2; }
    log "rollback $(current_tag) -> $target"
    roll_out "$target" && wait_ready "$target" || { log "✗ rollback to $target is unhealthy"; exit 1; }
    echo "$(current_tag)" > "$STATE_DIR/previous"; echo "$target" > "$STATE_DIR/current"
    log "rollback complete: $target"
    exit 0 ;;
  ""|-*)
    echo "usage: $0 <image-tag> | --rollback | --status" >&2; exit 2 ;;
esac

TAG="$1"
PREVIOUS="$(current_tag)"
log "deploy $TAG (was ${PREVIOUS:-none}) by ${DEPLOY_ACTOR:-$(whoami)}"

IMAGE_TAG="$TAG" compose --profile migrate pull --quiet migrate api scheduler web clamav edge

log "migrate (gate)"
if ! IMAGE_TAG="$TAG" compose --profile migrate run --rm -e DEPLOY_ACTOR="deploy:$TAG:${DEPLOY_ACTOR:-$(whoami)}" migrate; then
  log "✗ migration failed; nothing rolled out, ${PREVIOUS:-the old version} keeps serving"
  exit 1
fi

log "roll out"
# Either step failing means roll back: `up` itself fails when a container
# never turns healthy, so it can't be left to set -e.
if roll_out "$TAG" && wait_ready "$TAG"; then
  if [ -n "$PREVIOUS" ] && [ "$PREVIOUS" != "$TAG" ]; then echo "$PREVIOUS" > "$STATE_DIR/previous"; fi
  echo "$TAG" > "$STATE_DIR/current"
  docker image prune -f --filter "until=168h" >/dev/null 2>&1 || true
  log "✓ deployed $TAG"
  exit 0
fi

if [ -n "$PREVIOUS" ]; then
  log "✗ $TAG failed its checks; rolling back to $PREVIOUS"
  if roll_out "$PREVIOUS" && wait_ready "$PREVIOUS"; then
    log "rolled back to $PREVIOUS"
  else
    log "✗ rollback to $PREVIOUS is unhealthy too: page the on-call owner"
  fi
else
  log "✗ $TAG failed its checks and there is no previous version to return to"
fi
exit 1
