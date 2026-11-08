#!/usr/bin/env bash
# Build without modifying the JAR currently mounted by the isolated backend.
set -euo pipefail
project_dir=$(cd -- "$(dirname -- "$0")/.." && pwd)
cd "$project_dir"
workdir=$(mktemp -d /tmp/equipment-dev-backend.XXXXXX)
candidate="backend/ruoyi-admin/target/ruoyi-admin.jar.next.$$"
cleanup() { rm -f -- "$candidate"; rm -rf -- "$workdir"; }
trap cleanup EXIT
tar -C backend --exclude=target --exclude=.git -cf - . | tar -C "$workdir" -xf -
docker run --rm -v "$workdir:/work" -v equipment-maven-cache:/root/.m2 -w /work maven:3.9-eclipse-temurin-17 mvn -o -B -DskipTests package
mkdir -p backend/ruoyi-admin/target
cp "$workdir/ruoyi-admin/target/ruoyi-admin.jar" "$candidate"
mv -f -- "$candidate" backend/ruoyi-admin/target/ruoyi-admin.jar
docker compose -p equipment-rebuild -f compose.dev.yaml up -d --no-deps --force-recreate backend
# The frontend can respond while the backend is still starting; wait for the
# backend API itself so callers do not begin tests on a transient 502.
ready=0
for _ in $(seq 1 90); do
  if curl -fsS --max-time 3 http://127.0.0.1:18090/prod-api/captchaImage 2>/dev/null | grep -q '"code":200'; then
    ready=1
    break
  fi
  sleep 2
done
if [ "$ready" != 1 ]; then
  printf 'Isolated backend did not become ready; inspect backend logs.\n' >&2
  exit 1
fi
printf 'Isolated backend rebuilt and API is ready.\n' 
