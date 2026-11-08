#!/usr/bin/env bash
set -uo pipefail
project_dir=$(cd -- "$(dirname -- "$0")/.." && pwd)
cd "$project_dir"
project=${AUDIT_PROJECT:-equipment-live}
compose_file=${AUDIT_COMPOSE_FILE:-compose.production.yaml}
env_file=${AUDIT_ENV_FILE:-.env.production}
warning_percent=${AUDIT_WARNING_PERCENT:-85}
report=$(python3 deploy/photo_storage_audit.py --project "$project" --compose-file "$compose_file" --env-file "$env_file" --warning-percent "$warning_percent" 2>&1)
status=$?
case "$status" in
  0) priority=user.info ;;
  1) priority=user.warning ;;
  *) priority=user.err ;;
esac
logger -p "$priority" -t equipment-photo-audit -- "project=$project exit=$status $report" || exit 2
exit "$status"
