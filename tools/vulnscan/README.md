# 웹 취약점 분석 도구 (vulnscan)

웹해킹·보안 **학습 전용** 도구. 로컬 격리 환경의 웹앱을 대상으로 OWASP Top 10 관점의 점검과 모의 해킹(능동 스캔)을 수행하고, 브라우저 대시보드로 결과를 본다.

> 학습·연구 목적의 격리 환경 진단 도구다. 허가되지 않은 시스템을 대상으로 사용하지 않는다.

## 안전 전제 (코드에 강제됨)

- **대상 제한:** `127.0.0.1`·`localhost`·사설 IP(루프백/프라이빗)만 허용. 외부 공인 주소는 요청 자체를 거부한다 (`safeguards.py`).
- **절대 차단 경로:** `/embed`(SSRF)·`/logout`·삭제/초기화류는 passive·active 무관하게 아예 요청하지 않는다.
- **능동 제외 경로:** `/admin`·`/signup`·게시판 쓰기 등은 공격 페이로드를 보내지 않는다. 대시보드에서 추가 가능.
- **속도·총량 제한:** 요청 간격과 최대 요청 수를 둔다(기본 0.2초 / 800건).
- **대시보드도 로컬 전용:** `127.0.0.1`에만 바인딩한다.

## 실행

표준 라이브러리만 쓴다(별도 설치 불필요, Python 3.9+).

```bash
cd tools/vulnscan
python3 scanner.py            # http://127.0.0.1:8900 대시보드
python3 scanner.py --port 8901
```

브라우저에서 대상 URL을 넣고 모드를 고른 뒤 **스캔**.

## 용범의 탑 통합 메뉴

상단 우측 **용범의 탑** 메뉴로 게임 FE를 같은 대시보드에서 연다.
게임 소스는 `apps/game`이며, `hsj`의 증거 선택·판정 FE를 반영했다.

저장소 루트에서 최초 실행:

```bash
npm ci --prefix apps/game
npm run build --prefix apps/game
python3 -B tools/vulnscan/scanner.py --host 127.0.0.1 --port 8900
```

- 통합 화면: <http://127.0.0.1:8900/#game>
- 게임 단독 화면: <http://127.0.0.1:8900/game/>
- 인트로: <http://127.0.0.1:8900/game/intro/>
- 게임 소스를 수정하면 `npm run build --prefix apps/game`로 다시 내보낸 뒤 화면을 새로고침한다.
- Next.js 개발 서버를 별도로 실행할 경우 주소는 `/game/`이다.

게임은 Next.js 정적 내보내기(`output: export`, `basePath: /game`)를 사용한다.
Python 서버는 `apps/game/out` 안의 파일만 제공하고 상위 경로·외부 심볼릭 링크는 차단한다.
빌드가 없으면 안내와 재시도 버튼을 표시한다. 별도의 게임 서버나 프록시는 필요 없다.

스캔과 게임 메뉴를 오가도 페이지와 게임 프레임을 재생성하지 않아 해당 화면의 상태를 유지한다.
새로고침·게임 페이지 간 이동·브라우저 종료 후 저장은 지원하지 않는다.
게임은 합성 데이터 기반 FE 데모이며 스캔 실행 또는 실제 스캔 소견·LLM과 연결되지 않는다.
`apps/game/tasks.md`의 서버 판정·터미널·세이브·랭킹은 별도 후속 작업이다.

검증 명령:

```bash
(cd tools/vulnscan && python3 -B -m unittest test_game_routes -v)
node --experimental-strip-types --test apps/game/tests/scenarios.test.mjs
npm run build --prefix apps/game
```

## 모드

| 모드 | 내용 |
| --- | --- |
| 수동 (passive) | 공격 요청 없이 헤더·쿠키·응답만 관찰. 가장 안전 |
| 능동 (모의 해킹) | 스코프 안에 공격 페이로드 전송(반사형 XSS, SQL 오류·불리언, 오류 유도). 제외 경로·속도제한 적용 |

## 점검 범위 (OWASP A01~A10)

정직성 원칙: 원격 스캔으로 자동 판정 가능한 것만 취약/양호로 보고하고, 소스·서버 접근이 필요한 항목은 **수동/화이트박스 필요**로 표시한다.

| 항목 | 방식 | 자동 |
| --- | --- | --- |
| A01 접근통제 | 숫자 ID 경로 접근성 힌트 / SSRF는 수동 | 일부 |
| A02 보안 설정 | 보안 헤더 누락, 서버 버전 노출 | O |
| A03 공급망 | 의존성 파일 스캔 필요 | 수동 |
| A04 암호화 | HTTP 평문, 쿠키 플래그, HSTS | O |
| A05 인젝션 | 반사형 XSS, SQL 오류 기반·불리언 기반 | O(능동) |
| A06 안전하지 않은 설계 | 로직 분석 필요 | 수동 |
| A07 인증 실패 | 로그인 흐름 수동(무차별 대입은 범위 밖) | 수동 |
| A08 무결성 실패 | 업로드·쿠키 권한값 수동 | 수동 |
| A09 로깅·경보 | 서버 로그 관찰 필요 | 수동 |
| A10 예외 처리 | 오류 유도로 DEBUG/상세 오류 노출 | O |

## 구성

| 파일 | 역할 |
| --- | --- |
| `scanner.py` | 로컬 서버(대시보드 + `/api/scan`), 얕은 크롤러·GET 폼 파라미터 수집 |
| `checks.py` | OWASP 점검 로직(passive/active) |
| `safeguards.py` | 호스트 allowlist·차단/제외 경로·속도제한 — **모든 요청의 단일 통로** |
| `static/index.html` | 대시보드 UI |

## 결과 해석

- **취약:** 자동 점검으로 확인된 취약점. 위험도(critical~low) 함께 표시.
- **수동 필요:** 이 도구만으로 판정 불가, 수동/화이트박스 점검 대상.
- **양호:** 해당 점검을 통과.

자동 판정은 오탐이 있을 수 있으므로, 중요한 소견은 수동 재현으로 확인한다. 세션 쿠키·시크릿은 결과에 저장하지 않는다.

## 로컬 GPT-2 API 연동 실습 (A05 한 건)

같은 컴퓨터에서 `llm-from-scratch`의 기존 Chapter 7 가중치와 Python 환경을 사용한다.
아래 명령은 Web-Hacking 저장소 루트에서 각자 다른 터미널에서 실행한다.
첫 줄의 경로는 로컬 모델 프로젝트 위치에 맞춘다.

```bash
MODEL_DIR="$HOME/projects/llm-from-scratch"
"$MODEL_DIR/.venv/bin/python" tools/vulnscan/local_model.py --model-dir "$MODEL_DIR" --port 8910
```

```bash
python3 tools/vulnscan/scanner.py --llm-port 8910
```

대시보드 `http://127.0.0.1:8900`에서 실습 웹앱을 능동 스캔한다.
스캐너가 감지한 첫 A05 의심 소견 카드에 영문 모델 설명이 표시된다.
스캔 결과의 판정과 모델 설명은 독립적이다. API 오류 시 소견 카드에 오류가 표시되며 기존 판정이 반환된다.

API는 `127.0.0.1`에서 `POST /v1/chat/completions`를 제공한다.
`model: "local-gpt2"`, 단일 `user` 메시지, 선택적 `max_tokens`를 받는다.
스캐너는 점검 코드에서 정한 관찰 문장만 보낸다. URL, 응답 본문, 쿠키, 파라미터 값은 전송하지 않는다.

### 모델 교체 — 자체 모델 ↔ Ollama (로컬·무과금)

연동부가 **OpenAI 호환**이라, 자체 모델 대신 **Ollama를 로컬로** 붙일 수 있다(외부 전송·과금 없음). 코드 변경 없이 **포트·모델명만** 바꾼다.

```bash
# 1) Ollama 로컬 서버 + 모델 받기 (한 번)
ollama serve                 # 127.0.0.1:11434 (OpenAI 호환 /v1)
ollama pull llama3           # 또는 qwen2.5, mistral, deepseek-r1 등 로컬 모델

# 2) 스캐너를 Ollama로 연결 (포트 11434 + 모델명)
python3 tools/vulnscan/scanner.py --llm-port 11434 --llm-model llama3
```

- 기본값은 **자체 모델**(`--llm-model local-gpt2`, 포트 8910) — 아무것도 안 바꾸면 기존 그대로.
- **로컬 전용 유지:** Ollama도 `127.0.0.1`에만 붙는다. 데이터는 밖으로 나가지 않는다.
- **클라우드 API 금지:** 외부 전송이 생기는 상용 API(DeepSeek/OpenAI 클라우드 등)는 스캐너에 연결하지 않는다.
- 전송 경계는 동일: 관찰 문장만, URL·응답·쿠키·값은 안 보냄.
