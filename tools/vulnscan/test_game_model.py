"""B1 문제 데이터 모델 검사. 네트워크·실행 없음."""
import copy
import unittest

import game_problems
from game_model import ProblemError, load_pool, parse_problem


def bad(**change):
    d = copy.deepcopy(game_problems.NIGHT_LOG)
    d.update(change)
    return d


class ModelTest(unittest.TestCase):
    def test_night_log_loads(self):
        p = game_problems.POOL["night-log"]
        self.assertEqual((p.type, p.difficulty, len(p.steps), len(p.commands)), ("terminal", "쉬움", 3, 9))

    def test_access_log_matches_spec(self):
        p = game_problems.POOL["night-log"]
        self.assertEqual(game_problems.GREP_401.count("\n") + 1, 23)
        self.assertEqual(sum(" 401" in l for l in game_problems.ACCESS_LOG.splitlines()), 23)
        cmd = {c.key: c for c in p.commands}
        self.assertTrue(cmd["count_ip"].pattern.search("count 10.0.0.9"))
        self.assertFalse(cmd["cat_access"].pattern.search("cat access.log; rm -rf /"))

    def test_rejects_bad_data(self):
        steps = copy.deepcopy(game_problems.NIGHT_LOG["steps"])
        steps[0]["choices"][1]["correct"] = True
        for change in (
            {"type": "shell"}, {"difficulty": "극악"}, {"id": "Bad Id"},
            {"steps": steps}, {"steps": steps[:2]}, {"requiredActions": ["nope|ls"]},
            {"hints": game_problems.NIGHT_LOG["hints"][:2]},
        ):
            with self.assertRaises(ProblemError, msg=str(list(change))):
                parse_problem(bad(**change))

    def test_rejects_bad_command(self):
        d = bad()
        d["commands"][2]["pattern"] = "("
        with self.assertRaises(ProblemError):
            parse_problem(d)
        d = bad()
        d["commands"][2]["reveals"] = ["E99"]
        with self.assertRaises(ProblemError):
            parse_problem(d)

    def test_pool_rejects_duplicates(self):
        with self.assertRaises(ProblemError):
            load_pool([bad(), bad()])


if __name__ == "__main__":
    unittest.main()
