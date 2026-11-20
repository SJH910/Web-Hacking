"""B2 탐색+판정 엔진 검사. 메모리 안에서만 동작한다."""
import copy
import itertools
import unittest

import game_problems
from game_engine import Games
from game_model import load_pool

_n = itertools.count(1)


def pick_problem():
    d = copy.deepcopy(game_problems.NIGHT_LOG)
    d.update(id="pick", title="증거 고르기", type="choice", requiredIds=["E01", "E03"])
    del d["commands"], d["requiredActions"]
    return d


def rid():
    return f"req-{next(_n):08d}"


class Flow:
    def __init__(self):
        pool = load_pool([game_problems.NIGHT_LOG, pick_problem()])
        self.g = Games(pool, lambda seed, p: ["night-log", "pick"])
        _, r = self.g.handle("POST", ["runs"], {"requestId": rid()})
        self.s = r["state"]

    def post(self, action, **body):
        st, r = self.g.handle("POST", ["runs", self.s["runId"], action], {"revision": self.s["revision"], "requestId": rid(), **body})
        if st == 200:
            self.s = r["state"]
        return st, r

    def ans(self, step, cid):
        return self.post("answers", step=step, choiceId=cid)[1]


class EngineTest(unittest.TestCase):
    def test_full_run(self):
        f = Flow()
        self.assertFalse(f.s["canJudge"])
        self.assertIsNone(f.s["step"])
        self.assertEqual(f.post("answers", step="classify", choiceId="c1")[0], 409)  # 조사 전 판정 거부
        # 차단 명령: 출력만 있고 상태 불변
        rev = f.s["revision"]
        self.assertEqual(f.post("commands", command="rm -rf /")[1]["output"], "허용되지 않은 명령입니다.")
        self.assertEqual(f.s["revision"], rev)
        # 한 그룹만 채우면 아직 판정 불가, 다른 그룹까지 채우면 가능(대소문자·공백 정규화)
        f.post("commands", command="  COUNT   10.0.0.9 ")
        self.assertFalse(f.s["canJudge"])
        f.post("commands", command="cat gate.conf")
        self.assertTrue(f.s["canJudge"])
        self.assertEqual({e["number"] for e in f.s["evidence"]}, {"E01", "E03"})
        self.assertEqual(set(f.s["step"]), {"key", "question", "choices"})
        self.assertTrue(all(set(c) == {"id", "label"} for c in f.s["step"]["choices"]))
        # 함정 → 신뢰도 -5, 오답 1; 같은 단계 재시도로 정답(단계점 5)
        r = f.ans("classify", "c2")
        self.assertEqual((r["correct"], f.s["trust"], f.s["totalWrong"]), (False, 55, 1))
        self.assertEqual(f.post("answers", step="verdict", choiceId="v2")[0], 409)  # 현재 단계 아님
        self.assertTrue(f.ans("classify", "c1")["correct"])
        f.ans("verdict", "v2")
        r = f.ans("action", "a1")
        self.assertEqual((f.s["cleared"], f.s["score"], f.s["trust"], f.s["flag"]), (True, 25, 59, "FLAG{floor1_unlogged_bruteforce}"))
        self.assertIn("차단", r["feedback"] + "차단")
        # 통과 후 다음 층: 선택형
        self.assertEqual(f.post("next")[0], 200)
        self.assertEqual((f.s["floor"], f.s["problem"]["type"], f.s["progress"], f.s["hints"]), (2, "choice", 0, []))
        self.assertEqual(len(f.s["evidence"]), 3)
        self.assertFalse(f.post("evidence", evidenceIds=["E01"])[1]["correct"])
        self.assertFalse(f.s["canJudge"])
        self.assertTrue(f.post("evidence", evidenceIds=["E03", "E01"])[1]["correct"])
        for step, cid in (("classify", "c1"), ("verdict", "v2"), ("action", "a1")):
            f.ans(step, cid)
        # 무오답·무힌트 쉬움: 30 + 5 = 35 → 총 60, 마지막 층이라 엔딩
        self.assertEqual((f.s["score"], f.s["trust"]), (60, 65))
        self.assertEqual(f.s["ending"], {"title": "냉철한 등반가", "narrative": f.s["ending"]["narrative"], "badges": ["침묵의 등반"], "bonus": 0})
        self.assertEqual(f.post("next")[0], 409)  # 마지막 층 다음 없음
        self.assertEqual(f.post("ranking", name="  테스터 ")[0], 200)
        self.assertEqual(f.post("ranking")[0], 409)  # 중복 등록
        _, ranks = f.g.handle("GET", ["rankings"], {})
        self.assertEqual(ranks, [{"rank": 1, "name": "테스터", "floor": 2, "score": 60, "trust": 65, "hints": 0}])

    def test_hints_cost_and_limit(self):
        f = Flow()
        for level in (1, 2, 3):
            f.post("hints")
            self.assertEqual(len(f.s["hints"]), level)
        self.assertEqual((f.s["trust"], f.s["totalHints"]), (57, 3))
        rev = f.s["revision"]
        self.assertIn("없습니다", f.post("hints")[1]["feedback"])  # 4번째: 감점·변화 없음
        self.assertEqual((f.s["trust"], f.s["revision"]), (57, rev))

    def test_revision_and_idempotency(self):
        f = Flow()
        old = dict(f.s)
        f.post("hints")
        st, _ = f.g.handle("POST", ["runs", old["runId"], "hints"], {"revision": old["revision"], "requestId": rid()})
        self.assertEqual(st, 409)  # 오래된 revision
        req = rid()
        body = {"revision": f.s["revision"], "requestId": req}
        first = f.g.handle("POST", ["runs", old["runId"], "hints"], body)
        again = f.g.handle("POST", ["runs", old["runId"], "hints"], body)
        self.assertEqual(first, again)  # 같은 requestId는 재처리하지 않음
        self.assertEqual(again[1]["state"]["totalHints"], 2)

    def test_bad_input(self):
        f = Flow()
        run = f.s["runId"]
        h = f.g.handle
        self.assertEqual(h("GET", ["runs", "nope"], {})[0], 404)
        self.assertEqual(h("POST", ["runs"], {})[0], 400)
        self.assertEqual(h("POST", ["runs", run, "commands"], {"requestId": "x", "revision": 0})[0], 400)
        self.assertEqual(h("POST", ["runs", run, "commands"], {"requestId": rid(), "revision": "0"})[0], 400)
        self.assertEqual(f.post("commands", command="a" * 500)[0], 400)
        self.assertEqual(f.post("commands", command=5)[0], 400)
        self.assertEqual(f.post("evidence", evidenceIds=["E01"])[0], 409)  # 터미널 문제에 증거 선택
        self.assertEqual(h("POST", ["runs", run, "bogus"], {})[0], 404)
        self.assertEqual(f.g.handle("POST", ["runs"], {"requestId": "same-req-1"})[1]["state"]["runId"],
                         f.g.handle("POST", ["runs"], {"requestId": "same-req-1"})[1]["state"]["runId"])

    def test_no_answers_leak(self):
        f = Flow()
        f.post("commands", command="count 10.0.0.9")
        f.post("commands", command="diff attempts logged")
        import json
        blob = json.dumps(f.s, ensure_ascii=False)
        for secret in ("correct", "isTrap", "FLAG{", "lockout"):
            self.assertNotIn(secret, blob)


if __name__ == "__main__":
    unittest.main()


class LimitTest(unittest.TestCase):
    def test_rate_limit(self):
        pool = load_pool([game_problems.NIGHT_LOG])
        g = Games(pool, lambda s, p: ["night-log"], limits=((5, 60), (2, 60)))
        codes = [g.handle("GET", ["rankings"], {}, "1.1.1.1")[0] for _ in range(7)]
        self.assertEqual(codes, [200] * 5 + [429] * 2)
        self.assertEqual(g.handle("GET", ["rankings"], {}, "2.2.2.2")[0], 200)  # 다른 클라이언트는 영향 없음

    def test_create_limit(self):
        g = Games(load_pool([game_problems.NIGHT_LOG]), lambda s, p: ["night-log"], limits=((100, 60), (2, 60)))
        codes = [g.handle("POST", ["runs"], {"requestId": rid()}, "9.9.9.9")[0] for _ in range(3)]
        self.assertEqual(codes, [200, 200, 429])

    def test_boundaries(self):
        f = Flow()
        self.assertEqual(f.post("commands", command="a" * 200)[0], 200)  # 상한 정확히
        self.assertEqual(f.post("commands", command="a" * 201)[0], 400)
        self.assertEqual(f.g.handle("GET", ["runs", "../etc", "x", "y", "z"], {})[0], 404)
        self.assertEqual(f.g.handle("GET", ["runs", "a b"], {})[0], 404)


class EndingTest(unittest.TestCase):
    def test_six_ending_boundaries(self):
        g = Games(load_pool([game_problems.NIGHT_LOG]), lambda s, p: ["night-log"])
        cases = {(80, 3): ("공명(共鳴)", 20), (80, 4): ("우직한 동행", 20), (79, 3): ("냉철한 등반가", 0), (40, 4): ("무명(無名)의 등정", 0),
                 (39, 3): ("고독한 해결사", 0), (0, 4): ("홀로 오른 탑", 0)}
        for (trust, wrong), (title, bonus) in cases.items():
            r = {"trust": trust, "wrong": wrong, "hints": 1, "banked": 100}
            g._finish(r)
            self.assertEqual((r["ending"]["title"], r["ending"]["bonus"], r["banked"]), (title, bonus, 100 + bonus), (trust, wrong))
        r = {"trust": 60, "wrong": 0, "hints": 0, "banked": 0}
        g._finish(r)
        self.assertEqual(r["ending"]["badges"], ["무결", "침묵의 등반"])
