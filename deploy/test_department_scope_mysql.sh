#!/usr/bin/env bash
set -euo pipefail
cd /opt/equipment-rebuild
net="scope-test-$RANDOM-$RANDOM"
mysql="scope-mysql-test"
if docker container inspect "$mysql" >/dev/null 2>&1; then echo 'test container name already in use' >&2; exit 1; fi
created=0
cleanup() { if [ "$created" = 1 ]; then docker rm -f "$mysql" >/dev/null 2>&1 || true; fi; docker network rm "$net" >/dev/null 2>&1 || true; }
trap cleanup EXIT
docker network create --internal "$net" >/dev/null
docker run -d --name "$mysql" --network "$net" -e MYSQL_ROOT_PASSWORD=isolated-test-only -e MYSQL_DATABASE=scope_mysql_test --tmpfs /var/lib/mysql mysql:8.0 >/dev/null
created=1
ready=0
for _ in $(seq 1 60); do
 if docker exec "$mysql" mysqladmin ping -h 127.0.0.1 -uroot -pisolated-test-only --silent >/dev/null 2>&1; then ready=1; break; fi
 sleep 1
done
[ "$ready" = 1 ] || { echo 'disposable mysql failed to start' >&2; exit 1; }
docker run --rm --network "$net" -v "$PWD:/work:ro" -w /work maven:3.9-eclipse-temurin-17 sh -c 'mkdir -p /tmp/boot /tmp/classes && cd /tmp/boot && jar xf /work/backend/ruoyi-admin/target/ruoyi-admin.jar && cd /work && javac -cp "/tmp/boot/BOOT-INF/lib/*:/tmp/boot/BOOT-INF/classes" -d /tmp/classes backend/ruoyi-admin/src/main/java/com/ruoyi/web/controller/equipment/DepartmentScopeResolver.java backend/ruoyi-admin/src/main/java/com/ruoyi/web/controller/equipment/DepartmentScopeDatabaseService.java backend/ruoyi-admin/src/main/java/com/ruoyi/web/controller/equipment/DepartmentScopeAccess.java backend/ruoyi-admin/src/main/java/com/ruoyi/web/controller/equipment/DepartmentScopeSql.java deploy/DepartmentScopeDatabaseMysqlTest.java deploy/DepartmentScopeSqlTest.java && java -cp "/tmp/classes:/tmp/boot/BOOT-INF/lib/*:/tmp/boot/BOOT-INF/classes" com.ruoyi.web.controller.equipment.DepartmentScopeDatabaseMysqlTest isolated-test-only && java -cp "/tmp/classes:/tmp/boot/BOOT-INF/lib/*:/tmp/boot/BOOT-INF/classes" DepartmentScopeSqlTest'
