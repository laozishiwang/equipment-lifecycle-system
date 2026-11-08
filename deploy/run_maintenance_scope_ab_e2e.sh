#!/usr/bin/env bash
set -euo pipefail
cd /opt/equipment-rebuild
[ "${EMS_ISOLATED_FIXTURE:-}" = YES ] || { echo 'Refusing without explicit isolated fixture confirmation' >&2; exit 1; }
project=maint-scope-20261106
[ -z "$(docker ps -aq --filter "label=com.docker.compose.project=$project")" ] || { echo 'Existing project containers; refusing' >&2; exit 1; }
[ -f /tmp/scope-matrix-build/ruoyi-admin/target/ruoyi-admin.jar ] || { echo 'Missing separately built test JAR' >&2; exit 1; }
if ss -ltn | awk '{print $4}' | grep -Eq ':(22192|23492)$'; then echo 'Test port already in use' >&2; exit 1; fi
work=$(mktemp -d /tmp/equipment-history-e2e.XXXXXX)
mkdir "$work/mysql" "$work/uploads" "$work/private"
chmod 777 "$work/mysql" "$work/uploads" "$work/private"
cat > "$work/isolate.yaml" <<YAML
services:
  mysql:
    volumes:
      - $work/mysql:/var/lib/mysql
  backend:
    volumes:
      - /tmp/scope-matrix-build/ruoyi-admin/target/ruoyi-admin.jar:/app/app.jar:ro
      - $work/uploads:/app/uploads
      - $work/private:/app/private-uploads
YAML
cat > "$work/disabled.yaml" <<'YAML'
services:
  backend:
    environment:
      EQUIPMENT_DEPARTMENT_SCOPE_ENABLED: 'false'
      EQUIPMENT_DEPARTMENT_SCOPE_EXPERIMENTAL: 'false'
YAML
base=(docker compose -p "$project" -f compose.maintenance-scope-test.yaml -f "$work/isolate.yaml")
cleanup() { local result=$?; trap - EXIT; "${base[@]}" down >/dev/null 2>&1 || { echo 'Temporary containers could not be removed' >&2; exit 1; }; echo "Isolated test data retained: $work"; exit "$result"; }
trap cleanup EXIT
"${base[@]}" up -d mysql redis >/dev/null
ready=0
for _ in $(seq 1 90); do
  if docker exec "$project-mysql-1" sh -c 'mysqladmin ping -h 127.0.0.1 -uroot -p"$MYSQL_ROOT_PASSWORD" --silent' >/dev/null 2>&1; then ready=1; break; fi
  sleep 2
done
[ "$ready" = 1 ] || { echo 'Isolated database not ready' >&2; exit 1; }
docker exec -i "$project-mysql-1" sh -c 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" scope_test_race 2>/dev/null' < deploy/scope_race_fixture.sql
"${base[@]}" up -d --no-deps backend frontend >/dev/null
wait_ready() { for _ in $(seq 1 90); do if curl -fsS http://127.0.0.1:22192/prod-api/captchaImage 2>/dev/null | grep -q '"code":200'; then return 0; fi; sleep 2; done; echo 'Isolated API not ready' >&2; return 1; }
wait_ready
python3 deploy/maintenance_scope_ab_e2e.py
