#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

if ! command -v docker >/dev/null 2>&1; then
  echo "Docker is not installed or is not on PATH. Install Docker Engine with the Compose plugin first." >&2
  exit 1
fi

if [[ ! -f .env ]]; then
  cp .env.example .env
  echo "Created .env from .env.example (local development defaults)."
fi

# Ensure the admin console has a separate, unpredictable local access key.
ADMIN_CURRENT="$(grep -E '^ADMIN_KEY=' .env | tail -n 1 | cut -d= -f2- || true)"
if [[ -z "${ADMIN_CURRENT}" || "${ADMIN_CURRENT}" == "demo-admin-change-me" ]]; then
  ADMIN_GENERATED="$(od -An -N32 -tx1 /dev/urandom | tr -d ' \n')"
  if grep -q '^ADMIN_KEY=' .env; then
    sed -i "s/^ADMIN_KEY=.*/ADMIN_KEY=${ADMIN_GENERATED}/" .env
  else
    printf '\nADMIN_KEY=%s\n' "${ADMIN_GENERATED}" >> .env
  fi
  echo "Generated a private ADMIN_KEY in .env. Retrieve it locally with: grep '^ADMIN_KEY=' .env"
fi

# Prefer rootless/current-user Docker access; use sudo when the user lacks socket permissions.
if docker info >/dev/null 2>&1; then
  DOCKER=(docker)
else
  echo "Docker requires elevated permissions on this machine; sudo may ask for your password."
  DOCKER=(sudo docker)
  "${DOCKER[@]}" info >/dev/null
fi

"${DOCKER[@]}" compose config -q
"${DOCKER[@]}" compose up --build -d

WEB_PORT="$(awk -F= '$1 == "WEB_PORT" {gsub(/\r/, "", $2); print $2; exit}' .env)"
API_PORT="$(awk -F= '$1 == "API_PORT" {gsub(/\r/, "", $2); print $2; exit}' .env)"
WEB_PORT="${WEB_PORT:-3100}"
API_PORT="${API_PORT:-8101}"

printf '\nWaiting for the frontend and API health check'
for _ in $(seq 1 60); do
  if command -v curl >/dev/null 2>&1 \
    && curl -fsS "http://127.0.0.1:${WEB_PORT}/" >/dev/null 2>&1 \
    && curl -fsS "http://127.0.0.1:${API_PORT}/api/health" >/dev/null 2>&1; then
    printf '\n\nJomiProman is responding.\n'
    printf 'Website:      http://localhost:%s\n' "$WEB_PORT"
    printf 'API docs:     http://localhost:%s/api/docs\n' "$API_PORT"
    printf 'Health check: http://localhost:%s/api/health\n' "$API_PORT"
    printf 'Admin panel:  http://localhost:%s/admin (use ADMIN_KEY from .env)\n' "$WEB_PORT"
    "${DOCKER[@]}" compose ps
    exit 0
  fi
  printf '.'
  sleep 2
done
printf '\nServices did not become ready within 120 seconds. Current status and recent logs:\n' >&2
"${DOCKER[@]}" compose ps >&2
"${DOCKER[@]}" compose logs --tail=60 backend frontend >&2
exit 1
