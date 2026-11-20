"""raon_llm(라온 LLM 어댑터) 테스트. 외부 네트워크 없음: 로컬 목 서버만 사용."""
import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import raon_llm


class _Mock(BaseHTTPRequestHandler):
    captured = []  # 모델에 전달된 user 프롬프트 기록(데이터 경계 검증용)

    def log_message(self, *a):
        pass

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        req = json.loads(self.rfile.read(n) or b"{}")
        user = req["messages"][-1]["content"]
        type(self).captured.append(user)
        reply = "라온이 다시 건넨 한마디."
        body = json.dumps({"choices": [{"message": {"content": reply}}]}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(body)


def _state(trust=60):
    return {
        "runId": "r1", "floor": 1, "trust": trust, "cleared": False,
        "problem": {"objective": "헤더 점검", "allyOpening": "분명 헤더 다 빠졌을걸?",
                    "type": "terminal", "difficulty": "쉬움"},
        "evidence": [{"title": "CSP", "detail": "있음"}],
        "hints": [{"level": 1, "text": "헤더가 있는지 먼저 확인", "source": "rule"}],
    }


class TrustTier(unittest.TestCase):
    def test_boundaries(self):
        self.assertEqual(raon_llm.trust_tier(80), "clear")
        self.assertEqual(raon_llm.trust_tier(79), "mixed")
        self.assertEqual(raon_llm.trust_tier(50), "mixed")
        self.assertEqual(raon_llm.trust_tier(49), "weak")

    def test_bad_input(self):
        self.assertEqual(raon_llm.trust_tier(None), "mixed")  # 기본 60


class DecorateFallback(unittest.TestCase):
    def test_no_client(self):
        obj = {"state": _state()}
        self.assertIs(raon_llm.decorate(None, obj), obj)  # 그대로 반환

    def test_dead_port_keeps_static(self):
        c = raon_llm.RaonClient(1, "llama3", timeout=1)  # 포트1: 연결 실패
        obj = {"state": _state()}
        out = raon_llm.decorate(c, obj)
        self.assertEqual(out["state"]["problem"]["allyOpening"], "분명 헤더 다 빠졌을걸?")
        self.assertNotIn("allySource", out["state"]["problem"])
        self.assertEqual(out["state"]["hints"][-1]["source"], "rule")

    def test_cleared_untouched(self):
        c = raon_llm.RaonClient(1, "llama3", timeout=1)
        obj = {"state": dict(_state(), cleared=True)}
        out = raon_llm.decorate(c, obj)
        self.assertEqual(out["state"]["problem"]["allyOpening"], "분명 헤더 다 빠졌을걸?")


class DecorateSuccess(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        _Mock.captured = []
        cls.srv = ThreadingHTTPServer(("127.0.0.1", 0), _Mock)
        cls.port = cls.srv.server_address[1]
        threading.Thread(target=cls.srv.serve_forever, daemon=True).start()

    @classmethod
    def tearDownClass(cls):
        cls.srv.shutdown()

    def test_decorate_redteam(self):
        c = raon_llm.RaonClient(self.port, "llama3", timeout=3)
        # 챌린지 시작: allyOpening 윤문
        o1 = raon_llm.decorate_redteam(c, {"challengeId": "c1", "floor": 1, "title": "열린 로비", "allyOpening": "원래 첫마디"})
        self.assertEqual(o1["allyOpening"], "라온이 다시 건넨 한마디.")
        self.assertEqual(o1["allySource"], "llm")
        # 힌트 응답: text 윤문
        o2 = raon_llm.decorate_redteam(c, {"text": "원래 힌트"})
        self.assertEqual(o2["text"], "라온이 다시 건넨 한마디.")
        self.assertEqual(o2["source"], "llm")
        # 다른 응답(html 등)은 건드리지 않음
        o3 = raon_llm.decorate_redteam(c, {"status": 200, "html": "<p>x</p>"})
        self.assertNotIn("allySource", o3)

    def test_replaces_and_tags(self):
        c = raon_llm.RaonClient(self.port, "llama3", timeout=3)
        obj = {"state": _state(trust=85)}
        out = raon_llm.decorate(c, obj)
        p = out["state"]["problem"]
        self.assertEqual(p["allyOpening"], "라온이 다시 건넨 한마디.")
        self.assertEqual(p["allySource"], "llm")
        self.assertEqual(out["state"]["hints"][-1]["source"], "llm")

    def test_data_boundary(self):
        """모델에 정답·채점·플래그·선택지가 전달되지 않는다."""
        c = raon_llm.RaonClient(self.port, "llama3", timeout=3)
        raon_llm.decorate(c, {"state": _state()})
        joined = "\n".join(_Mock.captured)
        for forbidden in ("correct", "flag", "choiceId", "required", "steps", "isTrap"):
            self.assertNotIn(forbidden, joined)

    def test_cached_once_per_floor(self):
        _Mock.captured = []
        c = raon_llm.RaonClient(self.port, "llama3", timeout=3)
        for _ in range(3):
            raon_llm.decorate(c, {"state": _state()})
        openings = [u for u in _Mock.captured if "입장" in u]
        self.assertEqual(len(openings), 1)  # 같은 (runId, floor)는 1회만 호출


if __name__ == "__main__":
    unittest.main()
