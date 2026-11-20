"""용범의 탑 문제 데이터 모델(B1). floor-slice-design §8 · problem-pool §3 계약.

정답·명령·출력은 서버 전용이다. 이 모듈은 클라이언트로 내려보내는 코드를 갖지 않는다(B2에서 별도 뷰 생성).
입력 dict의 키는 계약(camelCase), 내부 속성은 snake_case.
"""
import re
from dataclasses import dataclass, field

TYPES = ("terminal", "choice")
DIFFICULTIES = ("쉬움", "보통", "어려움")
STEP_KEYS = ("classify", "verdict", "action")
_ID = re.compile(r"^[a-z0-9][a-z0-9-]{0,63}$")


class ProblemError(ValueError):
    """문제 데이터가 계약에 맞지 않을 때."""


@dataclass(frozen=True)
class Choice:
    id: str
    label: str
    correct: bool = False
    is_trap: bool = False


@dataclass(frozen=True)
class Step:
    key: str
    question: str
    choices: tuple
    why: str


@dataclass(frozen=True)
class Evidence:
    number: str
    title: str
    detail: str
    tag: str


@dataclass(frozen=True)
class Hint:
    level: int
    text: str


@dataclass(frozen=True)
class Command:
    key: str
    pattern: re.Pattern
    output: str
    reveals: tuple = ()


@dataclass(frozen=True)
class Problem:
    id: str
    title: str
    type: str
    difficulty: str
    owasp: str
    objective: str
    evidence: tuple
    ally_opening: str
    hints: tuple
    flag: str
    steps: tuple
    commands: tuple = ()
    # terminal: 그룹별 OR("a|b") 중 1개 이상 실행. choice: 전부 선택해야 하는 증거 번호.
    required_actions: tuple = ()
    required_ids: tuple = ()
    extra: dict = field(default_factory=dict, compare=False)


def _need(cond, msg):
    if not cond:
        raise ProblemError(msg)


def _str(d, key, where):
    v = d.get(key)
    _need(isinstance(v, str) and v.strip(), f"{where}: '{key}' 문자열 필요")
    return v


def _step(d, where):
    key = _str(d, "key", where)
    _need(key in STEP_KEYS, f"{where}: key는 {STEP_KEYS} 중 하나")
    raw = d.get("choices")
    _need(isinstance(raw, list) and len(raw) >= 2, f"{where}: 보기 2개 이상")
    choices = tuple(Choice(_str(c, "id", where), _str(c, "label", where), c.get("correct") is True, c.get("isTrap") is True) for c in raw)
    _need(len({c.id for c in choices}) == len(choices), f"{where}: 보기 id 중복")
    _need(sum(c.correct for c in choices) == 1, f"{where}: 정답은 정확히 1개")
    _need(not any(c.correct and c.is_trap for c in choices), f"{where}: 정답이 함정일 수 없음")
    return Step(key, _str(d, "question", where), choices, _str(d, "why", where))


def parse_problem(d: dict) -> Problem:
    """검증하며 Problem 생성. 어긋나면 ProblemError."""
    _need(isinstance(d, dict), "문제는 dict")
    pid = _str(d, "id", "problem")
    _need(_ID.match(pid), f"{pid}: id는 소문자·숫자·하이픈")
    where = pid
    ptype, diff = _str(d, "type", where), _str(d, "difficulty", where)
    _need(ptype in TYPES, f"{where}: type은 {TYPES}")
    _need(diff in DIFFICULTIES, f"{where}: difficulty는 {DIFFICULTIES}")

    evidence = tuple(Evidence(_str(e, "number", where), _str(e, "title", where), _str(e, "detail", where), _str(e, "tag", where)) for e in d.get("evidence") or [])
    numbers = {e.number for e in evidence}
    _need(evidence and len(numbers) == len(evidence), f"{where}: 증거 1개 이상, 번호 유일")

    hints = tuple(Hint(h.get("level"), _str(h, "text", where)) for h in d.get("hints") or [])
    _need([h.level for h in hints] == [1, 2, 3], f"{where}: 힌트는 level 1,2,3 순서")

    steps = tuple(_step(s, f"{where}.steps") for s in d.get("steps") or [])
    _need([s.key for s in steps] == list(STEP_KEYS), f"{where}: steps 순서는 {STEP_KEYS}")

    commands, required_actions, required_ids = (), (), ()
    if ptype == "terminal":
        cmds = []
        for c in d.get("commands") or []:
            key = _str(c, "key", where)
            try:
                pat = re.compile(_str(c, "pattern", where))
            except re.error as e:
                raise ProblemError(f"{where}.{key}: 정규식 오류 {e}") from e
            reveals = tuple(c.get("reveals") or ())
            _need(set(reveals) <= numbers, f"{where}.{key}: 없는 증거 번호 {set(reveals) - numbers}")
            cmds.append(Command(key, pat, c.get("output", ""), reveals))
        commands = tuple(cmds)
        keys = {c.key for c in commands}
        _need(commands and len(keys) == len(commands), f"{where}: 명령 1개 이상, key 유일")
        required_actions = tuple(d.get("requiredActions") or ())
        _need(required_actions, f"{where}: requiredActions 필요")
        for group in required_actions:
            _need(set(group.split("|")) <= keys, f"{where}: requiredActions에 없는 명령 '{group}'")
        # 필수 그룹을 채워도 접근 가능한 증거가 있어야 한다는 최소 보장은 reveals로 충분
    else:
        required_ids = tuple(d.get("requiredIds") or ())
        _need(required_ids and set(required_ids) <= numbers, f"{where}: requiredIds는 증거 번호의 비어 있지 않은 부분집합")

    return Problem(pid, _str(d, "title", where), ptype, diff, _str(d, "owasp", where), _str(d, "objective", where),
                   evidence, _str(d, "allyOpening", where), hints, _str(d, "flag", where), steps,
                   commands, required_actions, required_ids)


def load_pool(raw_list) -> dict:
    """문제 목록 → {id: Problem}. id·title 중복 거부."""
    pool = {}
    for raw in raw_list:
        p = parse_problem(raw)
        _need(p.id not in pool, f"id 중복: {p.id}")
        pool[p.id] = p
    _need(len({p.title for p in pool.values()}) == len(pool), "title 중복")
    return pool
