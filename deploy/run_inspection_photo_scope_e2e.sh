#!/usr/bin/env bash
# Experimental test only; the equipment-rebuild Compose project and loopback port
# must point to the isolated development database, never to production.
set -euo pipefail
cd /opt/equipment-rebuild
[ "${EMS_ISOLATED_FIXTURE:-}" = YES ] || { echo 'Refusing non-isolated execution' >&2; exit 1; }
: "${EMS_PHOTO_A_USER:?}" "${EMS_PHOTO_A_PASSWORD:?}" "${EMS_PHOTO_B_USER:?}" "${EMS_PHOTO_B_PASSWORD:?}"
: "${EMS_PHOTO_A_DEVICE:?}" "${EMS_PHOTO_B_DEVICE:?}" "${EMS_PHOTO_A_INSPECTION:?}" "${EMS_PHOTO_A_USER_ID:?}"
override=$(mktemp /tmp/equipment-photo-scope.XXXXXX)
restore() {
  local original=$?
  trap - EXIT
  if ! docker compose -p equipment-rebuild -f compose.dev.yaml up -d --no-deps --force-recreate backend; then
    echo 'ERROR: failed to restore default isolated backend configuration' >&2
    rm -f -- "$override"
    exit 1
  fi
  rm -f -- "$override"
  exit "$original"
}
trap restore EXIT
cat > "$override" <<'YAML'
services:
  backend:
    environment:
      EQUIPMENT_DEPARTMENT_SCOPE_ENABLED: 'true'
      EQUIPMENT_DEPARTMENT_SCOPE_EXPERIMENTAL: 'true'
YAML
docker compose -p equipment-rebuild -f compose.dev.yaml -f "$override" up -d --no-deps --force-recreate backend
ready=0
for _ in $(seq 1 90); do
  if curl -fsS http://127.0.0.1:18090/prod-api/captchaImage 2>/dev/null | grep -q '"code":200'; then ready=1; break; fi
  sleep 2
done
[ "$ready" = 1 ] || { echo 'Isolated backend did not become ready' >&2; exit 1; }
python3 deploy/inspection_photo_scope_e2e.py
