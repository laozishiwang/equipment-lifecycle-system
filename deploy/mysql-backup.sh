#!/usr/bin/env bash
set -euo pipefail
# Usage: MYSQL_CNF=/secure/client.cnf ./deploy/mysql-backup.sh [database] [directory]
cnf=${MYSQL_CNF:?Set MYSQL_CNF to a protected MySQL client option file}
database=${1:-equipment}
directory=${2:-./backups}
[[ $database =~ ^[A-Za-z0-9_]+$ ]] || { echo 'Invalid database name' >&2; exit 1; }
[[ -f $cnf ]] || { echo 'MySQL option file not found' >&2; exit 1; }
umask 077
mkdir -p -- "$directory"
output="$directory/${database}-$(date -u +%Y%m%dT%H%M%SZ).sql.gz"
[[ ! -e $output ]] || { echo 'Backup already exists' >&2; exit 1; }
tmp=$(mktemp "$directory/.mysql-backup.XXXXXXXX")
trap 'rm -f -- "$tmp"' EXIT
mysqldump --defaults-extra-file="$cnf" --single-transaction --quick --routines --triggers --set-gtid-purged=OFF "$database" | gzip -c > "$tmp"
gzip -t "$tmp"
mv -- "$tmp" "$output"
sha256sum "$output" > "$output.sha256"
printf 'Backup created: %s\n' "$output"
