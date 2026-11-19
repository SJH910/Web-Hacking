"""B7 어댑터 검사: 더미 소견 → 증거·명령, 게임 모델 검증 통과, 위험 문자 정리."""
import copy
import unittest

import game_problems
from game_adapter import bake
from game_model import parse_problem

FINDINGS = [
    {"owasp": "A02", "title": "보안 헤더 누락: content-security-policy", "severity": "low", "status": "vuln", "evidence": "응답에 content-security-policy 없음", "note": ""},
    {"owasp": "A04", "title": "HSTS 없음", "severity": "low", "status": "vuln", "evidence": "Strict-Transport-Security 헤더 없음", "note": "HTTPS 강제 없음"},
    {"owasp": "A09", "title": "로깅 점검", "severity": "info", "status": "manual", "evidence": "", "note": "서버 접근 필요"},
    {"owasp": "A05", "title": "무시될 소견", "severity": "info", "status": "error", "evidence": "x", "note": ""},
]


class AdapterTest(unittest.TestCase):
    def test_bake_and_validate(self):
        evidence, commands, verdict = bake(FINDINGS)
        self.assertEqual([e["number"] for e in evidence], ["E1", "E2", "E3"])  # error 상태는 제외
        self.assertEqual(verdict, "취약")
        d = copy.deepcopy(game_problems.NIGHT_LOG)
        d.update(id="baked", title="구운 문제", evidence=evidence, commands=commands, requiredActions=["inspect1", "inspect2|inspect3"])
        p = parse_problem(d)  # 모델 검증 통과
        self.assertTrue(p.commands[0].pattern.fullmatch("inspect e1"))
        self.assertIn("HTTPS 강제 없음", commands[1]["output"])

    def test_verdict_rules(self):
        self.assertEqual(bake([FINDINGS[2]])[2], "증거 부족")
        self.assertEqual(bake([{"owasp": "A02", "title": "있음", "status": "safe", "evidence": "ok"}])[2], "양호")
        self.assertEqual(bake([])[2], "증거 부족")

    def test_sanitizes_and_truncates(self):
        evidence, commands, _ = bake([{"owasp": "A05", "title": "t\x00\x1b[31m", "status": "vuln", "evidence": "<x7y>" + "a" * 500, "note": None}])
        self.assertNotIn("\x00", evidence[0]["title"] + commands[0]["output"])
        self.assertNotIn("\x1b", evidence[0]["title"] + commands[0]["output"])
        self.assertLessEqual(len(evidence[0]["detail"]), 200)
        self.assertEqual(bake(["not a dict", None, 3])[0], [])


if __name__ == "__main__":
    unittest.main()
