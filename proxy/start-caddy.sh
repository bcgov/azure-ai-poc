#!/usr/bin/env sh
# Retry wrapper for Caddy (Alpine-compatible, POSIX sh)

# Env vars you can override at runtime:
#   MAX_RETRIES      - total restart attempts (default: 30)
#   DELAY_SECONDS    - delay between attempts in seconds (default: 5)
#   CADDY_BIN        - caddy binary path/name (default: caddy)
#   CADDY_CONFIG     - path to Caddyfile (default: /etc/caddy/Caddyfile)
#   CADDY_EXTRA_ARGS - extra args to pass to "caddy run" (default: empty)

set -eu
set -o pipefail 2>/dev/null || true  # pipefail not available in all POSIX shells

MAX_RETRIES="${MAX_RETRIES:-30}"
DELAY_SECONDS="${DELAY_SECONDS:-5}"
CADDY_BIN="${CADDY_BIN:-caddy}"
CADDY_CONFIG="${CADDY_CONFIG:-/etc/caddy/Caddyfile}"
CADDY_EXTRA_ARGS="${CADDY_EXTRA_ARGS:-}"

ts() { date -u +"%Y-%m-%dT%H:%M:%SZ"; }

if ! command -v "$CADDY_BIN" >/dev/null 2>&1; then
  echo "$(ts) - ERROR: caddy binary not found at '$CADDY_BIN'"
  exit 127
fi

[ -f "$CADDY_CONFIG" ] || echo "$(ts) - WARN: Caddyfile not found at '$CADDY_CONFIG' (caddy will report if this is a problem)"

stop=0
status=1

on_term() {
  stop=1
  echo "$(ts) - Received termination signal; will stop after current attempt."
}
trap on_term INT TERM

attempt=1
while [ "$attempt" -le "$MAX_RETRIES" ] && [ "$stop" -eq 0 ]; do
  echo "$(ts) - Starting Caddy (attempt $attempt/$MAX_RETRIES)"
  # shellcheck disable=SC2086 - CADDY_EXTRA_ARGS intentionally word-split
  "$CADDY_BIN" run --config "$CADDY_CONFIG" --adapter caddyfile $CADDY_EXTRA_ARGS || true
  status=$?
  if [ "$status" -eq 0 ]; then
    echo "$(ts) - Caddy exited cleanly (code 0). Not retrying."
    exit 0
  fi

  echo "$(ts) - Caddy exited with code $status"
  attempt=$((attempt + 1))

  if [ "$attempt" -le "$MAX_RETRIES" ] && [ "$stop" -eq 0 ]; then
    echo "$(ts) - Retrying in ${DELAY_SECONDS}s..."
    i=0
    while [ "$i" -lt "$DELAY_SECONDS" ]; do
      [ "$stop" -ne 0 ] && break
      sleep 1
      i=$((i + 1))
    done
  fi
done

if [ "$stop" -ne 0 ]; then
  echo "$(ts) - Stopped by signal. Exiting with code $status."
else
  echo "$(ts) - Max retries ($MAX_RETRIES) reached. Exiting with code $status."
fi
exit "$status"