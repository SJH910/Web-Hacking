"""B4 안전 경계 + 풀 전체 풀이 가능성 검사. 네트워크·실행 없음(소켓은 오히려 막고 검사)."""
import ast
import re
import socket
import unittest
from pathlib import Path
from unittest.mock import patch

import game_problems
from game_engine import Games
from game_model import load_pool

HERE = Path(__file__).parent
FORBIDDEN_IMPORTS = {"subprocess", "socket", "urllib", "http", "requests", "shutil", "ctypes", "importlib", "pickle", "marshal", "os", "asyncio"}
FORBIDDEN_CALLS = {"eval", "exec", "compile", "__import__", "open", "system", "popen"}


def sample_input(pattern):
    """정규식에서 허용 입력 하나를 복원한다(우리 패턴은 리터럴과 공백 구분자만 쓴다)."""
    bs = chr(92)
    return re.sub(re.escape(bs) + "(.)", r"\1", pattern.strip("^$").replace(bs + "s+", " "))


class BoundaryTest(unittest.TestCase):
    def test_game_modules_have_no_exec_or_network(self):
        files = sorted(HERE.glob("game_*.py"))
        self.assertTrue(files)
        for f in files:
            for node in ast.walk(ast.parse(f.read_text(encoding="utf-8"))):
                if isinstance(node, ast.Import):
                    mods = {a.name.split(".")[0] for a in node.names}
                elif isinstance(node, ast.ImportFrom):
                    mods = {(node.module or "").split(".")[0]}
                else:
                    mods = set()
                self.assertFalse(mods & FORBIDDEN_IMPORTS, f"{f.name}: {mods & FORBIDDEN_IMPORTS}")
                if isinstance(node, ast.Call):
                    # re.compile 등 속성 호출은 허용하고, 맨 이름 호출과 system/popen만 막는다
                    name = node.func.id if isinstance(node.func, ast.Name) else getattr(node.func, "attr", "")
                    bad = name in FORBIDDEN_CALLS and (isinstance(node.func, ast.Name) or name in {"system", "popen"})
                    self.assertFalse(bad, f"{f.name}: {name}() 호출")

    def test_commands_reject_injection_variants(self):
        for p in game_problems.POOL.values():
            for c in p.commands:
                base = sample_input(c.pattern.pattern)
                self.assertTrue(c.pattern.fullmatch(base), f"{p.id}.{c.key}: 복원 입력 불일치 '{base}'")
                for bad in (base + "; ls", base + " && ls", base + " | sh", "$(" + base + ")", "x " + base, base + " ../../etc/passwd"):
                    text = " ".join(bad.split()).lower()
                    self.assertFalse(any(k.pattern.fullmatch(text) for k in p.commands), f"{p.id}: '{bad}' 허용됨")

    def test_every_problem_is_solvable_offline(self):
        def no_net(*a, **k):
            raise AssertionError("네트워크 접근 시도")
        with patch.object(socket.socket, "connect", no_net), patch.object(socket, "create_connection", no_net):
            for pid, p in game_problems.POOL.items():
                g = Games(load_pool([r for r in game_problems.RAW if r["id"] == pid]), lambda s, pool, i=pid: [i])
                run = g.handle("POST", ["runs"], {"requestId": f"req-solve-{pid}"})[1]["state"]
                self.assertFalse(run["canJudge"], pid)
                rev = run["revision"]

                def post(action, **body):
                    nonlocal rev
                    code, r = g.handle("POST", ["runs", run["runId"], action], {"revision": rev, "requestId": f"{action}-{rev}-{pid}", **body})
                    self.assertEqual(code, 200, (pid, action, r))
                    rev = r["state"]["revision"]
                    return r["state"]

                if p.type == "terminal":
                    by_key = {c.key: c for c in p.commands}
                    for group in p.required_actions:
                        state = post("commands", command=sample_input(by_key[group.split("|")[0]].pattern.pattern))
                else:
                    state = post("evidence", evidenceIds=list(p.required_ids))
                self.assertTrue(state["canJudge"], pid)
                for s in p.steps:
                    state = post("answers", step=s.key, choiceId=next(c.id for c in s.choices if c.correct))
                self.assertTrue(state["cleared"], pid)
                self.assertEqual(state["flag"], p.flag)
                self.assertEqual(state["ending"]["bonus"], 0 if state["trust"] < 80 else 20)
                self.assertEqual(state["score"], STEP[p.difficulty] * 3 + 5 + state["ending"]["bonus"], pid)  # 무오답·무힌트 만점


STEP = {"쉬움": 10, "보통": 15, "어려움": 20}

if __name__ == "__main__":
    unittest.main()
