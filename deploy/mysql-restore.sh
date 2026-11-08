#!/usr/bin/env bash
set -euo pipefail
# Usage: MYSQL_CNF=/secure/client.cnf ./deploy/mysql-restore.sh backup.sql.gz target_database
cnf=${MYSQL_CNF:?Set MYSQL_CNF to a protected MySQL client option file}
backup=${1:?Specify a .sql.gz backup}
database=${2:?Specify the target database explicitly}
[[ $database =~ ^[A-Za-z0-9_]+$ ]] || { echo 'Invalid database name' >&2; exit 1; }
[[ -f $cnf && -f $backup ]] || { echo 'Option file or backup not found' >&2; exit 1; }
gzip -t "$backup"
printf 'This imports into database %s and may overwrite its data. Type the database name to continue: ' "$database" >&2
read -r confirmation
[[ $confirmation == "$database" ]] || { echo 'Cancelled' >&2; exit 1; }
gzip -dc -- "$backup" | mysql --defaults-extra-file="$cnf" "$database"
echo 'Import completed.'
