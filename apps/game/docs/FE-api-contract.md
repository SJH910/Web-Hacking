# FE API 연동 제안 — B 담당 확인 필요

- 상태: **프런트가 사용하는 제안 계약. 기존 백엔드 구현 또는 합의된 API가 아님.**
- 날짜: 2026-11-19
- 상위 게임 데이터·판정 계약: floor-slice-design.md §8, problem-pool.md, scoring-trust.md.
- 2026-11-19: tools/vulnscan이 아래 계약을 그대로 구현했다([B2](./B2.md)·[B3](./B3.md)·[B5](./B5.md)·[B6](./B6.md)·[B8](./B8.md)). 경로·응답은 변경 없이 확정. 429(요청 제한)가 추가됐고, 랭킹 등록은 선택 필드 `name`을 받는다.
- 정적 FE는 동일 origin의 `/api/game/`를 호출한다. Next의 `/game` basePath를 API 경로에 붙이지 않는다.

## 요청

| 메서드 | 경로(`/api/game/` 이후) | 본문 | 용도 |
|---|---|---|---|
| POST | runs | requestId | 서버가 시드·10문제 순서를 정해 등반 생성 |
| GET | runs/:runId | 없음 | 서버 상태로 이어하기/동기화 |
| POST | runs/:runId/commands | command, revision, requestId | 화이트리스트 명령, 합성 출력 |
| POST | runs/:runId/evidence | evidenceIds, revision, requestId | 선택형 증거 조건 확인 |
| POST | runs/:runId/answers | step, choiceId, revision, requestId | 현재 3단 판정 제출 |
| POST | runs/:runId/hints | revision, requestId | 다음 힌트 및 감점 |
| POST | runs/:runId/next | revision, requestId | 통과 후 다음 층 |
| POST | runs/:runId/ranking | revision, requestId | 서버 점수 기반 등록 |
| GET | rankings | 없음 | 서버 정렬 결과 조회 |

`requestId`는 UUID, `revision`은 서버 상태 버전이다. 서버는 중복 requestId의 재처리를 막고 오래된 revision은 409로 거부해야 한다. FE는 변경 요청 오류 후 자동 재전송하지 않고 상태 재조회를 요구한다. 명령 차단은 output/feedback을 담은 정상 응답으로 반환하며 점수를 변경하지 않는다.

## 응답

랭킹 조회를 제외한 모든 성공 응답은 `{ state, output?, feedback?, correct? }`이다. state는 최신 전체 스냅샷이다. 필드 정의는 [game-api.ts](../app/play/game-api.ts)가 FE 구현 기준이다.

```json
{
  "state": {
    "runId": "run_001", "revision": 0, "seed": "seed_001", "floor": 1,
    "score": 0, "trust": 60, "progress": 0, "cleared": false,
    "canJudge": false, "totalWrong": 0, "totalHints": 0,
    "problem": {
      "id": "night-log", "title": "야간 접속 기록", "type": "terminal",
      "difficulty": "쉬움", "objective": "접근 기록과 감사 기록을 비교하세요.",
      "allyOpening": "정상 트래픽일 수도 있지 않을까?"
    },
    "evidence": [], "step": null, "hints": []
  }
}
```

- runId: 영문·숫자·밑줄·하이픈 1~128자. 인증 토큰 대신 사용하는 것으로 합의한 것은 아님.
- evidence: `{number,title,detail,tag}[]`. 터미널형은 발견한 증거만, 선택형은 선택 가능한 증거를 제공한다.
- step: `null` 또는 `{key,question,choices:[{id,label}]}`. key는 classify/verdict/action. correct/isTrap/why는 제출 전에 보내지 않는다. 판정 후 해설은 feedback으로 제공한다.
- canJudge: 서버가 탐색/증거 조건으로 결정한다. 버튼 비활성화만으로 보호되지 않으므로 서버에서도 검증한다.
- cleared 시 flag를 반환한다. 10층 통과 후 `ending:{title,narrative,badges:string[],bonus:number}`를 함께 제공한다.
- score: 서버 계산 총점이며 엔딩 bonus가 이미 포함되어 있다. FE에서 다시 더하지 않는다.
- hints: 현재 층의 공개된 `{level:1|2|3,text,source:"rule"|"llm"}[]`. 규칙 폴백은 rule로 표시한다.
- next는 이전 층의 evidence/hints/step을 새 층 상태로 교체한다. 서버가 보관한 시드/순서를 유지한다.
- rankings 응답: `[{rank,name,floor,score,trust,hints}]`. 점수→신뢰도→힌트 순 정렬은 서버에서 한다.
- 이름·참가자 식별·랭킹 등록 권한 정책은 B 담당 확정 필요. 이 FE 작업에서는 인증/권한을 추가하거나 바꾸지 않았다.

## 오류와 저장

HTTP 404는 API 미연결 안내, 기타 non-2xx는 상태 재조회 안내. JSON 구조가 잘못되면 상태를 덮어쓰지 않는다. 제한시간 15초, 변경 중 중복 클릭 차단. localStorage는 `{version:1,runId}`만 저장하며 서버 상태 복원에 사용한다. 서버 보관이 없으면 이어하기가 불가능하다. 초기 등반 생성이 타임아웃 난 경우 생성 여부를 알 수 없으며 새 요청은 별도 등반을 만들 수 있다.

## 연동 수락 체크

2026-11-19 서버 측 검증 결과: 아래 8개는 `tools/vulnscan` 테스트와 FE의 실제 `game-api.ts`(isGame·isRanks)로 10층 전체 플레이를 돌려 확인했다. **브라우저 화면에서의 수동 확인은 아직 하지 않았다.**

- [x] night-log에서 필수 명령 그룹 두 개 확인 전 판정 거부
- [x] 정답·함정·점수·신뢰도 및 힌트 감점 서버 검증
- [x] 같은 단계 중복 제출·오래된 revision 거부
- [x] 선택형 증거 조건 확인 후 동일한 3단 판정
- [x] 새로고침 후 동일 시드·층·점수 복원
- [x] 통과 전에 next 거부, 10층 다음 층 없음
- [x] seed별 10문제/난이도/객관식 제한, 문제 중복 없음
- [x] 서버 점수로 랭킹 등록·조회, 6종 엔딩 경계
