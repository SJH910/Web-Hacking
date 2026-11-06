# 진단 연습 환경 (DVWA + ZAP)

로컬 전용이다. DVWA는 `127.0.0.1:4280`에만 열리며, 이 설정을 바꾸지 않는다.

## 시작

```bash
cd lab
mkdir -p reports && chmod 777 reports
docker compose up -d
```

1. <http://127.0.0.1:4280/setup.php> 에서 **Create / Reset Database**를 누른다.
2. `admin` / `password`로 로그인한다.

## 스캔

| 종류 | 명령 | 내용 |
| --- | --- | --- |
| 기본 스캔 | `docker compose run --rm zap zap-baseline.py -t http://dvwa/ -m 2 -r baseline.html -J baseline.json -I` | 공격 요청 없음. 로그인 없이 보이는 범위만 |
| 능동 스캔 | `./scan-active.sh` | 로그인 세션으로 `sqli`, `xss_r` 페이지에 공격 요청 전송 |

결과는 `reports/`에 저장되며 git에는 올리지 않는다.

## 의존성 스캔 (Django)

```bash
python3 -m venv .venv
.venv/bin/pip install pip-audit
.venv/bin/pip-audit -r <웹앱 경로>/requirements.txt
```

## 주의

- 능동 스캔은 `zap-active-plan.yaml`의 `includePaths` 범위만 공격한다. 범위를 넓힐 때는 `setup`, `logout`, `security`, `csrf`를 제외 상태로 유지한다. 이 페이지들을 공격하면 DB 초기화, 로그아웃, 비밀번호 변경이 일어날 수 있다.
- 세션 쿠키는 ZAP Automation의 `replacer` 작업으로 넣었을 때 요청에 실리지 않았다. `ZAP_AUTH_HEADER` 환경 변수를 쓴다.
- 스캔 결과에 SQLi·XSS가 없으면 앱이 안전하다는 뜻이 아닐 수 있다. 세션이 적용됐는지부터 확인한다.

## 종료

```bash
docker compose stop     # 데이터 유지, 다시 켤 때 docker compose start
docker compose down -v  # 전부 삭제
```
