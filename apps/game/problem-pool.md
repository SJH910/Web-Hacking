# 문제 풀 · 층별 랜덤 출제 (X3)

- 담당: 게임 기획 (황선정)
- 상위 문서: [floor-slice-design.md](./floor-slice-design.md) · [tasks.md](./tasks.md)
- 결정: **X3** — 문제를 풀(pool)에 여러 개 두고, 10층을 오르며 **중복 없이 랜덤 출제**. 유형 혼합(터미널/객관식).

> 이 결정으로 ③(두 시나리오 충돌)이 해소된다 — **둘 중 고르지 않고 둘 다 풀의 서로 다른 문제**로 넣는다.

---

## 1. 모델 개요

```
문제 풀(목표 12~15, 점진 확장)
   ├─ 터미널형(type:"terminal")  명령 탐색: grep·count·cat·diff …
   └─ 객관식형(type:"choice")    증거 선택 + 판정
        │  10층 등반 시 출제 규칙(아래)에 따라
        ▼
각 층 = 풀에서 중복 없이 1문제 → 10층 = 서로 다른 10문제
```

## 2. 출제 규칙 (결정적 · 시드 기반)

입력: `pool`(각 문제 `{id, type, difficulty}`), `seed`

1. **1~3층(도입):** `difficulty=="쉬움"` 문제에서 무작위 3개(중복 없음)
2. **4~8층(중반):** 남은 풀 전체에서 무작위 5개(중복 없음)
3. **9~10층(클라이맥스):** 남은 풀의 **`difficulty=="어려움"` 우선** 2개(중복 없음). 어려움이 모자라면 보통으로 보충
4. **유형 상한:** 뽑힌 10개 중 `type=="choice"`는 **최대 5개**
   - 초과 시: 뒤 층의 choice 문제를 남은 terminal 문제로 **교체**(시드 결정적) → 터미널 ≥ 5 보장
5. **시드 저장:** 출제 순서를 세이브에 기록 → **이어하기 시 동일 문제**, **랭킹 공정성**(X1 백엔드 판정과 연결)

> 완전 랜덤이 아니라 **1~3층 쉬움 → 중반 랜덤 → 9~10층 어려움 가중**의 난이도 곡선이 들어간 **제약 있는 무작위**다.

### 풀이 만족해야 할 최소 조건
- 총 문제 **≥ 10** (목표 12~15, 현재 19)
- `difficulty=="쉬움"` **≥ 3** (1~3층용)
- `difficulty=="어려움"` **≥ 2** (9~10층용)
- `type=="terminal"` **≥ 5** (객관식 상한 5를 10층에서 채우려면)

## 3. 문제 공통 스키마 (계약 §8 확장)

```ts
type ProblemType = "terminal" | "choice";
type Problem = {
  id: string;
  title: string;            // 방(관문) 이름 — 풀 내 유일
  type: ProblemType;        // 출제 유형
  difficulty: "쉬움" | "보통" | "어려움";
  owasp: string;            // 학습 소재(A01, A07·A09 …)
  evidence: Evidence[];
  allyOpening: string;      // 라온의 (의도적으로 틀린) 첫마디
  hints: Hint[];
  flag: string;
  // 유형별
  commands?: Command[];        // terminal 전용
  requiredActions?: string[];  // terminal 전용(핵심 명령)
  requiredIds?: string[];      // choice 전용(필수 증거 선택)
  steps: PuzzleStep[];         // 공통: 결론 판정(분류→판정→조치)
};

type FloorState = {
  seed: string;            // 출제 재현용
  order: string[];         // 10개 problem id 순서
  floor: number;           // 1..10
  score: number; trust: number; cleared: boolean;
};
```

- 판정·정답·명령 출력은 **서버 보관**(X1). 클라이언트에 정답 미전송.

## 4. 유형별 템플릿

### 터미널형 (type:"terminal")
- `commands[]`(화이트리스트 명령→합성 출력) + `requiredActions`(핵심 명령 실행) + `steps`(3단 판정)
- 예: 야간 접속 기록(§5 P1)

### 객관식/관찰형 (type:"choice")
- `evidence[]` + `requiredIds`(필수 증거 체크) + `steps`(판정)
- 관찰/시뮬레이션 모드로 증거 열람 후 판정
- 예: 기록 보관소·유리문 로그인·제어실 온실(§5 P2~P4)

## 5. 현재 풀 등록 (4문제 — 확장 시작점)

| id | 제목 | type | 난이도 | OWASP | 결론 | 출처 |
|---|---|---|---|---|---|---|
| night-log | 야간 접속 기록 | terminal | 쉬움 | A07·A09 | 취약 | 내 G2(브루트포스) ·[scenario-1](./scenario-1-record-archive.md) |
| archive | 기록 보관소 | choice | 쉬움 | A01 | 정상(반복≠침입) | 프런트 scenarios.ts |
| login | 유리문 로그인 | choice | 보통 | A01 | 취약/정상 | 프런트 scenarios.ts |
| greenhouse | 제어실 온실 | choice | 보통 | A02 | — | 프런트 scenarios.ts |

- **이름 충돌 해소:** 내 브루트포스 문제를 "기록 보관소" → **"야간 접속 기록"**으로 변경(프런트 archive와 구분).

### 배치1 확장 (G8, +6) → 총 10문제 · 최소 조건 충족

[pool-problems.md](./pool-problems.md)에서 6문제 추가.

| id | 제목 | type | 난이도 | OWASP | 결론 |
|---|---|---|---|---|---|
| old-lock | 낡은 자물쇠 | terminal | 쉬움 | A03 | 취약 |
| whisper | 속삭이는 오류 | terminal | 쉬움 | A10 | 취약 |
| plaintext | 평문의 문 | terminal | 보통 | A04 | 취약 |
| twisted | 뒤바뀐 질문 | terminal | 보통 | A05 | 취약 |
| quiet-vault | 조용한 금고 | terminal | 쉬움 | A02 | **양호** |
| open-window | 열린 창문 | choice | 보통 | A01 | 취약 |

### 배치2 확장 (G8, +5) → 총 15문제

| id | 제목 | type | 난이도 | OWASP | 결론 |
|---|---|---|---|---|---|
| weak-otp | 세 자리 비밀 | terminal | 보통 | A06 | 취약 |
| integrity-box | 봉인된 상자 | choice | 보통 | A08 | 취약 |
| faint-steps | 희미한 발자국 | terminal | 보통 | A09 | **증거 부족** |
| strong-gate | 튼튼한 대문 | terminal | 쉬움 | A07 | **양호** |
| mirror-room | 거울의 방 | terminal | 어려움 | A05(XSS) | 취약 |

### 배치3 확장 (G8, +4 전부 어려움) → 총 19문제

| id | 제목 | type | 난이도 | OWASP | 결론 |
|---|---|---|---|---|---|
| returned-letter | 되돌아온 편지 | terminal | 어려움 | A01 SSRF | 취약 |
| two-faced-token | 두 얼굴의 토큰 | terminal | 어려움 | A08 | 취약 |
| slow-confession | 느린 자백 | terminal | 어려움 | A05(블라인드) | 취약 |
| deceptive-door | 멀쩡해 보이는 문 | terminal | 어려움 | A04 | 취약 |

**풀 합계: 터미널 14 · 객관식 5 · 쉬움 6 · 보통 8 · 어려움 5 (총 19)**
- 난이도 곡선 보강(어려움 1→5) → 후반 층(4~10 랜덤)이 싱겁지 않게.
- 결론: 취약 다수 + 양호 2 + 정상 1 + 증거부족 1.
- OWASP **A01~A10 전 항목** 커버.

> 난이도 곡선: **1~3층 쉬움 → 4~8층 랜덤 → 9~10층 어려움 가중**(§2 적용). 어려움 5개로 9~10층을 충분히 채움.

## 6. 확장 로드맵 (G6 이후)

풀을 10층 플레이 가능 상태로 만들려면 다음을 **추가 저작**해야 한다.
- **터미널형 +4 이상**(현재 1 → ≥5): 로그 분석·설정 점검·주입 흔적 등
- **쉬움 +1 이상**(현재 2 → ≥3): 1~3층용
- 목표 **12~15문제**까지 난이도·OWASP 다양화

## 7. 담당자 인계

| 역할 | 할 일 |
|---|---|
| 게임 기획(G) | 풀 문제 저작(유형·난이도·OWASP 분산), 본 규칙 유지 |
| 백엔드(B) | **출제 알고리즘**(§2, 시드 결정적·제약 반영) + 유형별 판정 |
| 프런트(F) | **두 유형 UI** 모두 처리(터미널 / 객관식·관찰) + 층 전환 |
| LLM(L) | 문제별 라온 대사(판정은 하지 않음) |

## 8. 미정/추후

- 난이도 "어려움" 티어 도입 시점(후반 층 전용)
- 풀 상한(무한 확장 vs 고정)
