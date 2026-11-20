"""용범의 탑 문제 풀 데이터(합성·가상). 서버 전용: 정답·명령·출력을 클라이언트로 보내지 않는다.

night-log(scenario-1-record-archive.md 기준) + game_pool.py의 15문제 = 16문제. 새 문제는 같은 형식으로 RAW에 추가한다.
프런트 목업 3개(archive·login·greenhouse)는 3단 판정이 없어 아직 풀에 없다.
"""
from game_model import load_pool


def _access_log():
    fails = [f"10.0.0.9     [10:02:0{1 + i * 6 // 23}] \"POST /gate/login\" 401" for i in range(23)]
    head = ['203.0.113.7  [09:58:14] "POST /gate/login" 200   gatekeeper']
    tail = ['10.0.0.9     [10:02:07] "POST /gate/login" 200   gatekeeper',
            '198.51.100.4 [10:05:33] "GET  /gate/status" 200']
    return head, fails, tail


_head, _fails, _tail = _access_log()
ACCESS_LOG = "\n".join(_head + _fails + _tail)
GREP_401 = "\n".join(_fails)
GREP_200 = "\n".join(l for l in _head + _tail if " 200" in l)

NIGHT_LOG = {
    "id": "night-log", "title": "야간 접속 기록", "type": "terminal", "difficulty": "쉬움", "owasp": "A07·A09",
    "objective": "문지기 로그인 기록을 뒤져 누가 어떻게 침입을 시도했는지, 왜 막히지 않았는지 판정하세요.",
    "allyOpening": "음, 접근 기록이 좀 많긴 한데… 인기 많은 문이라 그런 거 아냐? 정상 트래픽 같은데 그냥 넘어가자.",
    "evidence": [
        {"number": "E01", "title": "반복된 접근 시도", "detail": "10.0.0.9에서 6초간 23회 연속 401.", "tag": "접근 기록"},
        {"number": "E02", "title": "실패 뒤 성공", "detail": "다수 실패 직후 같은 IP에서 200 1건.", "tag": "응답 기록"},
        {"number": "E03", "title": "기록되지 않은 실패", "detail": "실패 23건이 감사 로그에 없음 + 잠금 미설정.", "tag": "권한/로깅 단서"},
    ],
    "commands": [
        {"key": "help", "pattern": r"^help$", "output": "명령: ls, cat <파일>, grep <코드> access.log, count <ip>, diff attempts logged"},
        {"key": "ls", "pattern": r"^ls$", "output": "access.log  security.log  gate.conf"},
        {"key": "cat_access", "pattern": r"^cat\s+access\.log$", "output": ACCESS_LOG, "reveals": ["E01", "E02"]},
        {"key": "grep_401", "pattern": r"^grep\s+401\s+access\.log$", "output": GREP_401, "reveals": ["E01"]},
        {"key": "grep_200", "pattern": r"^grep\s+200\s+access\.log$", "output": GREP_200, "reveals": ["E02"]},
        {"key": "count_ip", "pattern": r"^count\s+10\.0\.0\.9$", "output": "10.0.0.9 → 6초간 24회 (23×401, 1×200)", "reveals": ["E01"]},
        {"key": "cat_security", "pattern": r"^cat\s+security\.log$", "output": "[10:02:07] login_ok ip=10.0.0.9 user=gatekeeper", "reveals": ["E03"]},
        {"key": "cat_conf", "pattern": r"^cat\s+gate\.conf$",
         "output": "session_timeout     = 30m\nlockout_threshold   =\nlog_failed_attempts = false", "reveals": ["E03"]},
        {"key": "diff_log", "pattern": r"^diff\s+attempts\s+logged$", "output": "시도한 실패: 23 / 기록된 실패: 0 → 23건 미기록", "reveals": ["E03"]},
    ],
    "requiredActions": ["grep_401|count_ip", "cat_security|cat_conf|diff_log"],
    "steps": [
        {"key": "classify", "question": "이 기록이 가리키는 문제는?", "choices": [
            {"id": "c1", "label": "무차별 대입 시도 + 실패 미기록", "correct": True},
            {"id": "c2", "label": "인기 많은 문이라 생긴 정상 트래픽", "isTrap": True},
            {"id": "c3", "label": "단순 서버 과부하"}],
         "why": "한 IP가 6초간 23회 실패 후 성공 → 자동 대입. 실패가 로그에 없어 '정상 트래픽'이 아니다."},
        {"key": "verdict", "question": "이 상태는?", "choices": [
            {"id": "v1", "label": "양호"},
            {"id": "v2", "label": "취약", "correct": True},
            {"id": "v3", "label": "증거 부족(needs_review)"}],
         "why": "무제한 시도(잠금 없음) + 실패 미기록 → 탐지·차단 부재. 증거가 명확해 needs_review 아님."},
        {"key": "action", "question": "올바른 조치는?", "choices": [
            {"id": "a1", "label": "시도 횟수 제한·잠금 + 실패 로그 기록", "correct": True},
            {"id": "a2", "label": "로그를 더 자주 비워 용량 확보", "isTrap": True},
            {"id": "a3", "label": "서버 증설"}],
         "why": "lockout_threshold 설정 + log_failed_attempts=true로 차단·탐지 복구."},
    ],
    "hints": [
        {"level": 1, "text": "한 곳(IP)에서 몇 번이나 두드렸는지 세어볼까?"},
        {"level": 2, "text": "실패가 이렇게 많은데, 그게 전부 기록에 남았는지 security.log랑 비교해봐."},
        {"level": 3, "text": "막는 장치(잠금)도, 남기는 장치(기록)도 없어 — 그게 핵심이야."},
    ],
    "flag": "FLAG{floor1_unlogged_bruteforce}",
}

from game_pool import POOL_RAW  # noqa: E402  (NIGHT_LOG 정의 뒤에 둔다)

RAW = [NIGHT_LOG] + POOL_RAW
POOL = load_pool(RAW)
