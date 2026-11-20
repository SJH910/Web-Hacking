# 라온 L2-L4 독립 모듈

위치: services/raon/raon.py. Python 표준 라이브러리만 사용하며 웹/게임 API에는 아직 연결되지 않았다.
외부 모델 호출·키·점수/신뢰도 변경·관문 판정을 수행하지 않는다.

## 실행
저장소 루트에서:
python3 -m unittest discover -s services/raon -p 'test_*.py' -v

generate(context, provider=None)는 response 및 hint를 반환한다.
provider는 Context를 받아 JSON 문자열 또는 dict를 반환하는 서버 측 함수다.
기본값은 모델을 호출하지 않고 source="rule", is_fallback=true로 표시한다.
실제 Provider 어댑터는 자체 HTTP timeout을 강제해야 한다. 이 모듈은 멈춘 함수를 강제 종료하지 않는다.

## L2 Context
필수 필드: scenario_id, stage, visible_evidence, player_claim, backend_feedback,
raon_trust, hint_directive.
stage: exploration / judgment / feedback.
visible_evidence: [{id,content}] 공개 증거만. 원본 Evidence의 number를 id,
공개 title/detail을 content로 변환하는 어댑터는 Backend 담당이다.
신뢰도 0~100은 scoring-trust.md에 맞췄다. hint_level은 basic/focused/detailed를
1/2/3으로 변환한다. 신뢰도에서 힌트 수준을 정하는 행위는 Backend 담당이다.
Context 전체는 신뢰된 서버 상태에서 구성해야 하며 사용자 입력을 통째로 전달하면 안 된다.

## L3 Response
필수 필드: schema_version("1.0"), scenario_id, stance, dialogue(1~300자),
evidence_refs, verification_cue(1~200자).
scenario_id/stance는 Context와 일치해야 한다. evidence_refs는 공개 ID만 허용한다.
단서는 Backend 승인 문구와 정확히 같아야 한다.
일반 모델 응답 검증은 validate_response로 수행한다.
JSON 검증은 대사 의미·정답 누설을 완전히 검사하지 않는다. L5 및 승인 대사 정책은 후속 작업이다.

## L4 Fallback
모델 미설정, 예외/timeout, 형식 오류이면 동일한 공개 단서를 쓰는 중립 안내로 대체한다.
오류를 억지로 연기하지 않으며 stance=evidence_guidance로 전환한다.
서버가 supported로 확인한 feedback에서만 acknowledge를 유지한다.
원본 모델 응답·예외 메시지·숨은 정답을 출력/로그로 노출하지 않는다.
hint는 FE-api-contract의 {level,text,source:"rule"|"llm"} 형식에 맞춘다.
외부 envelope의 source/is_fallback은 서버가 작성하고 LLM 출력에 맡기지 않는다.
잘못된 Backend Context는 Provider 호출 전에 거부한다. 이런 경우 게임 상태를 복구해야 하므로
안전하지 않은 Context를 이용해 폴백하지 않는다.

## 진행 상태
L2/L3/L4의 독립 구현 및 14개 테스트 완료. 실제 LLM·게임 HTTP API·프런트 연동,
화면상 폴백 배지 표시는 미완료다. API 담당과 공개 Context 구성·단서 정책을 합의한 후 연결한다.
코드 커밋·푸시·배포는 수행하지 않았다.
