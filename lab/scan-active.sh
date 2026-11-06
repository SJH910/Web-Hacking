#!/usr/bin/env bash
# 로컬 DVWA에 로그인해 세션을 얻은 뒤 ZAP 능동 스캔을 실행한다.
set -euo pipefail
cd "$(dirname "$0")"

BASE=http://127.0.0.1:4280
JAR=$(mktemp)
trap 'rm -f "$JAR"' EXIT

token() { grep -oE "user_token' value='[a-f0-9]+" | sed "s/.*value='//"; }

T=$(curl -s -c "$JAR" -b "$JAR" "$BASE/login.php" | token)
curl -s -o /dev/null -c "$JAR" -b "$JAR" \
  -d "username=admin&password=password&Login=Login&user_token=$T" "$BASE/login.php"

SID=$(awk '$6=="PHPSESSID"{print $7}' "$JAR" | tail -1)
[ -n "$SID" ] || { echo "로그인 실패: 세션 없음" >&2; exit 1; }

cp zap-active-plan.yaml reports/plan.yaml
trap 'rm -f "$JAR" reports/plan.yaml' EXIT

docker compose run --rm \
  -e ZAP_AUTH_HEADER=Cookie \
  -e "ZAP_AUTH_HEADER_VALUE=PHPSESSID=$SID; security=low" \
  -e ZAP_AUTH_HEADER_SITE=dvwa \
  zap \
  zap.sh -cmd -autorun /zap/wrk/plan.yaml
