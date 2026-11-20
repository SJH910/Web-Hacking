"""출제 알고리즘(B8, problem-pool.md §2). 같은 시드 → 같은 순서(이어하기·랭킹 공정성)."""
import random

FLOORS = 10
EASY_FLOORS, MID_FLOORS, MAX_CHOICE = 3, 5, 5


def make_order(seed, pool):
    """pool: {id: Problem}. 1~3층 쉬움 3 → 4~8층 무작위 5 → 9~10층 어려움 우선 2, 객관식 ≤5·중복 없음."""
    rng = random.Random(seed)
    ids = sorted(pool)
    diff = lambda i: pool[i].difficulty
    used, last = [], []

    def take(candidates, n, into):
        pick = [c for c in candidates if c not in used and c not in last]
        into.extend(rng.sample(pick, min(n, len(pick))))

    take([i for i in ids if diff(i) == "쉬움"], EASY_FLOORS, used)
    # 클라이맥스(어려움)를 먼저 확보해 중반 추첨이 어려움을 다 쓰지 못하게 한다. 모자라면 보통으로 보충.
    take([i for i in ids if diff(i) == "어려움"], FLOORS - EASY_FLOORS - MID_FLOORS, last)
    take([i for i in ids if diff(i) == "보통"], FLOORS - EASY_FLOORS - MID_FLOORS - len(last), last)
    take(ids, MID_FLOORS, used)
    take(ids, FLOORS - len(used) - len(last), used)
    used += last

    # 객관식 상한: 뒤 층부터 남은 터미널 문제로 교체. 1차는 도입·클라이맥스 층의 난이도를 지키고, 그래도 넘으면 2차는 난이도를 무시한다.
    for keep_tier in (True, False):
        for pos in range(len(used) - 1, -1, -1):
            if sum(pool[i].type == "choice" for i in used) <= MAX_CHOICE:
                return used
            if pool[used[pos]].type != "choice":
                continue
            tier = keep_tier and (pos < EASY_FLOORS or pos >= EASY_FLOORS + MID_FLOORS)
            spare = [i for i in ids if i not in used and pool[i].type == "terminal" and (not tier or diff(i) == diff(used[pos]))]
            if spare:
                used[pos] = rng.choice(spare)
    return used
