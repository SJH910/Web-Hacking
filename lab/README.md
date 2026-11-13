# 진단 환경 (DVWA 연습 + 실습 웹앱 스캔)

로컬 전용이다. 모든 포트는 `127.0.0.1`에만 열리며, 이 설정을 바꾸지 않는다.

- **B1 연습:** DVWA + ZAP (`docker-compose.yml`). `127.0.0.1:4280`.
- **B2 진단:** 지역아동센터 실습 웹앱(`vuln_practice_web_v1/`) 대상. `127.0.0.1:8000`. 아래 "B2 — 실습 웹앱 스캔" 참고.

---

## B1 — DVWA 연습

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

---

## B2 — 실습 웹앱 스캔 (지역아동센터)

대상은 `vuln_practice_web_v1/`의 Django 앱이다. ZAP을 웹앱과 같은 compose 네트워크(`jiacenter-vuln_lab`)에 붙여 `http://web:8000`을 스캔한다. S2 담당(A02·A04·A10).

### 1. 웹앱 기동

```bash
cd vuln_practice_web_v1 && docker compose up -d && cd ..
```

- 호스트에서는 <http://127.0.0.1:8000> 으로 열린다(이 기기 전용).
- 종료: `(cd vuln_practice_web_v1 && docker compose down)`

### 2. 스캔

| 종류 | 명령 | 내용 |
| --- | --- | --- |
| 기본 스캔 | `./scan-b2.sh baseline` | 공격 요청 없음. 먼저 이걸로 접근·범위 확인 |
| 능동 스캔 | `./scan-b2.sh active` | 스코프 안만 공격. 제외 경로는 `zap-b2-plan.yaml` |

결과는 `reports/b2-*.{html,json}`에 저장되며 git에는 올리지 않는다.

### 스캔 제외 경로

`zap-b2-plan.yaml`의 `excludePaths`는 W가 PR #2에서 전달한 목록(2026-11-13)이다. 부작용(세션 종료·계정 변경·데이터 생성/삭제·외부 요청)이 있는 경로를 범위에서 뺀다. `excludePaths`는 URL 단위라 메서드와 무관하게 GET·POST 모두 제외된다.

- `/admin/` 전체, `/signup*`, `/embed*`, `/attendance/*`, `/my*`
- 게시판 쓰기·댓글·수정·삭제(`/board/posts/new/`, `.../<id>/`, `.../<id>/edit/`, `.../<id>/delete/`)
- `/embed`(SSRF)는 로컬 네트워크로 외부 요청이 나가지 않도록 제외했다. SSRF 자체는 A01(S1)이 통제된 조건에서 수동 확인한다.

### 주의

- 현재 B2 plan은 **로그인 없이** 스캔한다. 설정·헤더·오류 화면(A02·A04·A10)은 비로그인으로도 대부분 보인다. 로그인 필요한 화면은 B1처럼 `ZAP_AUTH_HEADER`로 세션을 넣어 별도 실행한다.
- `spider`는 `postForm: false`라 폼을 제출하지 않는다. 제외 밖 경로에 데이터가 생기지 않게 한 것이다.
- 스캔 결과가 비어 있어도 안전하다는 뜻이 아니다. spider가 페이지를 찾았는지(스코프·접근)부터 확인한다.
