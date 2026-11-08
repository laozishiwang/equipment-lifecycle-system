#!/usr/bin/env bash
set -euo pipefail
# Run from the project directory; compose environment and backup destination are explicit.
project_dir=$(cd -- "$(dirname -- "$0")/.." && pwd)
cd "$project_dir"
compose_file=${COMPOSE_FILE:-compose.production.yaml}
env_file=${ENV_FILE:-.env.production}
backup_root=${BACKUP_ROOT:-/opt/equipment-backups}
project_name=${COMPOSE_PROJECT_NAME:-equipment}
umask 077
mkdir -p -- "$backup_root"
stamp=$(date -u +%Y%m%dT%H%M%SZ)
output="$backup_root/$stamp"
if ! mkdir -- "$output"; then echo 'Backup directory already exists' >&2; exit 1; fi
compose=(docker compose --project-name "$project_name" --env-file "$env_file" -f "$compose_file")
# Keep incomplete files separate; never report success if either archive fails.
"${compose[@]}" exec -T mysql sh -c 'exec mysqldump --single-transaction --quick --routines --triggers -uroot -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE"' 2>/dev/null | gzip -c > "$output/database.sql.gz.partial"
gzip -t "$output/database.sql.gz.partial"
mv -- "$output/database.sql.gz.partial" "$output/database.sql.gz"
"${compose[@]}" exec -T backend tar -C /app/uploads -czf - . > "$output/uploads.tar.gz.partial"
gzip -t "$output/uploads.tar.gz.partial"
tar -tzf "$output/uploads.tar.gz.partial" >/dev/null
mv -- "$output/uploads.tar.gz.partial" "$output/uploads.tar.gz"
"${compose[@]}" exec -T backend tar -C /app/private-uploads -czf - . > "$output/private-uploads.tar.gz.partial"
gzip -t "$output/private-uploads.tar.gz.partial"
tar -tzf "$output/private-uploads.tar.gz.partial" >/dev/null
mv -- "$output/private-uploads.tar.gz.partial" "$output/private-uploads.tar.gz"
(cd "$output" && sha256sum database.sql.gz uploads.tar.gz private-uploads.tar.gz > SHA256SUMS && sha256sum -c SHA256SUMS)
printf 'Backup created: %s\n' "$output"
