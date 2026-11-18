# 프로젝트 소스 트리와 역할별 독립 테스트

## 현재 구현된 구조

```text
hsj/
|-- app/
|   |-- layout.tsx          [프런트엔드] 공통 HTML 레이아웃과 메타데이터
|   |-- page.tsx            [프런트엔드] 테스트 UI, 목업 시나리오와 상호작용
|   `-- globals.css         [프런트엔드] 게임 UI 테마와 반응형 스타일
|-- package.json            [공통] Next.js 실행, 빌드, 타입 검사
|-- package-lock.json       [공통] npm 의존성 잠금
|-- tsconfig.json           [공통] TypeScript 설정
|-- next.config.ts          [공통] Next.js 설정
|-- plan.md                 [게임 기획] 게임 제안
|-- team-roles.md           [공통] 팀 역할과 협업 방식
|-- role-prompts.md         [공통] 네 역할별 작업 프롬프트
|-- page-ui-meta-prompt.md  [프런트엔드] 페이지 UI 메타프롬프트
`-- work-log.md             [공통] 작업 이력
```

현재는 프런트엔드 목업만 구현되어 있다. Python 시나리오 API, 실제 LLM 연결, 자동화 테스트는 아직 저장소에 없다.

## 역할별 구현을 분리한 권장 구조

아래는 목표 구조이며 아직 생성되지 않은 디렉터리와 서버를 포함한다. 문서 파일은 현재 저장소 루트에 있고, 팀이 원하면 후속 정리 때 `docs/`로 옮긴다.

```text
hsj/
|-- apps/
|   `-- web/                         [프런트엔드]
|       |-- app/
|       |   |-- page.tsx             게임 화면 조립
|       |   `-- api/                 선택 사항: 브라우저용 서버 프록시
|       |-- src/
|       |   |-- components/          층 지도, 퀘스트, 증거, 동료 UI
|       |   |-- features/floor/      층 진행과 클라이언트 상태
|       |   |-- lib/api-client.ts    백엔드 계약을 호출하는 클라이언트
|       |   `-- mocks/               화면 개발·독립 테스트용 응답
|       `-- tests/                   컴포넌트와 사용자 흐름 테스트
|
|-- services/
|   |-- scenario-api/                [Python 백엔드·보안]
|   |   |-- app/
|   |   |   |-- routes/              시나리오 조회와 행동 처리 API
|   |   |   |-- domain/              퍼즐 상태와 결정적 정답 판정
|   |   |   `-- data/                합성 시나리오와 증거
|   |   |-- tests/                   API·도메인·입력 검증 테스트
|   |   |-- pyproject.toml
|   |   `-- Dockerfile
|   |
|   `-- companion-api/                [LLM]
|       |-- app/
|       |   |-- routes/              동료 대화 API
|       |   |-- prompts/             시스템 규칙과 캐릭터 프롬프트
|       |   |-- context/             게임 상태를 최소 컨텍스트로 변환
|       |   `-- providers/           모델 연결과 로컬 대체 구현
|       |-- evals/                    고정 입력·기대 출력·품질 평가
|       |-- tests/                    응답 스키마와 오류 처리 테스트
|       `-- pyproject.toml
|
|-- packages/
|   `-- contracts/                    [세 역할 공동 소유]
|       |-- openapi.yaml              서비스 간 HTTP 요청·응답 계약
|       |-- schemas/                  JSON Schema로 검증할 데이터 형식
|       `-- fixtures/                 모든 담당자가 공유하는 합성 테스트 데이터
|
|-- docs/
|   |-- project-structure.md          이 문서
|   `-- work-log.md
|-- package.json                      웹 앱 실행·타입 검사
`-- compose.yaml                      선택 사항: 전체 서비스를 한 번에 실행
```

`apps/web`, `services/scenario-api`, `services/companion-api`는 각각 단독 실행할 수 있게 유지한다. `packages/contracts`에는 인터페이스와 합성 예제만 두고 서비스 구현 로직은 넣지 않는다.

## 역할 간 경계와 연결

```text
[웹 앱]
  |-- 시나리오 요청 ------------------> [Python scenario-api]
  |                                       |-- 행동 허용 여부 검증
  |                                       |-- 게임 상태 및 증거 판정
  |
  `-- 동료 대화 요청 ------------------> [LLM companion-api]
                                          |-- 전달된 증거만 컨텍스트에 사용
                                          |-- 스키마가 맞는 대화·힌트 응답

             양쪽 API의 요청·응답 형식
                            |
                   [packages/contracts]
```

- 시나리오 API가 관문 완료 여부와 증거의 진위를 결정한다.
- LLM API는 대화·힌트만 반환하며 게임 상태를 직접 변경하지 않는다.
- 웹 앱은 서버가 제공한 상태를 표시한다. 모델 응답을 정답 판정으로 사용하지 않는다.
- 브라우저에서 LLM 제공자 API를 직접 호출하지 않는다. 모델 키와 제공자 호출은 LLM 서버에 둔다.

## 함수·변수 이름과 공통 계약

모든 내부 이름을 세 역할이 똑같이 정할 필요는 없다. 다만 모듈·서비스 경계를 넘어가는 API 필드, 이벤트, 공용 타입은 이름과 의미를 통일해야 한다. 각 담당자의 내부 함수와 변수는 자기 영역에서 일관되게 정하고, 경계에서 공통 계약으로 변환한다.

예를 들어 프런트엔드에서 `selectedFloor`를 쓰고 백엔드 내부에서 `current_floor`를 쓰는 것은 괜찮다. API 요청/응답에서는 한 가지 표기법으로 고정하고, 변환이 필요하면 API 클라이언트나 DTO에서 명시적으로 변환한다. `floor`, `floorNumber`, `level`처럼 같은 개념에 여러 이름을 섞어 쓰지 않는다.

권장 규칙:

| 구분 | 규칙 | 예 |
|---|---|---|
| TypeScript 변수·함수 | `camelCase` | `selectedScenario`, `submitAction()` |
| TypeScript 타입·컴포넌트 | `PascalCase` | `FloorState`, `EvidenceCard` |
| Python 변수·함수 | `snake_case` | `selected_scenario`, `submit_action()` |
| JSON/OpenAPI 필드 | `camelCase`로 고정 | `scenarioId`, `evidenceIds`, `completed` |
| JSON Schema 계약 이름 | 의미가 하나인 명사형 | `ScenarioActionRequest`, `CompanionReply` |
| 상태·이벤트 값 | 소문자 `snake_case` 문자열 또는 명시된 enum | `scenario_started`, `action_rejected` |
| 환경 변수 | 대문자 `SNAKE_CASE` | `COMPANION_API_KEY` |

언어별 관례는 내부 구현에 적용하고, JSON 계약의 필드명은 서비스 전반에서 동일하게 유지한다. 자동 생성된 API 타입이나 검증 스키마를 사용하면 이름 불일치를 일찍 발견할 수 있다.

MVP에서 우선 고정할 공용 용어:

```text
floor          현재 탑 층 번호 (1부터 시작)
scenarioId     선택한 사전 정의 시나리오 ID
objective      플레이어가 해결할 목표
evidenceIds    서버가 발견했다고 판정한 증거 ID 목록
discoveredFlags 시나리오 진행 중 확인한 상태 플래그
trust          동료 신뢰도 (0-100 정수)
completed      서버가 판정한 관문 완료 여부
```

LLM 요청에는 서버가 허용한 게임 상태와 증거 ID만 전달한다. LLM 응답은 `message`, `confidence`, `evidenceIds`, `suggestedAction` 등 합의된 출력 스키마로 검증한다. LLM이 `completed` 값을 반환하거나 서버의 완료 상태를 덮어쓰게 하지 않는다.

API 계약의 변경 절차:

1. `packages/contracts`의 OpenAPI/Schema와 합성 fixture를 먼저 변경한다.
2. 해당 변경을 소비하는 프런트엔드·Python·LLM의 담당자가 호환성 영향을 확인한다.
3. 제공자는 스키마 검증과 단위 테스트를 갱신하고, 소비자는 fixture 기반 테스트를 갱신한다.
4. 필드 제거·의미 변경은 기존 소비자를 깨뜨릴 수 있으므로 버전 변경 또는 호환 기간을 둔다.

## 역할별 독립 테스트 방법

아래 명령은 제안하는 테스트 구조가 만들어진 뒤 사용할 명령이다. 현재 저장소에는 `apps/`, Python 서비스, `npm test` 스크립트가 아직 없으며, 현재 가능한 검사는 루트의 `npm run typecheck`와 `npm run build`다.

### 게임 기획·프런트엔드

```bash
cd apps/web
npm run dev
npm run typecheck
npm test
```

- 로컬 목업 또는 `packages/contracts/fixtures` 응답으로 화면을 구동한다.
- 백엔드 없이 시나리오 카드 선택, 로딩·오류·빈 결과, 완료 화면을 테스트한다.
- API 연결은 별도 통합 테스트에서 계약에 맞는지 확인한다.

### Python 백엔드·보안

```bash
cd services/scenario-api
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
uvicorn app.main:app --reload --port 8001
```

- 외부 모델과 웹 앱 없이 도메인·API 테스트를 실행한다.
- 정상 요청 외에도 잘못된 입력, 허용되지 않은 행동, 상태 경계값을 테스트한다.
- 테스트 데이터는 합성 fixtures만 사용하고, 임의 코드 실행이나 실제 대상 URL 요청을 구현하지 않는다.

### LLM 담당

```bash
cd services/companion-api
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
pytest
python -m app.evals
uvicorn app.main:app --reload --port 8002
```

- 프롬프트와 컨텍스트 구성은 고정된 게임 상태 fixtures로 평가한다.
- 기본 단위 테스트는 외부 모델 호출 없이 결정적인 fake provider로 수행한다.
- 별도의 선택적 평가에서만 서버 측 테스트 키를 사용한다. 키가 없으면 단위 테스트는 그대로 실행 가능해야 한다.
- 정답을 지어내는지, 전달되지 않은 증거를 주장하는지, 형식이 잘못된 응답이 처리되는지 확인한다.

### 전체 통합 테스트

```bash
# 저장소 루트에서 전체 서비스 실행
docker compose up --build

# 별도 터미널에서 웹 타입 검사와 테스트
npm run typecheck
npm test
```

통합 테스트에서는 고정된 시나리오 API 응답과 fake LLM provider를 우선 사용한다. 실제 모델 키나 외부 웹사이트 없이 핵심 게임 흐름을 재현할 수 있어야 한다.

## 독립 작업을 가능하게 하는 팀 규칙

1. 구현 전에 OpenAPI와 JSON Schema로 요청·응답을 합의하고 계약 변경을 함께 리뷰한다.
2. 담당자는 공통 계약의 자기 서비스 구간과 관련 fixtures를 유지한다. 다른 담당자의 구현 파일을 직접 수정하지 않는다.
3. 각 역할은 자체 테스트 명령과 로컬 실행 명령을 문서화하고, 다른 서비스가 꺼져도 단위 테스트가 통과하게 한다.
4. Pull request마다 자기 영역의 테스트를 실행한다. 계약 변경 시 웹·Python·LLM 담당자가 함께 호환성을 확인한다.
5. 합성 fixtures는 외부 네트워크나 비밀 키 없이 재현 가능하게 유지한다.

## MVP에서 먼저 나눌 최소 단위

현재 단일 웹 앱을 한 번에 다중 패키지 구조로 바꾸기보다 다음 계약과 경계부터 분리하는 것을 권장한다.

1. 웹 앱에서 시나리오 데이터와 결과 목업을 별도 파일로 옮긴다.
2. 시나리오 입력·응답과 LLM 입력·응답 JSON Schema를 합의한다.
3. Python 담당은 정적 합성 시나리오 API와 pytest를 먼저 만든다.
4. LLM 담당은 fake provider와 프롬프트 평가 케이스부터 만든다.
5. 프런트엔드는 mock API로 독립 동작하도록 만든 뒤 각 API에 연결한다.
