# G2 — 시나리오 1 「기록 보관소」 완성형 명세

- 담당: 게임 기획
- 상위 문서: [floor-slice-design.md](./floor-slice-design.md) · [tasks.md](./tasks.md)
- 대상 단계: M1 수직 슬라이스 (1층·1시나리오)
- 조작 모델: **가상 터미널 탐색 + 결정적 판정**(X2). 판정은 **백엔드**(X1).
- 학습 주제: 접근 로그 분석 → **무차별 대입 흔적 + 실패 미기록**(OWASP A07 인증 실패 · A09 로깅 실패)

> 모든 데이터는 **가상·합성**이다. 실제 요청·명령 실행·네트워크 접근은 없다. 터미널은 아래 화이트리스트 명령만 받고, 출력은 서버가 보관한 고정 스크립트다.

---

## 1. 관문 개요

- **관문명:** 1층 — 기록 보관소
- **난이도:** 쉬움
- **목표:** 문지기 로그인 기록을 뒤져 **누가·어떻게 침입을 시도했는지** 밝히고, 왜 막히지 않았는지 판정한다.
- **표면(surface):** 터미널
- **라온(동료)의 함정:** "기록이 좀 많은데 인기 많은 문이라 그래. 정상 트래픽이야." → 이 말대로 고르면 **오답**.

## 2. 합성 데이터 (서버 보관, 터미널 출력용)

### access.log (문지기 로그인 접근 기록)
```
203.0.113.7  [09:58:14] "POST /gate/login" 200   gatekeeper
10.0.0.9     [10:02:01] "POST /gate/login" 401
10.0.0.9     [10:02:01] "POST /gate/login" 401
10.0.0.9     [10:02:02] "POST /gate/login" 401
10.0.0.9     [10:02:02] "POST /gate/login" 401
10.0.0.9     [10:02:03] "POST /gate/login" 401
   … (10.0.0.9 에서 6초간 23회 연속 401) …
10.0.0.9     [10:02:07] "POST /gate/login" 200   gatekeeper
198.51.100.4 [10:05:33] "GET  /gate/status" 200
```

### security.log (감사 로그)
```
[10:02:07] login_ok ip=10.0.0.9 user=gatekeeper
```
→ **성공만 1줄.** 실패 23건은 한 줄도 없음.

### gate.conf (문 설정)
```
session_timeout     = 30m
lockout_threshold   =            # 비어 있음 — 잠금 미설정
log_failed_attempts = false      # 실패를 기록하지 않음
```

## 3. 허용 명령 세트 (화이트리스트 → 고정 출력)

| key | 입력(정규식) | 출력 요약 | 드러내는 증거 |
|---|---|---|---|
| help | `^help$` | 사용 가능한 명령 목록 | — |
| ls | `^ls$` | `access.log  security.log  gate.conf` | — |
| cat_access | `^cat\s+access\.log$` | access.log 전체 | E01·E02 |
| grep_401 | `^grep\s+401\s+access\.log$` | 401 줄만(23건, 전부 10.0.0.9) | E01 |
| grep_200 | `^grep\s+200\s+access\.log$` | 200 줄 2건(정상 1 + 공격 뒤 1) | E02 |
| count_ip | `^count\s+10\.0\.0\.9$` | `10.0.0.9 → 6초간 24회 (23×401, 1×200)` | E01 |
| cat_security | `^cat\s+security\.log$` | login_ok 1줄뿐 | E03 |
| cat_conf | `^cat\s+gate\.conf$` | lockout 비어 있음·log_failed_attempts=false | E03 |
| diff_log | `^diff\s+attempts\s+logged$` | `시도한 실패: 23 / 기록된 실패: 0 → 23건 미기록` | E03 |

- 화이트리스트 밖 입력 → `허용되지 않은 명령입니다.` (안전 차단, 진행·점수 영향 없음)
- 대소문자·여분 공백은 서버에서 정규화 후 매칭.

## 4. 증거 (Evidence)

| id | 제목 | 상세 | 획득 경로 |
|---|---|---|---|
| E01 | 반복된 접근 시도 | 10.0.0.9 한 곳에서 6초간 23회 연속 로그인 실패(401) | grep_401 / count_ip |
| E02 | 실패 뒤 성공 | 다수 실패 직후 같은 IP에서 1회 성공(200) | grep_200 / cat_access |
| E03 | 기록되지 않은 실패 | 실패 23건이 감사 로그에 없음 + 잠금 미설정 | cat_security / cat_conf / diff_log |

## 5. 완료 조건

### (A) 행동 기반 — 핵심 탐색을 실제로 했는가
- **반드시** 다음을 **각 그룹에서 1개 이상** 실행:
  - 무차별 대입 확인: `grep_401` **또는** `count_ip`
  - 미기록 확인: `cat_security` **또는** `cat_conf` **또는** `diff_log`
- `requiredActions`(둘 중 최소 1개씩)를 충족해야 판정 단계 활성화.

### (B) 결론 기반 — 3단 판정 (결정적, 보기 중 정답 1개)

**1) 분류 — 이 기록이 가리키는 문제는?**
- A. **무차별 대입(brute-force) 시도 + 실패 미기록** ✅
- B. 인기 많은 문이라 생긴 정상 트래픽 ⟵ *라온의 주장(함정)*
- C. 단순 서버 과부하
- 해설: 한 IP가 6초간 23회 실패 후 성공 → 자동 대입. 게다가 실패가 로그에 없음. "정상 트래픽"이 아니다(라온 반박).

**2) 판정 — 이 상태는?**
- A. 양호
- B. **취약** ✅
- C. 증거 부족(needs_review)
- 해설: 무제한 시도(잠금 없음) + 실패 미기록 → 탐지·차단 부재. 증거가 명확해 needs_review 아님.

**3) 조치 — 올바른 대응은?**
- A. **로그인 시도 횟수 제한·잠금 + 실패 로그 기록** ✅
- B. 로그를 더 자주 비워 용량 확보 ⟵ *함정(오히려 증거 삭제)*
- C. 서버 증설
- 해설: `lockout_threshold` 설정 + `log_failed_attempts=true`로 차단·탐지 복구.

## 6. 라온(동료) 대사

- **틀린 첫마디(opening):** "음, 접근 기록이 좀 많긴 한데… 인기 많은 문이라 그런 거 아냐? 정상 트래픽 같은데 그냥 넘어가자."
- **힌트 단계(질문 시):**
  1. "한 곳(IP)에서 몇 번이나 두드렸는지 세어볼까?" *(→ count_ip 유도)*
  2. "실패가 이렇게 많은데, 그게 전부 기록에 남았는지 security.log랑 비교해봐." *(→ cat_security/diff 유도)*
  3. "막는 장치(잠금)도, 남기는 장치(기록)도 없어 — 그게 핵심이야." *(→ 조치 정답 유도)*
- 함정 매핑: 1번 분류의 보기 B(정상 트래픽) = 라온의 첫마디. 이 보기를 고르면 오답 + "증거를 다시 보라"로 유도.

## 7. 보상·판정 결과

- **통과 플래그:** `FLAG{floor1_unlogged_bruteforce}`
- 3단 전부 정답 → 봉인 해제 → 2층 해금.
- 점수·신뢰도 가감은 G4(수치) 확정값을 따른다. 라온의 틀린 말을 증거로 반박하고 바로 정답 시 신뢰도 회복.

## 8. 구현용 데이터 (계약 §8 형식 — 백엔드 B1·B2가 그대로 사용)

```ts
const scenarioRecordArchive: Scenario = {
  id: "record-archive",
  title: "기록 보관소",
  category: "로그 분석",
  difficulty: "쉬움",
  surface: "terminal",
  allyOpening:
    "음, 접근 기록이 좀 많긴 한데… 인기 많은 문이라 그런 거 아냐? 정상 트래픽 같은데 그냥 넘어가자.",
  evidence: [
    { number: "E01", title: "반복된 접근 시도", detail: "10.0.0.9에서 6초간 23회 연속 401.", tag: "접근 기록" },
    { number: "E02", title: "실패 뒤 성공", detail: "다수 실패 직후 같은 IP에서 200 1건.", tag: "응답 기록" },
    { number: "E03", title: "기록되지 않은 실패", detail: "실패 23건이 감사 로그에 없음 + 잠금 미설정.", tag: "권한/로깅 단서" },
  ],
  commands: [
    { key: "help",         pattern: "^help$",                        output: "명령: ls, cat <파일>, grep <코드> access.log, count <ip>, diff attempts logged", reveals: [] },
    { key: "ls",           pattern: "^ls$",                          output: "access.log  security.log  gate.conf", reveals: [] },
    { key: "cat_access",   pattern: "^cat\\s+access\\.log$",         output: "<access.log 전체>", reveals: ["E01", "E02"] },
    { key: "grep_401",     pattern: "^grep\\s+401\\s+access\\.log$", output: "<10.0.0.9의 401 23줄>", reveals: ["E01"] },
    { key: "grep_200",     pattern: "^grep\\s+200\\s+access\\.log$", output: "203.0.113.7 … 200 / 10.0.0.9 [10:02:07] 200", reveals: ["E02"] },
    { key: "count_ip",     pattern: "^count\\s+10\\.0\\.0\\.9$",     output: "10.0.0.9 → 6초간 24회 (23×401, 1×200)", reveals: ["E01"] },
    { key: "cat_security", pattern: "^cat\\s+security\\.log$",       output: "[10:02:07] login_ok ip=10.0.0.9 user=gatekeeper", reveals: ["E03"] },
    { key: "cat_conf",     pattern: "^cat\\s+gate\\.conf$",          output: "lockout_threshold= (비어 있음)\nlog_failed_attempts=false", reveals: ["E03"] },
    { key: "diff_log",     pattern: "^diff\\s+attempts\\s+logged$",  output: "시도한 실패: 23 / 기록된 실패: 0 → 23건 미기록", reveals: ["E03"] },
  ],
  completion: {
    // 그룹별 1개 이상 실행해야 판정 활성화 (OR 조합은 백엔드에서 처리)
    requiredActions: ["grep_401|count_ip", "cat_security|cat_conf|diff_log"],
    steps: [
      { key: "classify", question: "이 기록이 가리키는 문제는?",
        choices: [
          { id: "c1", label: "무차별 대입 시도 + 실패 미기록", correct: true },
          { id: "c2", label: "인기 많은 문이라 생긴 정상 트래픽", correct: false, isTrap: true },
          { id: "c3", label: "단순 서버 과부하", correct: false },
        ],
        why: "한 IP가 6초간 23회 실패 후 성공 → 자동 대입. 실패가 로그에 없어 '정상 트래픽'이 아니다." },
      { key: "verdict", question: "이 상태는?",
        choices: [
          { id: "v1", label: "양호", correct: false },
          { id: "v2", label: "취약", correct: true },
          { id: "v3", label: "증거 부족(needs_review)", correct: false },
        ],
        why: "무제한 시도(잠금 없음) + 실패 미기록 → 탐지·차단 부재. 증거가 명확해 needs_review 아님." },
      { key: "action", question: "올바른 조치는?",
        choices: [
          { id: "a1", label: "시도 횟수 제한·잠금 + 실패 로그 기록", correct: true },
          { id: "a2", label: "로그를 더 자주 비워 용량 확보", correct: false, isTrap: true },
          { id: "a3", label: "서버 증설", correct: false },
        ],
        why: "lockout_threshold 설정 + log_failed_attempts=true로 차단·탐지 복구." },
    ],
  },
  hints: [
    { level: 1, text: "한 곳(IP)에서 몇 번이나 두드렸는지 세어볼까?" },
    { level: 2, text: "실패가 이렇게 많은데, 그게 전부 기록에 남았는지 security.log랑 비교해봐." },
    { level: 3, text: "막는 장치(잠금)도, 남기는 장치(기록)도 없어 — 그게 핵심이야." },
  ],
  flag: "FLAG{floor1_unlogged_bruteforce}",
};
```

## 9. 예외 흐름 점검

| 흐름 | 기대 동작 |
|---|---|
| 탐색 전 판정 시도 | requiredActions 미충족 → 판정 비활성 + "먼저 기록을 조사하세요" |
| 화이트리스트 밖 명령 | "허용되지 않은 명령입니다." (점수 영향 없음) |
| 분류에서 라온 주장(B) 선택 | 오답 처리 + "증거(E01·E03)를 다시 보라" |
| 조치에서 함정(B) 선택 | 오답 + "그건 증거를 지우는 행위" 안내 |
| 오답 반복 | 재시도 허용, 점수 하한 0(G4 수치) |

## 10. 다른 담당자와 맞출 것

- **백엔드(B1·B2):** §8 데이터·`requiredActions` OR 매칭·명령 정규식 판정·3단 채점을 서버에서 구현. 정답/출력 클라이언트 미전송.
- **프런트(F1):** 터미널 입력창 + 출력 영역, 증거 패널(E01~E03 점등), 판정 단계 UI.
- **LLM(L1):** 라온 대사를 §6 톤·확신도 스키마로. 단, **정답 판정은 하지 않음**(함정 첫마디·힌트만).
- **게임 기획 후속:** G3(함정·대사 확정 — 본 문서로 1차 완료) · G4(점수·신뢰도 수치).
