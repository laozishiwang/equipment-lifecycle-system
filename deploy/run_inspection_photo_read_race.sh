#!/usr/bin/env bash
# Disposable inspection-scope fixture only; never use production or shared dev.
set -euo pipefail
cd /opt/equipment-rebuild
[ "${EMS_ISOLATED_FIXTURE:-}" = YES ] || { echo 'Refusing non-isolated execution' >&2; exit 1; }
p=inspection-scope-20261105
[ -z "$(docker ps -aq --filter label=com.docker.compose.project=$p)" ] || { echo 'Test project already in use' >&2; exit 1; }
[ -d /tmp/inspection-scope-20261105/mysql ] && [ -f /tmp/inspection-scope-build/ruoyi-admin/target/ruoyi-admin.jar ] || { echo 'Missing dedicated test fixtures' >&2; exit 1; }
cleanup() {
 local result=$?
 trap - EXIT
 if ! docker compose -p "$p" -f compose.inspection-scope-test.yaml down >/dev/null 2>&1; then echo 'Test cleanup failed' >&2; exit 1; fi
 exit "$result"
}
trap cleanup EXIT
# Create a new unique file exclusively; preserve it with the disposable fixture.
name=$(python3 -c 'import base64,pathlib,uuid; n=str(uuid.uuid4())+".png"; p=pathlib.Path("/tmp/inspection-scope-20261105/private")/n; f=p.open("xb"); f.write(base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+/6x0AAAAASUVORK5CYII=")); f.close(); print(n)')
docker compose -p "$p" -f compose.inspection-scope-test.yaml up -d >/dev/null
ready=0
for _ in $(seq 1 90); do
 if curl -fsS http://127.0.0.1:22091/prod-api/captchaImage 2>/dev/null | grep -q '"code":200'; then ready=1; break; fi
 sleep 2
done
[ "$ready" = 1 ] || { echo 'Test backend not ready' >&2; exit 1; }
printf "%s\n" "UPDATE sys_role SET status='0' WHERE role_id=99001; INSERT IGNORE INTO sys_role_menu SELECT 99001,menu_id FROM sys_menu WHERE perms='equipment:inspection:list'; UPDATE ems_equipment_department SET dept_id=99001 WHERE equipment_id=99001; UPDATE ems_inspection SET equipment_id=99001,inspector_id=1 WHERE id=99001; INSERT INTO ems_inspection_photo(id,inspection_id,stored_name,media_type,file_size,uploaded_by) VALUES (99001,99001,'$name','image/png',68,1) ON DUPLICATE KEY UPDATE inspection_id=99001,stored_name=VALUES(stored_name),media_type='image/png';" | docker exec -i "$p-mysql-1" sh -c 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" scope_test_race 2>/dev/null'
EMS_ISOLATED_FIXTURE=YES PYTHONPATH=/tmp/scope-race-20261105/python python3 deploy/inspection_photo_read_race.py
