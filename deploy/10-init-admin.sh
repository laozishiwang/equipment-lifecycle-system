#!/bin/sh
# MySQL image runs this only when creating a new data directory.
# A subshell keeps shell options from leaking into the sourced MySQL entrypoint.
(
set -eu
: "${ADMIN_BCRYPT_BASE64:?ADMIN_BCRYPT_BASE64 is required}"
admin_hash=$(printf '%s' "$ADMIN_BCRYPT_BASE64" | base64 -d)
printf '%s' "$admin_hash" | grep -Eq '^\$2[aby]\$(1[2-5])\$[./A-Za-z0-9]{53}$' || { echo 'Invalid administrator bcrypt hash' >&2; exit 1; }
[ "$admin_hash" != '$2a$10$7JB720yubVSZvUI0rEqK/.VqGOZTH.ulu33dHOiBE8ByOhJIrdAu2' ] || { echo 'Default administrator password hash is forbidden' >&2; exit 1; }
mysql --protocol=socket -uroot -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE" <<SQL
UPDATE sys_user SET password='$admin_hash', pwd_update_date=NOW() WHERE user_id=1 AND user_name='admin';
UPDATE sys_user SET status='1' WHERE user_name='ry' AND user_id=2;
SQL
)
