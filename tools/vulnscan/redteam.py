"""용범의 탑 레드팀(파훼자) 모드 — 가상 취약 웹앱 챌린지 엔진.

점진 전환(신 모드): 기존 game_engine(블루팀 판정)은 그대로 두고 별도 모듈로 추가한다.
설계: apps/game/red-team-redesign.md.

불변식:
  - 실제 네트워크·실행 없음. 모든 페이지·응답은 서버 고정 합성 스크립트.
  - FLAG는 서버 보관. 익스플로잇 성공 조건을 서버가 확인했을 때만 응답 본문에 노출.
  - 모든 데이터·비밀·세션은 가짜.

모델: 각 챌린지는 '실제 페이지처럼 보이는' HTML(폼·링크 포함)을 돌려준다.
      플레이어가 페이지 안에서 상호작용(링크 클릭·폼 입력·주소 편집)하면 visit가 결정적 합성 응답을 준다.
      챌린지별 취약을 성공적으로 공격하면 exploited=True, FLAG가 본문에 포함된다.
"""
import html as _html
import random
import re
import secrets

RT_FLAG_RE = re.compile(r"^FLAG\{[A-Za-z0-9_]{1,64}\}$")
_XSS_EXEC = re.compile(r"<\s*script|on\w+\s*=|<\s*svg|<\s*img|<\s*iframe|javascript:", re.I)
_SQLI = re.compile(r"'\s*or\s*'?1'?\s*=\s*'?1|'\s*or\s+1\s*=\s*1|'\s*--|'\s*or\s*'", re.I)


def _resp(status, inner, *, title="", comments=(), owner=None, exploited=False, flag=False):
    return {"status": status, "title": title, "html": inner, "owner": owner,
            "sourceComments": list(comments), "exploited": exploited, "flagRevealed": flag}


def esc(s):
    return _html.escape(str(s), quote=True)


# ====================================================================
# C1. 열린 로비 — A01 접근통제(IDOR) · guided · 쉬움
# ====================================================================
C1 = {
    "id": "open-lobby", "title": "열린 로비", "siteName": "쪽지함",
    "difficulty": "쉬움", "owasp": "A01 접근통제(IDOR)", "tier": "guided",
    "session": {"user": "visitor", "cookies": "sid=sess_v01; role=user"},
    "entry": "/inbox",
    "allyOpening": "네 쪽지함만 보면 돼. 다른 번호는 어차피 막혀 있을 거야.",
    "hints": ["쪽지 주소에 번호가 보이지? 그 번호를 눈여겨봐.",
              "페이지 '소스 보기'에 개발자가 흘린 메모가 있어.",
              "내 쪽지가 18이면, 바로 옆 번호는 누구 걸까?"],
    "flag": "FLAG{idor_sequential_notes}",
    "wrapUp": "번호만 바꿔 남의 자원에 접근했다 — IDOR(접근 통제). 서버가 요청자의 소유권을 확인해야 한다.",
    "notes": {
        18: ("visitor", "환영합니다, visitor님! 첫 로그인을 축하해요."),
        19: ("admin", "[관리자 전용] 임시 복구 코드: hunter2 · FLAG{idor_sequential_notes}"),
        20: ("staff-02", "[staff-02] 회의는 3시로 미뤄졌습니다."),
        21: ("staff-03", "[staff-03] 프린터 토너 교체 요청."),
        22: ("staff-07", "[staff-07] 점심 메뉴 투표 부탁."),
    },
}


def _c1(path, query, data):
    me = C1["session"]["user"]
    if path == "/inbox":
        inner = ("<h2>📬 쪽지함 — visitor 님</h2>"
                 "<!-- note ids are sequential -->"
                 "<ul class='rt-list'>"
                 "<li><a href='/note?id=18'>#18 · 환영합니다</a></li>"
                 "</ul><p class='rt-muted'>받은 쪽지 1통.</p>")
        return _resp(200, inner, title="쪽지함", comments=["note ids are sequential"])
    if path == "/robots.txt":
        return _resp(200, "<pre>User-agent: *\nDisallow: /note</pre>", title="robots.txt")
    if path == "/note":
        try:
            nid = int(query.get("id"))
        except (TypeError, ValueError):
            return _resp(400, "<p>id가 올바르지 않습니다.</p>", title="오류")
        rec = C1["notes"].get(nid)
        if rec is None:
            return _resp(404, "<p>쪽지를 찾을 수 없습니다.</p>", title="404")
        owner, body = rec
        is_flag = "FLAG{" in body
        inner = f"<h2>쪽지 #{nid}</h2><p class='rt-owner'>소유자: {esc(owner)}</p><p>{esc(body)}</p>"
        return _resp(200, inner, title=f"쪽지 #{nid}", owner=owner,
                     exploited=(owner != me), flag=is_flag)
    return _resp(404, "<p>없는 페이지입니다.</p>", title="404")


# ====================================================================
# C2. 거울 게시판 — A05 반사형 XSS · mixed · 보통
# ====================================================================
C2 = {
    "id": "mirror-board", "title": "거울 게시판", "siteName": "거울 방명록",
    "difficulty": "보통", "owasp": "A05 반사형 XSS", "tier": "mixed",
    "session": {"user": "guest", "cookies": "sid=sess_g22"},
    "entry": "/board",
    "allyOpening": "그냥 글자가 그대로 보이는 거야, 위험할 거 없어.",
    "hints": ["검색창에 특수문자 < 나 > 를 넣으면 어떻게 보일까?",
              "입력이 '그대로' 나온다는 건 브라우저가 태그로 해석할 수도 있다는 뜻이야.",
              "<svg onload=alert(1)> 처럼 실행되는 태그를 검색창에 넣어 봐."],
    "flag": "FLAG{reflected_xss_admin_cookie}",
    "wrapUp": "입력이 이스케이프 없이 그대로 반사됐다 — 반사형 XSS. 출력 인코딩과 CSP가 필요하다.",
}


def _c2(path, query, data):
    if path != "/board":
        return _resp(404, "<p>없는 페이지입니다.</p>", title="404")
    q = (data or {}).get("q", query.get("q", ""))
    form = ("<h2>🪞 거울 방명록</h2>"
            "<!-- 검색어는 그대로(이스케이프 없이) 다시 보여집니다 -->"
            "<form data-rt action='/board' method='get'>"
            "<input name='q' placeholder='방명록 검색'>"
            "<button type='submit'>검색</button></form>")
    if not q:
        body = ("<ul class='rt-list'><li>환영합니다 :)</li><li>오늘도 좋은 하루!</li></ul>")
        return _resp(200, form + body, title="거울 방명록",
                     comments=["검색어는 그대로(이스케이프 없이) 다시 보여집니다"])
    # 취약: 입력을 이스케이프 없이 그대로 반사한다.
    reflected = f"<div class='rt-reflect'>검색 결과 ‘{q}’ — 0건</div>"
    if _XSS_EXEC.search(q):
        leak = ("<div class='rt-alert'>⚠️ 관리자 봇이 방금 이 페이지를 열람했습니다. "
                "주입된 스크립트가 실행되어 세션이 유출됐습니다 → "
                "<b>FLAG{reflected_xss_admin_cookie}</b></div>")
        return _resp(200, form + reflected + leak, title="거울 방명록",
                     comments=["검색어는 그대로(이스케이프 없이) 다시 보여집니다"],
                     exploited=True, flag=True)
    return _resp(200, form + reflected, title="거울 방명록",
                 comments=["검색어는 그대로(이스케이프 없이) 다시 보여집니다"])


# ====================================================================
# C3. 참·거짓의 문 — A03 SQLi 인증 우회 · mixed · 보통
# ====================================================================
C3 = {
    "id": "truth-gate", "title": "참·거짓의 문", "siteName": "직원 포털",
    "difficulty": "보통", "owasp": "A03 SQL 인젝션(인증 우회)", "tier": "mixed",
    "session": {"user": "anonymous", "cookies": "(비로그인)"},
    "entry": "/login",
    "allyOpening": "비밀번호를 모르면 못 들어가. 추측은 시간 낭비일 뿐이야.",
    "hints": ["아이디 칸에 작은따옴표 ' 하나만 넣고 로그인해 봐. 뭐가 뜨지?",
              "오류 메시지가 쿼리 구조를 알려줘. WHERE 절을 떠올려.",
              "' OR '1'='1 처럼 조건이 '항상 참'이 되게 만들어 봐."],
    "flag": "FLAG{auth_bypass_sqli}",
    "wrapUp": "입력이 쿼리 논리로 해석됐다 — SQL 인젝션 인증 우회. 파라미터 바인딩(프리페어드 스테이트먼트)이 필요하다.",
}


def _c3(path, query, data):
    if path != "/login":
        return _resp(404, "<p>없는 페이지입니다.</p>", title="404")
    d = data or {}
    user = d.get("user", query.get("user", ""))
    pw = d.get("pw", query.get("pw", ""))
    form = ("<h2>🔐 직원 로그인</h2>"
            "<!-- 질의: SELECT * FROM users WHERE user='$user' AND pw='$pw' -->"
            "<form data-rt action='/login' method='post'>"
            "<input name='user' placeholder='아이디'>"
            "<input name='pw' type='password' placeholder='비밀번호'>"
            "<button type='submit'>로그인</button></form>")
    comments = ["질의: SELECT * FROM users WHERE user='$user' AND pw='$pw'"]
    if not user and not pw:
        return _resp(200, form, title="직원 로그인", comments=comments)
    # 인증 우회 성공
    if _SQLI.search(user) or _SQLI.search(pw):
        leak = ("<div class='rt-alert'>✅ admin 으로 로그인되었습니다(인증 우회). "
                "관리 콘솔 접근 토큰 → <b>FLAG{auth_bypass_sqli}</b></div>")
        return _resp(200, form + leak, title="로그인 성공", comments=comments,
                     exploited=True, flag=True)
    # 작은따옴표 → SQL 오류(단서)
    if "'" in user or "'" in pw:
        err = ("<div class='rt-error'>SQL 오류: unterminated quoted string near "
               f"\"WHERE user='{esc(user)}'\"</div>")
        return _resp(200, form + err, title="오류", comments=comments)
    return _resp(200, form + "<div class='rt-error'>로그인 실패: 아이디 또는 비밀번호가 올바르지 않습니다.</div>",
                 title="로그인 실패", comments=comments)


CHALLENGES = {"c1": C1, "c2": C2, "c3": C3}
_VISITORS = {"c1": _c1, "c2": _c2, "c3": _c3}
ORDER = ["c1", "c2", "c3"]


def catalog():
    return [{"id": cid, "title": CHALLENGES[cid]["title"], "owasp": CHALLENGES[cid]["owasp"],
             "difficulty": CHALLENGES[cid]["difficulty"], "tier": CHALLENGES[cid]["tier"]}
            for cid in ORDER]


# ---- 등반: 층별 랜덤 출제(중복 없음). 시드 기반 결정적 → 이어하기·공정성(X3) ----
def _order(seed):
    o = list(ORDER)
    random.Random(str(seed)).shuffle(o)
    return o


def climb():
    """새 등반 시작: 시드 발급. 층 수는 풀 크기. 출제 순서는 서버가 시드로 재현(FE에 미리 노출 안 함)."""
    return {"seed": secrets.token_hex(4), "floors": len(ORDER)}


def floor_start(seed, n):
    """시드의 n번째 층 챌린지 시작 정보. 현재 층만 돌려줘 다음 층을 미리 스포일하지 않는다."""
    o = _order(seed)
    if not isinstance(n, int) or not 1 <= n <= len(o):
        return None
    return {**start(o[n - 1]), "floor": n, "floors": len(o)}


def start(cid):
    c = CHALLENGES[cid]
    return {"challengeId": cid, "title": c["title"], "siteName": c["siteName"],
            "difficulty": c["difficulty"], "owasp": c["owasp"], "tier": c["tier"],
            "entry": c["entry"], "session": c["session"], "allyOpening": c["allyOpening"],
            "hintCount": len(c["hints"]), "cleared": False}


def visit(cid, path, query, data):
    return _VISITORS[cid](path, query or {}, data or {})


def hint(cid, level):
    c = CHALLENGES[cid]
    if not isinstance(level, int) or not 1 <= level <= len(c["hints"]):
        return None
    return c["hints"][level - 1]


def submit(cid, flag):
    c = CHALLENGES[cid]
    if not isinstance(flag, str) or not RT_FLAG_RE.match(flag.strip()):
        return {"cleared": False, "message": "FLAG 형식이 올바르지 않습니다. 예: FLAG{...}"}
    if flag.strip() == c["flag"]:
        return {"cleared": True, "wrapUp": c["wrapUp"]}
    return {"cleared": False, "message": "FLAG가 일치하지 않습니다. 더 탐색해 보세요."}


# ---- HTTP 진입점: (상태코드, JSON). scanner가 /api/redteam/ 이후 경로를 넘긴다. ----
def handle(method, parts, body):
    try:
        if method == "GET" and parts == ["catalog"]:
            return 200, {"challenges": catalog()}
        if method == "GET" and parts == ["climb"]:
            return 200, climb()
        if method == "GET" and len(parts) == 3 and parts[0] == "floor":
            try:
                n = int(parts[2])
            except ValueError:
                return 400, {"error": "층 번호 오류"}
            fs = floor_start(parts[1], n)
            return (200, fs) if fs else (404, {"error": "없는 층"})
        if method == "GET" and len(parts) == 2 and parts[1] == "start":
            cid = parts[0]
            return (200, start(cid)) if cid in CHALLENGES else (404, {"error": "없는 챌린지"})
        if method == "POST" and len(parts) == 2:
            cid, action = parts
            if cid not in CHALLENGES:
                return 404, {"error": "없는 챌린지"}
            if action == "visit":
                path = body.get("path")
                if not isinstance(path, str) or len(path) > 2048:
                    return 400, {"error": "path가 올바르지 않습니다."}
                raw, _, qs = path.partition("?")
                query = {}
                for pair in qs.split("&"):
                    if "=" in pair:
                        k, v = pair.split("=", 1)
                        query[k] = v
                data = body.get("data") if isinstance(body.get("data"), dict) else {}
                return 200, visit(cid, raw, query, data)
            if action == "hint":
                t = hint(cid, body.get("level"))
                return (200, {"text": t}) if t else (400, {"error": "힌트 번호 오류"})
            if action == "submit":
                return 200, submit(cid, body.get("flag", ""))
        return 404, {"error": "not found"}
    except Exception:  # noqa: BLE001 — 어떤 입력에도 500 대신 안전 실패
        return 400, {"error": "요청 처리 실패"}
