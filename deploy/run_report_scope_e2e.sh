#!/usr/bin/env bash
set -euo pipefail
cd /opt/equipment-rebuild
[ "${EMS_ISOLATED_FIXTURE:-}" = YES ] || { echo 'isolated confirmation required' >&2; exit 1; }
p=scope-race-20261105
[ -z "$(docker ps -aq --filter "label=com.docker.compose.project=$p")" ] || { echo 'test project is already active' >&2; exit 1; }
[ -d /tmp/scope-race-20261105/mysql ] || { echo 'missing isolated fixture database' >&2; exit 1; }
cleanup() { docker compose -p "$p" -f compose.scope-race.yaml down >/dev/null 2>&1 || true; }
trap cleanup EXIT
docker compose -p "$p" -f compose.scope-race.yaml up -d
ready=0
for _ in $(seq 1 90); do
 if curl -fsS http://127.0.0.1:22090/prod-api/captchaImage 2>/dev/null | grep -q '"code":200'; then ready=1; break; fi
 sleep 2
done
[ "$ready" = 1 ] || { echo 'test backend not ready' >&2; exit 1; }
EMS_ISOLATED_FIXTURE=YES python3 deploy/report_scope_e2e.py
