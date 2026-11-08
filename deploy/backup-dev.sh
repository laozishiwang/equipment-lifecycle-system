#!/usr/bin/env bash
set -euo pipefail
# Run only against the named isolated development database container.
container=equipment-rebuild-mysql-1
backup_dir=${1:-/opt/equipment-rebuild/backups}
umask 077
mkdir -p -- "$backup_dir"
backup="$backup_dir/equipment-dev-$(date -u +%Y%m%dT%H%M%SZ).sql.gz"
temp="$backup.partial"
trap 'rm -f -- "$temp"' EXIT
docker exec "$container" sh -c 'exec mysqldump --single-transaction --quick --routines --triggers -uroot -p"$MYSQL_ROOT_PASSWORD" equipment_dev' 2>/dev/null | gzip -c > "$temp"
gzip -t "$temp"
mv -- "$temp" "$backup"
sha256sum "$backup" > "$backup.sha256"
printf 'Backup created: %s\n' "$backup"
