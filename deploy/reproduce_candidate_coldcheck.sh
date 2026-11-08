#!/usr/bin/env bash
set -euo pipefail
cd /opt/equipment-rebuild
[ "${EMS_ISOLATED_FIXTURE:-}" = YES ] || { echo "Refusing without EMS_ISOLATED_FIXTURE=YES" >&2; exit 1; }
project=equipment-candidate-cold-repro
root=/opt/equipment-candidate-cold-repro
[ ! -e "$root" ] || { echo candidate_path_exists; exit 1; }
if [ -n "$(docker ps -aq --filter "label=com.docker.compose.project=$project")" ] || [ -n "$(docker volume ls -q --filter "label=com.docker.compose.project=$project")" ] || [ -n "$(docker network ls -q --filter "label=com.docker.compose.project=$project")" ]; then
  echo existing_project_resources_refused >&2; exit 1
fi
mkdir -m 700 "$root"
exec > >(tee "$root/coldcheck.log") 2>&1
cp /opt/equipment-candidate-cold-1105b/candidate.jar "$root/candidate.jar"
chmod 400 "$root/candidate.jar"
printf '%s  %s\n' c64a2e65c7529273e07b20111cf1b15c92e9c88a4f9aa36773ec962b2ac6173a "$root/candidate.jar" | sha256sum -c -
sha256sum "$root/candidate.jar"
cat > "$root/override.yaml" <<'YAML'
services:
  backend:
    image: eclipse-temurin:17-jre
    working_dir: /app
    command: ["java", "-jar", "/candidate/candidate.jar"]
    volumes:
      - /opt/equipment-candidate-cold-repro/candidate.jar:/candidate/candidate.jar:ro
  frontend:
    image: equipment-live-frontend:latest
YAML
compose=(docker compose -p "$project" --env-file .env.prodcheck-20261104 -f compose.production.yaml -f deploy/compose.prodcheck.yaml -f "$root/override.yaml")
cleanup() {
  local result=$?
  trap - EXIT
  if ! "${compose[@]}" down; then echo cleanup_failed >&2; exit 1; fi
  exit "$result"
}
trap cleanup EXIT
"${compose[@]}" up -d --no-build mysql redis backend frontend
ready=0
for i in $(seq 1 120); do if curl -fsS http://127.0.0.1:18092/prod-api/captchaImage 2>/dev/null | grep -q '"code":200'; then ready=1; break; fi; sleep 2; done
[ "$ready" = 1 ] || { echo backend_not_ready; exit 1; }
checks=$(printf "%s\n" "SELECT config_value FROM sys_config WHERE config_key='sys.account.captchaEnabled'; SELECT COUNT(*) FROM sys_user WHERE user_name='ry' AND status='1';" | "${compose[@]}" exec -T mysql sh -c 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE" -N 2>/dev/null')
[ "$checks" = $'true\n1' ] || { echo unexpected_initial_security_settings >&2; exit 1; }
printf 'captcha_enabled=true test_user_disabled=true\n' 
python3 -c 'import json,urllib.request; p=json.dumps({"username":"admin","password":"admin123"}).encode();r=urllib.request.urlopen(urllib.request.Request("http://127.0.0.1:18092/prod-api/login",p,{"Content-Type":"application/json"}));assert not json.load(r).get("token");print("default_admin_login_rejected_with_captcha")'
printf "%s\n" "UPDATE sys_config SET config_value='false' WHERE config_key='sys.account.captchaEnabled';" | "${compose[@]}" exec -T mysql sh -c 'mysql -uroot -p"$MYSQL_ROOT_PASSWORD" "$MYSQL_DATABASE" 2>/dev/null'
"${compose[@]}" exec -T redis redis-cli FLUSHDB >/dev/null
python3 deploy/prodcheck_test.py
python3 deploy/prodcheck_business_test.py
sha256sum "$root/candidate.jar"
