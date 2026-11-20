"""용범의 탑 '라온' LLM 어댑터 (L2~L4). 선택적·로컬 전용.

라온은 판정하지 않는다(X1: 판정·점수·정답은 전부 game_engine). 이 모듈은 라온의 '대사'만 만든다.
  - 의도적으로 틀린 첫마디(allyOpening)를 라온 말투로 다시 쓴다(틀린 방향은 유지).
  - 힌트 텍스트를 신뢰도 구간별 품질로 전달한다(≥80 clear / 50~79 mixed / <50 weak — scoring-trust.md G4).
모델이 없거나 응답 형식이 맞지 않으면 None을 돌려, 호출부가 고정 대사(폴백)를 그대로 쓴다. 모델은 블로커가 아니다.

모델 교체 = 포트·모델명만 (vulnscan llm_review.py와 동일 패턴):
  - OpenAI 호환 로컬 엔드포인트 127.0.0.1:<port> 로 POST /v1/chat/completions.
  - 기본 자체 모델, 대안 Ollama(llama3·qwen2.5 등, 127.0.0.1:11434). 클라우드 API 금지(외부 전송·과금).

데이터 경계(최소 전달): 층·목표·공개된 증거·신뢰도·라온의 (틀린) 입장만 보낸다.
정답·채점 로직·정답 보기·플래그는 보내지 않는다(state 뷰에 애초에 없음 — game_engine._view 참고).
"""
import http.client
import json
import threading

MAX_CHARS = 280          # 대사 길이 상한(폭주 방지)
MAX_CACHE = 2000         # (runId, floor[, level])별 1회만 생성하도록 캐시

SYSTEM = (
    "너는 '라온'이다. 용범의 탑을 함께 오르는 안내자지만 완벽하지 않다. "
    "너는 판정하지 않는다. 정답을 단정하지 말고, 주어진 '입장'의 방향을 유지해라. "
    "한국어로 1~2문장, 캐릭터 말투로만 답하라. 메타 설명·따옴표·목록·머리말 금지."
)

_TONE = {
    "clear": "분명하고 구체적으로",
    "mixed": "절반쯤 모호하게, 방향만 살짝",
    "weak": "희미하고 에둘러서",
}


def trust_tier(trust):
    """신뢰도 → 힌트 품질 구간 (G4)."""
    try:
        t = int(trust)
    except (TypeError, ValueError):
        t = 60
    return "clear" if t >= 80 else "mixed" if t >= 50 else "weak"


class RaonClient:
    """OpenAI 호환 로컬 엔드포인트 뒤의 모델로 라온 대사를 생성한다. 실패 시 None."""

    def __init__(self, port, model="llama3", timeout=20):
        self.port, self.model, self.timeout = port, model, timeout
        self._cache = {}
        self._lock = threading.Lock()

    def _chat(self, user):
        payload = {
            "model": self.model,
            "messages": [{"role": "system", "content": SYSTEM},
                         {"role": "user", "content": user}],
            "max_tokens": 120,
            "temperature": 0.7,
            "stream": False,
        }
        conn = http.client.HTTPConnection("127.0.0.1", self.port, timeout=self.timeout)
        try:
            conn.request("POST", "/v1/chat/completions", json.dumps(payload),
                         {"Content-Type": "application/json"})
            resp = conn.getresponse()
            if resp.status != 200:
                return None
            data = json.loads(resp.read(65536))
            text = data["choices"][0]["message"]["content"]
            if not isinstance(text, str):
                return None
            text = " ".join(text.split())[:MAX_CHARS]
            return text or None
        except (OSError, http.client.HTTPException, ValueError, KeyError, IndexError, TypeError):
            return None
        finally:
            conn.close()

    def _once(self, key, build_user):
        """같은 키는 한 번만 모델 호출. 실패(None)도 캐시해 매 요청 재호출을 막는다."""
        with self._lock:
            if key in self._cache:
                return self._cache[key]
        text = self._chat(build_user())
        with self._lock:
            if len(self._cache) > MAX_CACHE:
                self._cache.clear()
            self._cache[key] = text
        return text

    def opening(self, state):
        p = state.get("problem", {})
        floor = state.get("floor")

        def build():
            ev = "; ".join(f"{e.get('title')}: {e.get('detail')}"
                           for e in state.get("evidence", [])[:4])
            return (f"[{floor}층] 목표: {p.get('objective', '')}\n"
                    f"관찰된 증거: {ev or '아직 없음'}\n"
                    f"라온의 입장(이 방향을 유지, 단정 금지): {p.get('allyOpening', '')}\n"
                    "이 입장을 라온의 말투로 다시 한마디.")

        return self._once(("open", state.get("runId"), floor), build)

    def hint(self, state, level, base_text):
        tier = trust_tier(state.get("trust", 60))

        def build():
            return (f"[{state.get('floor')}층] 전하려는 힌트 내용: {base_text}\n"
                    f"신뢰도 상태: {tier}. {_TONE[tier]} 전달하되 정답을 직접 말하지 마라. 1문장.")

        return self._once(("hint", state.get("runId"), state.get("floor"), level), build)

    def rephrase_hint(self, base_text, tier="mixed"):
        """힌트 1건을 신뢰도 구간 톤으로 윤문(캐시 없음). 레드팀 등 단건 힌트용."""
        user = (f"전하려는 힌트 내용: {base_text}\n"
                f"신뢰도 상태: {tier}. {_TONE.get(tier, _TONE['mixed'])} 전달하되 정답을 직접 말하지 마라. 1문장.")
        return self._chat(user)


def decorate(client, obj):
    """state를 가진 응답에 라온 LLM 대사를 입힌다. 생성 실패분은 고정 대사를 유지한다.

    - allyOpening: LLM 성공 시 교체하고 allySource='llm' 표시(실패 시 그대로, source 미표시).
    - hints: 가장 최근(마지막) 힌트 텍스트만 신뢰도 구간 품질로 교체, source='llm'.
    판정·점수·플래그 등 state의 다른 필드는 건드리지 않는다.
    """
    if not client or not isinstance(obj, dict):
        return obj
    state = obj.get("state")
    if not isinstance(state, dict) or state.get("cleared"):
        return obj
    p = state.get("problem")
    if isinstance(p, dict) and p.get("allyOpening"):
        text = client.opening(state)
        if text:
            p["allyOpening"] = text
            p["allySource"] = "llm"
    hints = state.get("hints")
    if isinstance(hints, list) and hints:
        last = hints[-1]
        text = client.hint(state, last.get("level"), last.get("text", ""))
        if text:
            last["text"] = text
            last["source"] = "llm"
    return obj


def decorate_redteam(client, obj):
    """레드팀 응답에 라온 LLM 대사를 입힌다(응답 형태가 블루팀과 달라 별도 처리).

    - 챌린지 시작(floor_start): 최상위 allyOpening(의도적 틀린 첫마디)을 윤문.
    - 힌트 응답: 최상위 text(단건 힌트)를 윤문. 실패 시 고정 대사 유지.
    정답·flag·html 등 다른 필드는 건드리지 않는다.
    """
    if not client or not isinstance(obj, dict):
        return obj
    if obj.get("allyOpening"):
        state = {"runId": obj.get("challengeId", "rt"), "floor": obj.get("floor", 1), "trust": 60,
                 "problem": {"objective": obj.get("title", ""), "allyOpening": obj["allyOpening"]},
                 "evidence": []}
        text = client.opening(state)
        if text:
            obj["allyOpening"] = text
            obj["allySource"] = "llm"
    if isinstance(obj.get("text"), str) and obj.get("text"):
        text = client.rephrase_hint(obj["text"])
        if text:
            obj["text"] = text
            obj["source"] = "llm"
    return obj
