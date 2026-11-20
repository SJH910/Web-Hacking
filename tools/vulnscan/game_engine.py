"""용범의 탑 탐색+판정 엔진(B2). 정답·명령 출력·점수는 전부 서버가 계산한다(X1).

점수·신뢰도: scoring-trust.md(G4), 엔딩: ending-branches.md(G7), HTTP 계약: apps/game/docs/FE-api-contract.md.
저장은 메모리뿐이다(B5에서 영속화). 외부 요청·실제 명령 실행은 없다: 입력은 화이트리스트 정규식과 비교만 한다.
"""
import re
import secrets
import threading
import time
from collections import deque

from game_order import make_order
from game_problems import POOL
from game_store import Store

STEP_BASE = {"쉬움": 10, "보통": 15, "어려움": 20}
WRONG_PENALTY, STEP_MIN, HINT_PENALTY, CLEAN_BONUS = 5, 2, 3, 5
TRUST_START, TRUST_CLEAN, TRUST_TRAP, TRUST_WRONG, TRUST_HINT = 60, 2, -5, -2, -1
HIGH_TRUST_BONUS = 20
MAX_CACHE, MAX_CMD, MAX_PARTS = 20, 200, 4
RUN_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
_RID = re.compile(r"^[A-Za-z0-9-]{8,64}$")
BLOCKED = "허용되지 않은 명령입니다."

ENDINGS = {  # (신뢰도 구간, 정확도) → (칭호, 서사)
    ("high", "precise"): ("공명(共鳴)", "라온이 틀릴 때마다 너는 증거로 바로잡았고, 라온은 조금씩 너를 닮아갔다. 의심과 믿음을 같은 손에 쥔 자만이 이 정상에 선다."),
    ("high", "struggle"): ("우직한 동행", "매 층 비틀거렸지만 그때마다 라온이 손을 내밀었고 너는 그 손을 증거로 되잡았다. 서툴러도 끝까지 곁을 지킨 등반이었다."),
    ("mid", "precise"): ("냉철한 등반가", "증거만 믿고 한 걸음씩. 라온의 말은 참고였을 뿐, 판단은 끝까지 네 몫이었다."),
    ("mid", "struggle"): ("무명(無名)의 등정", "틀리면 다시 서고 막히면 돌아온 이름 없는 발걸음. 누구였는지가 아니라 끝까지 올랐다는 것만이 남는다."),
    ("low", "precise"): ("고독한 해결사", "라온을 믿지 않았다. 그럼에도 틀리지 않았다. 외롭지만 날카로운 등반."),
    ("low", "struggle"): ("홀로 오른 탑", "라온의 말에 휘둘리다 멀어졌고, 힘겹게 혼자 올랐다. 다음엔 증거를 먼저 보게 될까."),
}


class ApiError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status, self.message = status, message


class RateLimiter:
    """키(클라이언트)별 고정 윈도 제한. shortcut: 프로세스 메모리 기준, 다중 프로세스면 공유 저장소로 옮긴다."""

    def __init__(self, limit, window):
        self.limit, self.window, self.hits = limit, window, {}

    def allow(self, key, now=None):
        now = time.monotonic() if now is None else now
        if len(self.hits) > 5000:
            self.hits.clear()
        q = self.hits.setdefault(key, deque())
        while q and now - q[0] >= self.window:
            q.popleft()
        if len(q) >= self.limit:
            return False
        q.append(now)
        return True


def _clamp(v, lo, hi):
    return max(lo, min(hi, v))


def _new_floor():
    return {"ran": [], "sel_ok": False, "wrong": [0, 0, 0], "hints": 0, "points": []}


class Games:
    def __init__(self, pool=None, order_fn=make_order, store=None, limits=((60, 10), (10, 60))):
        self.pool, self.order_fn = pool or POOL, order_fn
        self.store = store or Store()
        self.rate, self.rate_create = RateLimiter(*limits[0]), RateLimiter(*limits[1])
        self.lock = threading.Lock()

    # ---- 상태 뷰(정답·명령·해설 미포함) ----
    def _problem(self, r):
        return self.pool[r["order"][r["floor"] - 1]]

    def _can_judge(self, r, p):
        f = r["f"]
        if p.type == "terminal":
            return all(any(k in f["ran"] for k in g.split("|")) for g in p.required_actions)
        return f["sel_ok"]

    def _score(self, r):
        f = r["f"]
        return r["banked"] + max(0, sum(f["points"]) - HINT_PENALTY * f["hints"]) if not r["cleared"] else r["banked"]

    def _view(self, r):
        p, f = self._problem(r), r["f"]
        can = self._can_judge(r, p)
        if p.type == "terminal":
            shown = {n for c in p.commands if c.key in f["ran"] for n in c.reveals}
            evidence = [e for e in p.evidence if e.number in shown]
        else:
            evidence = list(p.evidence)
        progress = len(f["points"])
        step = None
        if can and not r["cleared"]:
            s = p.steps[progress]
            step = {"key": s.key, "question": s.question, "choices": [{"id": c.id, "label": c.label} for c in s.choices]}
        state = {
            "runId": r["id"], "revision": r["rev"], "seed": r["seed"], "floor": r["floor"], "score": self._score(r),
            "trust": r["trust"], "progress": progress, "cleared": r["cleared"], "canJudge": can,
            "totalWrong": r["wrong"], "totalHints": r["hints"],
            "problem": {"id": p.id, "title": p.title, "type": p.type, "difficulty": p.difficulty,
                        "objective": p.objective, "allyOpening": p.ally_opening},
            "evidence": [{"number": e.number, "title": e.title, "detail": e.detail, "tag": e.tag} for e in evidence],
            "step": step,
            "hints": [{"level": h.level, "text": h.text, "source": "rule"} for h in p.hints[:f["hints"]]],
        }
        if r["cleared"]:
            state["flag"] = p.flag
        if r["ending"]:
            state["ending"] = r["ending"]
        return state

    # ---- 공통 ----
    def _run(self, run_id):
        r = self.store.get_run(run_id) if RUN_ID.match(run_id) else None
        if r is None:
            raise ApiError(404, "등반을 찾을 수 없습니다.")
        return r

    def _guard(self, r, body):
        rid, rev = body.get("requestId"), body.get("revision")
        if not isinstance(rid, str) or not _RID.match(rid):
            raise ApiError(400, "requestId가 올바르지 않습니다.")
        if type(rev) is not int:
            raise ApiError(400, "revision이 올바르지 않습니다.")
        if rid in r["seen"]:
            return r["seen"][rid]
        if rev != r["rev"]:
            raise ApiError(409, "상태가 오래되었습니다. 다시 불러오세요.")
        return None

    def _done(self, r, body, result, changed=True):
        if changed:
            r["rev"] += 1
        result["state"] = self._view(r)
        r["seen"][body["requestId"]] = result
        while len(r["seen"]) > MAX_CACHE:
            del r["seen"][next(iter(r["seen"]))]
        self.store.put_run(r)
        return result

    # ---- 동작 ----
    def create(self, body):
        rid = body.get("requestId")
        if not isinstance(rid, str) or not _RID.match(rid):
            raise ApiError(400, "requestId가 올바르지 않습니다.")
        known = self.store.get_create(rid)
        if known and (r := self.store.get_run(known)):
            return {"state": self._view(r)}
        seed = "seed_" + secrets.token_hex(4)
        order = self.order_fn(seed, self.pool)
        r = {"id": secrets.token_urlsafe(12), "seed": seed, "order": order, "floor": 1, "rev": 0, "banked": 0,
             "trust": TRUST_START, "wrong": 0, "hints": 0, "cleared": False, "ending": None, "ranked": False,
             "f": _new_floor(), "seen": {}}
        self.store.put_run(r)
        self.store.put_create(rid, r["id"])
        return {"state": self._view(r)}

    def command(self, r, body):
        p = self._problem(r)
        if p.type != "terminal":
            raise ApiError(409, "이 문제는 명령 탐색을 쓰지 않습니다.")
        raw = body.get("command")
        if not isinstance(raw, str) or len(raw) > MAX_CMD:
            raise ApiError(400, "command가 올바르지 않습니다.")
        text = " ".join(raw.split()).lower()
        for c in p.commands:
            if c.pattern.fullmatch(text):
                new = c.key not in r["f"]["ran"]
                if new:
                    r["f"]["ran"].append(c.key)
                return self._done(r, body, {"output": c.output}, changed=new)
        return self._done(r, body, {"output": BLOCKED}, changed=False)

    def evidence(self, r, body):
        p = self._problem(r)
        if p.type != "choice":
            raise ApiError(409, "이 문제는 증거 선택을 쓰지 않습니다.")
        ids = body.get("evidenceIds")
        known = {e.number for e in p.evidence}
        if not isinstance(ids, list) or not all(isinstance(i, str) for i in ids) or not set(ids) <= known:
            raise ApiError(400, "evidenceIds가 올바르지 않습니다.")
        ok = set(ids) == set(p.required_ids) and len(ids) == len(set(ids))
        r["f"]["sel_ok"] = ok
        fb = "핵심 증거를 찾았습니다. 판정으로 넘어가세요." if ok else "선택한 증거로는 아직 결론을 내리기 어렵습니다."
        return self._done(r, body, {"feedback": fb, "correct": ok})

    def answer(self, r, body):
        p, f = self._problem(r), r["f"]
        if r["cleared"] or not self._can_judge(r, p):
            raise ApiError(409, "먼저 기록을 조사하세요.")
        i = len(f["points"])
        s = p.steps[i]
        if body.get("step") != s.key:
            raise ApiError(409, "현재 단계가 아닙니다. 다시 불러오세요.")
        choice = next((c for c in s.choices if c.id == body.get("choiceId")), None)
        if choice is None:
            raise ApiError(400, "choiceId가 올바르지 않습니다.")
        if not choice.correct:
            f["wrong"][i] += 1
            r["wrong"] += 1
            r["trust"] = _clamp(r["trust"] + (TRUST_TRAP if choice.is_trap else TRUST_WRONG), 0, 100)
            fb = "라온의 말을 그대로 따랐습니다. 증거를 다시 확인하세요." if choice.is_trap else "증거를 다시 확인하세요."
            return self._done(r, body, {"feedback": fb, "correct": False})
        f["points"].append(max(STEP_MIN, STEP_BASE[p.difficulty] - WRONG_PENALTY * f["wrong"][i]))
        if f["wrong"][i] == 0:
            r["trust"] = _clamp(r["trust"] + TRUST_CLEAN, 0, 100)
        if len(f["points"]) == len(p.steps):
            clean = sum(f["wrong"]) == 0 and f["hints"] == 0
            r["banked"] += max(0, sum(f["points"]) - HINT_PENALTY * f["hints"] + (CLEAN_BONUS if clean else 0))
            r["cleared"] = True
            if r["floor"] == len(r["order"]):
                self._finish(r)
        return self._done(r, body, {"feedback": s.why, "correct": True})

    def _finish(self, r):
        bonus = HIGH_TRUST_BONUS if r["trust"] >= 80 else 0
        r["banked"] += bonus
        tier = "high" if r["trust"] >= 80 else "mid" if r["trust"] >= 40 else "low"
        title, narrative = ENDINGS[(tier, "precise" if r["wrong"] <= 3 else "struggle")]
        badges = (["무결"] if r["wrong"] == 0 else []) + (["침묵의 등반"] if r["hints"] == 0 else [])
        r["ending"] = {"title": title, "narrative": narrative, "badges": badges, "bonus": bonus}

    def hint(self, r, body):
        p, f = self._problem(r), r["f"]
        if r["cleared"] or f["hints"] >= len(p.hints):
            return self._done(r, body, {"feedback": "더 받을 수 있는 힌트가 없습니다."}, changed=False)
        f["hints"] += 1
        r["hints"] += 1
        r["trust"] = _clamp(r["trust"] + TRUST_HINT, 0, 100)
        return self._done(r, body, {})

    def next(self, r, body):
        if not r["cleared"] or r["floor"] >= len(r["order"]):
            raise ApiError(409, "다음 층으로 갈 수 없습니다.")
        r["floor"] += 1
        r["cleared"] = False
        r["f"] = _new_floor()
        return self._done(r, body, {})

    def ranking(self, r, body):
        if not (r["cleared"] and r["floor"] == len(r["order"])):
            raise ApiError(409, "모든 층을 통과해야 등록할 수 있습니다.")
        if r["ranked"]:
            raise ApiError(409, "이미 등록되었습니다.")
        r["ranked"] = True
        name = body.get("name")
        name = " ".join(name.split())[:20] if isinstance(name, str) and name.strip() else "등반가-" + r["id"][:4]
        self.store.add_rank(r["id"], name, r["floor"], r["banked"], r["trust"], r["hints"])
        return self._done(r, body, {"feedback": "랭킹에 등록했습니다."}, changed=False)

    def rankings(self):
        return self.store.top_ranks(100)

    # ---- HTTP 진입점: (상태코드, JSON 객체) ----
    def handle(self, method, parts, body, client=""):
        """parts = '/api/game/' 이후 경로 조각. client = 요청 제한 키(보통 IP)."""
        try:
            with self.lock:
                if len(parts) > MAX_PARTS:
                    raise ApiError(404, "not found")
                if not self.rate.allow(client) or (method == "POST" and parts == ["runs"] and not self.rate_create.allow(client)):
                    raise ApiError(429, "요청이 너무 많습니다. 잠시 후 다시 시도하세요.")
                if method == "GET" and parts == ["rankings"]:
                    return 200, self.rankings()
                if method == "POST" and parts == ["runs"]:
                    return 200, self.create(body)
                if len(parts) >= 2 and parts[0] == "runs":
                    r = self._run(parts[1])
                    if method == "GET" and len(parts) == 2:
                        return 200, {"state": self._view(r)}
                    action = {"commands": self.command, "evidence": self.evidence, "answers": self.answer,
                              "hints": self.hint, "next": self.next, "ranking": self.ranking}.get(parts[2] if len(parts) == 3 else "")
                    if method == "POST" and action:
                        return 200, self._guard(r, body) or action(r, body)
                raise ApiError(404, "not found")
        except ApiError as e:
            return e.status, {"error": e.message}


GAMES = Games()
