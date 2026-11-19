"""B8 출제 알고리즘 + 풀 최소 조건 검사."""
import copy
import unittest

import game_problems
from game_model import load_pool
from game_order import make_order

POOL = game_problems.POOL


class OrderTest(unittest.TestCase):
    def test_pool_meets_minimums(self):  # problem-pool.md §2 최소 조건
        kinds = [p.type for p in POOL.values()]
        self.assertGreaterEqual(len(POOL), 10)
        self.assertGreaterEqual(sum(p.difficulty == "쉬움" for p in POOL.values()), 3)
        self.assertGreaterEqual(sum(p.difficulty == "어려움" for p in POOL.values()), 2)
        self.assertGreaterEqual(kinds.count("terminal"), 5)

    def test_deterministic_and_unique(self):
        for n in range(200):
            seed = f"seed_{n}"
            order = make_order(seed, POOL)
            self.assertEqual(order, make_order(seed, POOL))
            self.assertEqual((len(order), len(set(order))), (10, 10))
            self.assertTrue(set(order) <= set(POOL))

    def test_difficulty_curve(self):
        for n in range(200):
            order = make_order(f"s{n}", POOL)
            self.assertTrue(all(POOL[i].difficulty == "쉬움" for i in order[:3]))
            self.assertEqual(sum(POOL[i].difficulty == "어려움" for i in order[8:]), 2)

    def test_seeds_differ(self):
        self.assertGreater(len({tuple(make_order(f"s{n}", POOL)) for n in range(50)}), 20)

    def test_choice_cap(self):
        raw = []
        for i in range(14):  # 객관식 8 + 터미널 6(최소 조건)을 난이도별로 섞은 합성 풀
            d = copy.deepcopy(game_problems.NIGHT_LOG)
            d.update(id=f"p{i}", title=f"문제{i}", difficulty=("쉬움", "보통", "어려움")[i % 3])
            if i >= 6:
                d.update(type="choice", requiredIds=["E01"])
                del d["commands"], d["requiredActions"]
            raw.append(d)
        pool = load_pool(raw)
        for n in range(100):
            order = make_order(f"c{n}", pool)
            self.assertEqual(len(order), 10)
            self.assertLessEqual(sum(pool[i].type == "choice" for i in order), 5)
            self.assertEqual(len(set(order)), len(order))

    def test_small_pool(self):
        small = {k: POOL[k] for k in ("night-log", "old-lock")}
        self.assertEqual(sorted(make_order("x", small)), ["night-log", "old-lock"])


if __name__ == "__main__":
    unittest.main()
