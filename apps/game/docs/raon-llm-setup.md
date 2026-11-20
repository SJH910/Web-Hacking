# 라온 LLM 연결 (Ollama) — 설정·구조

게임 안내자 **라온**의 대사를 로컬 LLM으로 생성하는 선택적 기능. **기본은 꺼짐**(고정 대사). 포트·모델명만 주면 켜진다.

- 어댑터: `tools/vulnscan/raon_llm.py` (vulnscan `llm_review.py`와 같은 I/O 계층)
- 훅: `tools/vulnscan/scanner.py` 게임 API 응답 후처리
- 설계 기준: `apps/game/llm-backend-note.md`(로컬 메모), 신뢰도→힌트 품질은 `scoring-trust.md`(G4)
- 관련 태스크: **L2**(컨텍스트 스키마)·**L3**(응답 검증)·**L4**(규칙 기반 폴백)

## 원칙 (지켜지는 것)

- **판정은 라온이 안 한다.** 정답·점수·플래그는 전부 `game_engine`(X1). 라온은 **대사만** 만든다.
- **모델 없으면 고정 대사 폴백.** 모델 다운·형식 불일치 시 기존 `allyOpening`/힌트를 그대로 쓴다. 모델은 블로커가 아니다.
- **로컬·무과금.** OpenAI 호환 `127.0.0.1` 루프백만. **클라우드 API 금지**(외부 전송·과금).
- **데이터 경계.** 모델에 넘기는 것: 층·목표·공개된 증거·신뢰도·라온의 (틀린) 입장. **정답·채점 로직·정답 보기·플래그는 보내지 않는다**(state 뷰에 애초에 없음). 테스트로 강제: `test_raon_llm.py::test_data_boundary`.

## 켜는 법 — Ollama (대안·무과금)

Ollama는 설치돼 있어야 한다(serve·모델 pull은 아래).

```bash
# 1) Ollama 데몬 실행 (별도 터미널)
ollama serve

# 2) 모델 받기 (한 번만)
ollama pull llama3            # 또는 qwen2.5 등

# 3) 스캐너를 라온 LLM과 함께 실행
python3 tools/vulnscan/scanner.py --game-llm-port 11434 --game-llm-model llama3
```

- 켜지면 기동 로그에 `라온 LLM: 127.0.0.1:11434 · 모델 llama3 (실패 시 고정 대사 폴백)` 표시.
- `--game-llm-port`를 **주지 않으면** 라온은 고정 대사만 쓴다(현재 기본 동작).

## 모델 교체 = 포트·모델명만

| 백엔드 | 실행 | 플래그 |
|---|---|---|
| Ollama(기본 대안) | `ollama serve` + `ollama pull <모델>` | `--game-llm-port 11434 --game-llm-model llama3` |
| 자체 모델(from-scratch) | `local_model.py`로 OpenAI 호환 서버 기동 | `--game-llm-port 8910 --game-llm-model local-gpt2` |

엔드포인트는 둘 다 `POST /v1/chat/completions`. 어댑터 코드 수정 없이 플래그만 바꾼다.

## 동작 요약

- **첫마디(allyOpening):** 문제의 "의도적으로 틀린 입장"을 라온 말투로 다시 씀(틀린 방향 유지 → 함정 설계 보존). 성공 시 `allySource: "llm"` 표시, 실패 시 고정 대사.
- **힌트:** 신뢰도 구간별 품질 — `≥80 clear / 50~79 mixed / <50 weak`. 성공 시 `source: "llm"`, 실패 시 `source: "rule"`.
- **캐시:** 같은 (등반·층)의 첫마디는 1회만 생성(요청마다 재호출 안 함).

## 검증

```bash
cd tools/vulnscan && python3 -B -m unittest test_raon_llm -v
# 폴백/성공/데이터 경계/캐시 8종. 외부 네트워크 없이 로컬 목 서버로 검증.
```

## 남은 일 (L 담당)

- 라온 성격·말투 프롬프트 다듬기(L1), 응답 스키마에 근거·확신도 명시(L3 심화), 프롬프트 주입·정답 노출 방어 테스트(L5).
- 신뢰도 구간별 **고정 대사 3단 세트**(폴백 품질 차등) 콘텐츠(L4·L7 연계).
