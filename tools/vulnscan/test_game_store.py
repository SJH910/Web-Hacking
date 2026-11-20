"""B5·B6 저장·랭킹 검사: 서버 재시작 후 복원, 랭킹 정렬·중복 방지."""
import os
import tempfile
import unittest

import game_problems
from game_engine import Games
from game_model import load_pool
from game_store import Store
from test_game_engine import pick_problem, rid


def make(path):
    pool = load_pool([game_problems.NIGHT_LOG, pick_problem()])
    return Games(pool, lambda s, p: ["night-log", "pick"], Store(path))


def post(g, run, action, rev, **body):
    return g.handle("POST", ["runs", run, action], {"revision": rev, "requestId": rid(), **body})


class StoreTest(unittest.TestCase):
    def test_restart_restores_state(self):
        with tempfile.TemporaryDirectory() as d:
            path = os.path.join(d, "g.db")
            g = make(path)
            state = g.handle("POST", ["runs"], {"requestId": "create-req-1"})[1]["state"]
            run = state["runId"]
            st = post(g, run, "commands", 0, command="count 10.0.0.9")[1]["state"]
            st = post(g, run, "hints", st["revision"])[1]["state"]
            g.store.db.close()
            g2 = make(path)  # 재시작
            back = g2.handle("GET", ["runs", run], {})[1]["state"]
            self.assertEqual(back, st)
            self.assertEqual((back["seed"], back["totalHints"], back["trust"]), (state["seed"], 1, 59))
            # 같은 create requestId는 같은 등반을 돌려준다
            self.assertEqual(g2.handle("POST", ["runs"], {"requestId": "create-req-1"})[1]["state"]["runId"], run)
            # 복원 후에도 이어서 진행
            self.assertEqual(post(g2, run, "commands", back["revision"], command="cat gate.conf")[0], 200)
            g2.store.db.close()  # Windows는 열린 파일을 지울 수 없다

    def test_ranking_order_and_dedupe(self):
        g = make(":memory:")
        for name, wrong in (("느림", 1), ("빠름", 0)):
            run = g.handle("POST", ["runs"], {"requestId": rid()})[1]["state"]["runId"]
            rev = 0
            for floor_cmds in (("count 10.0.0.9", "cat gate.conf"), None):
                if floor_cmds:
                    for c in floor_cmds:
                        rev = post(g, run, "commands", rev, command=c)[1]["state"]["revision"]
                else:
                    rev = post(g, run, "evidence", rev, evidenceIds=["E01", "E03"])[1]["state"]["revision"]
                for step, cid in (("classify", "c1"), ("verdict", "v2"), ("action", "a1")):
                    if wrong and step == "action" and floor_cmds:
                        rev = post(g, run, "answers", rev, step=step, choiceId="a3")[1]["state"]["revision"]
                    rev = post(g, run, "answers", rev, step=step, choiceId=cid)[1]["state"]["revision"]
                if floor_cmds:
                    rev = post(g, run, "next", rev)[1]["state"]["revision"]
            self.assertEqual(post(g, run, "ranking", rev, name=name)[0], 200)
            self.assertEqual(post(g, run, "ranking", rev + 0)[0], 409)
        ranks = g.handle("GET", ["rankings"], {})[1]
        self.assertEqual([r["name"] for r in ranks], ["빠름", "느림"])
        self.assertEqual([r["rank"] for r in ranks], [1, 2])
        self.assertGreater(ranks[0]["score"], ranks[1]["score"])


if __name__ == "__main__":
    unittest.main()
