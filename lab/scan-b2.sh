#!/usr/bin/env bash
# B2 스캔 — 지역아동센터 실습 웹앱(jiacenter) 대상.
# 웹앱 compose(jiacenter-vuln)가 먼저 떠 있어야 한다:
#   (cd vuln_practice_web_v1 && docker compose up -d)
#
# ZAP을 웹앱과 같은 네트워크(jiacenter-vuln_lab)에 붙여 http://web:8000 을 스캔한다.
# 공격 요청을 보내지 않는 기본 스캔(baseline)과, 스코프 안만 치는 능동 스캔(active) 두 가지.
#
# 사용법:
#   ./scan-b2.sh baseline   # 패시브만. 공격 요청 없음. 먼저 이걸로 범위·접근 확인.
#   ./scan-b2.sh active     # 능동 스캔. zap-b2-plan.yaml 의 excludePaths 적용.
set -euo pipefail
cd "$(dirname "$0")"

MODE="${1:-baseline}"
NET=jiacenter-vuln_lab
TARGET=http://web:8000
mkdir -p reports

# 웹앱 네트워크가 있는지 확인
docker network inspect "$NET" >/dev/null 2>&1 || {
  echo "네트워크 $NET 없음. 웹앱을 먼저 띄우세요: (cd vuln_practice_web_v1 && docker compose up -d)" >&2
  exit 1
}

case "$MODE" in
  baseline)
    # 공격 요청 없음. 로그인 없이 보이는 범위만.
    docker run --rm --network "$NET" -v "$PWD/reports:/zap/wrk:rw" \
      ghcr.io/zaproxy/zaproxy:stable \
      zap-baseline.py -t "$TARGET/" -m 2 -r b2-baseline.html -J b2-baseline.json -I
    echo "결과: reports/b2-baseline.html, reports/b2-baseline.json"
    ;;
  active)
    # 능동 스캔. 제외 경로는 zap-b2-plan.yaml 에 있다.
    cp zap-b2-plan.yaml reports/b2-plan.yaml
    trap 'rm -f reports/b2-plan.yaml' EXIT
    docker run --rm --network "$NET" -v "$PWD/reports:/zap/wrk:rw" \
      ghcr.io/zaproxy/zaproxy:stable \
      zap.sh -cmd -autorun /zap/wrk/b2-plan.yaml
    echo "결과: reports/b2-active.html, reports/b2-active.json"
    ;;
  *)
    echo "사용법: $0 [baseline|active]" >&2
    exit 1
    ;;
esac
