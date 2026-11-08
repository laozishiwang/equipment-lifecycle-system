#!/usr/bin/env bash
set -euo pipefail
cd /opt/equipment-rebuild
net="photo-read-test-$RANDOM-$RANDOM"
name="photo-read-mysql-$RANDOM-$RANDOM"
cleanup() { docker rm -f "$name" >/dev/null 2>&1 || true; docker network rm "$net" >/dev/null 2>&1 || true; }
trap cleanup EXIT
docker network create --internal "$net" >/dev/null
docker run -d --name "$name" --network "$net" --network-alias photo-read-mysql --tmpfs /var/lib/mysql -e MYSQL_ROOT_PASSWORD=isolated-test-only -e MYSQL_DATABASE=photo_test mysql:8.0 >/dev/null
ready=0
for _ in $(seq 1 90); do
 if docker exec "$name" mysqladmin ping -h 127.0.0.1 -uroot -pisolated-test-only --silent >/dev/null 2>&1; then ready=1; break; fi
 sleep 1
done
[ "$ready" = 1 ] || { echo 'temporary mysql failed' >&2; exit 1; }
docker run --rm --network "$net" -v "$PWD:/work:ro" -w /work maven:3.9-eclipse-temurin-17 sh -c 'mkdir -p /tmp/boot /tmp/classes && cd /tmp/boot && jar xf /work/backend/ruoyi-admin/target/ruoyi-admin.jar && cd /work && javac -cp "/tmp/boot/BOOT-INF/lib/*" -d /tmp/classes backend/ruoyi-admin/src/main/java/com/ruoyi/web/controller/equipment/DepartmentScopeResolver.java backend/ruoyi-admin/src/main/java/com/ruoyi/web/controller/equipment/DepartmentScopeDatabaseService.java backend/ruoyi-admin/src/main/java/com/ruoyi/web/controller/equipment/DepartmentScopeAccess.java backend/ruoyi-admin/src/main/java/com/ruoyi/web/controller/equipment/DepartmentScopeSql.java backend/ruoyi-admin/src/main/java/com/ruoyi/web/controller/equipment/InspectionScopeSql.java deploy/InspectionPhotoScopeMysqlTest.java && java -cp "/tmp/classes:/tmp/boot/BOOT-INF/lib/*" com.ruoyi.web.controller.equipment.InspectionPhotoScopeMysqlTest'
