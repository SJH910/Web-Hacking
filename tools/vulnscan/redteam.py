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


# ====================================================================
# C4. 심부름꾼 — A10 SSRF · raw · 어려움
# ====================================================================
_SSRF_INTERNAL = re.compile(r"127\.0\.0\.1|localhost|0\.0\.0\.0|10\.\d|192\.168\.|169\.254\.|internal|metadata", re.I)
C4 = {
    "id": "errand", "title": "심부름꾼", "siteName": "링크 미리보기",
    "difficulty": "어려움", "owasp": "A10 SSRF", "tier": "raw",
    "session": {"user": "guest", "cookies": "(비로그인)"},
    "entry": "/preview",
    "allyOpening": "주소 넣으면 미리 보여주는 편한 기능이야. 외부 링크나 확인해.",
    "hints": ["이 기능은 서버가 네 '대신' 그 주소로 요청해. 외부 말고 내부 주소를 넣으면?",
              "127.0.0.1 이나 10.0.0.1 같은 내부 주소를 미리보기 해 봐.",
              "allowlist가 없어 내부망·메타데이터(169.254.169.254)까지 접근돼."],
    "flag": "FLAG{ssrf_internal_access}",
    "wrapUp": "서버가 입력 URL로 대신 요청 — SSRF. 대상 allowlist·내부/메타데이터 차단이 필요하다.",
}


def _c4(path, query, data):
    if path != "/preview":
        return _resp(404, "<p>없는 페이지입니다.</p>", title="404")
    url = (data or {}).get("url", query.get("url", ""))
    form = ("<h2>🔗 링크 미리보기</h2>"
            "<!-- 서버가 입력한 주소로 대신 요청합니다. allowlist 없음 -->"
            "<form data-rt action='/preview' method='get'>"
            "<input name='url' placeholder='http://example.test'>"
            "<button type='submit'>미리보기</button></form>")
    comments = ["서버가 입력한 주소로 대신 요청합니다. allowlist 없음"]
    if not url:
        return _resp(200, form, title="링크 미리보기", comments=comments)
    if _SSRF_INTERNAL.search(url):
        leak = ("<div class='rt-alert'>서버가 내부 주소로 대신 요청함 → 내부 관리 콘솔 응답: "
                "<b>FLAG{ssrf_internal_access}</b></div>")
        return _resp(200, form + leak, title="내부 응답", comments=comments, exploited=True, flag=True)
    return _resp(200, form + f"<div class='rt-reflect'>외부 미리보기 ‘{esc(url)}’ — 제목: 환영합니다</div>",
                 title="미리보기", comments=comments)


# ====================================================================
# C5. 숨은 문서고 — A01 강제 브라우징 · guided · 쉬움
# ====================================================================
C5 = {
    "id": "hidden-archive", "title": "숨은 문서고", "siteName": "사내 포털",
    "difficulty": "쉬움", "owasp": "A01 강제 브라우징", "tier": "guided",
    "session": {"user": "guest", "cookies": "(비로그인)"},
    "entry": "/",
    "allyOpening": "링크에 걸린 공개 문서만 보면 돼. 숨은 건 어차피 못 들어가.",
    "hints": ["검색엔진용 robots.txt에 '숨기고 싶은' 경로가 적혀 있기도 해.",
              "/robots.txt 를 열어 Disallow 경로를 확인해.",
              "Disallow에 적힌 경로로 주소창에 직접 쳐서 들어가 봐."],
    "flag": "FLAG{forced_browsing}",
    "wrapUp": "숨겼지만 접근 통제가 없는 경로 — 강제 브라우징(A01). 인증·인가로 보호해야 한다.",
}


def _c5(path, query, data):
    if path in ("/", "/home"):
        return _resp(200, "<h2>🏢 사내 포털</h2><ul class='rt-list'><li><a href='/docs'>공개 문서</a></li></ul>",
                     title="사내 포털")
    if path == "/robots.txt":
        return _resp(200, "<pre>User-agent: *\nDisallow: /admin-backup/</pre>", title="robots.txt",
                     comments=["Disallow: /admin-backup/ — 숨기려던 경로가 노출됨"])
    if path == "/docs":
        return _resp(200, "<h2>공개 문서</h2><ul class='rt-list'><li>사용 안내.pdf</li><li>복지 규정.pdf</li></ul>", title="문서")
    if path.startswith("/admin-backup"):
        return _resp(200, "<h2>백업 관리</h2><p>인증 없이 접근됨. 전체 백업·자격증명: <b>FLAG{forced_browsing}</b></p>",
                     title="백업 관리", owner="admin", exploited=True, flag=True)
    return _resp(404, "<p>없는 페이지입니다.</p>", title="404")


# ====================================================================
# C6. 바꿔치기 영수증 — A08 파라미터 변조 · mixed · 보통
# ====================================================================
C6 = {
    "id": "swap-receipt", "title": "바꿔치기 영수증", "siteName": "포인트 상점",
    "difficulty": "보통", "owasp": "A08 무결성(파라미터 변조)", "tier": "mixed",
    "session": {"user": "buyer", "cookies": "sid=sess_b7"},
    "entry": "/order",
    "allyOpening": "정가대로 결제하면 돼. 금액은 못 바꿔.",
    "hints": ["결제 금액이 폼의 input 값에 그대로 들어 있지? 서버가 그 값을 믿어.",
              "price 값을 0 이나 1 로 바꿔서 결제해 봐.",
              "클라이언트가 보낸 금액을 서버가 검증하지 않는 게 문제야."],
    "flag": "FLAG{price_tampering}",
    "wrapUp": "클라이언트가 보낸 금액을 서버가 그대로 신뢰 — 무결성 실패(A08). 서버에서 가격을 검증해야 한다.",
}


def _c6(path, query, data):
    if path == "/order":
        return _resp(200, "<h2>🛒 포인트 상점</h2><p>한정판 뱃지 — 정가 <b>10000</b>원</p>"
                     "<!-- 결제 금액을 클라이언트가 보냅니다(서버 미검증) -->"
                     "<form data-rt action='/checkout' method='get'>"
                     "<input name='price' value='10000'><button type='submit'>결제</button></form>",
                     title="포인트 상점", comments=["결제 금액을 클라이언트가 보냅니다(서버 미검증)"])
    if path == "/checkout":
        raw = (data or {}).get("price", query.get("price", "10000"))
        try:
            price = int(raw)
        except (TypeError, ValueError):
            return _resp(400, "<p>금액이 올바르지 않습니다.</p>", title="오류")
        if price < 10000:
            return _resp(200, f"<div class='rt-alert'>결제 완료: {price}원 — 서버가 금액을 검증하지 않음. "
                         "할인 쿠폰: <b>FLAG{price_tampering}</b></div>", title="결제 완료", exploited=True, flag=True)
        return _resp(200, f"<div class='rt-reflect'>결제 완료: {price}원</div>", title="결제 완료")
    return _resp(404, "<p>없는 페이지입니다.</p>", title="404")


# ====================================================================
# C7. 수다쟁이 에러 — A10 정보 노출 · guided · 쉬움
# ====================================================================
C7 = {
    "id": "chatty-error", "title": "수다쟁이 에러", "siteName": "금고",
    "difficulty": "쉬움", "owasp": "A10 정보 노출", "tier": "guided",
    "session": {"user": "guest", "cookies": "(비로그인)"},
    "entry": "/vault",
    "allyOpening": "번호만 제대로 넣으면 돼. 이상한 값 넣어봤자 그냥 오류야.",
    "hints": ["숫자 말고 이상한 값(문자·기호)을 넣으면 서버가 어떻게 반응할까?",
              "id 칸에 abc 나 ' 를 넣어 오류를 일으켜 봐.",
              "운영이라면 깔끔한 오류만 떠야 하는데, DEBUG가 켜져 상세 오류·경로가 노출돼."],
    "flag": "FLAG{verbose_error_leak}",
    "wrapUp": "상세 오류·스택·설정이 그대로 노출 — 정보 노출(A10). DEBUG off·커스텀 오류 페이지가 필요하다.",
}


def _c7(path, query, data):
    if path != "/vault":
        return _resp(404, "<p>없는 페이지입니다.</p>", title="404")
    raw = (data or {}).get("id", query.get("id", ""))
    form = ("<h2>🔐 금고</h2>"
            "<form data-rt action='/vault' method='get'>"
            "<input name='id' placeholder='금고 번호'><button type='submit'>열기</button></form>")
    if not raw:
        return _resp(200, form, title="금고")
    try:
        int(raw)
    except (TypeError, ValueError):
        err = ("<div class='rt-error'>500 Internal Server Error<br>Traceback (most recent call last) … "
               "DEBUG=True · settings: SECRET_KEY=dev-… · master_path=/vault/master<br>"
               "노출된 경로에서 발견: <b>FLAG{verbose_error_leak}</b></div>")
        return _resp(200, form + err, title="500 오류", exploited=True, flag=True)
    return _resp(200, form + f"<div class='rt-reflect'>금고 {esc(raw)}: 비어 있음</div>", title="금고")


# ====================================================================
# C8. 열린 창고 — A01/A05 경로 탐색 · mixed · 보통
# ====================================================================
C8 = {
    "id": "open-store", "title": "열린 창고", "siteName": "파일 보관함",
    "difficulty": "보통", "owasp": "A01 경로 탐색", "tier": "mixed",
    "session": {"user": "staff", "cookies": "sid=sess_s3"},
    "entry": "/files",
    "allyOpening": "목록에 있는 파일만 받으면 돼.",
    "hints": ["다운로드 주소에 파일명이 그대로 들어가지? 상위 폴더로 거슬러 올라가면?",
              "name 에 ../ 를 붙여 상위 경로(../../secret)를 요청해 봐.",
              "입력 경로를 제한하지 않아 서버 밖 파일까지 읽혀."],
    "flag": "FLAG{path_traversal}",
    "wrapUp": "입력 파일명으로 상위 경로 접근 — 경로 탐색. 경로 정규화·화이트리스트가 필요하다.",
}


def _c8(path, query, data):
    if path == "/files":
        return _resp(200, "<h2>📁 파일 보관함</h2>"
                     "<!-- 파일명을 그대로 경로에 붙입니다 -->"
                     "<ul class='rt-list'><li><a href='/download?name=guide.txt'>guide.txt</a></li>"
                     "<li><a href='/download?name=notice.txt'>notice.txt</a></li></ul>",
                     title="파일 보관함", comments=["파일명을 그대로 경로에 붙입니다"])
    if path == "/download":
        name = (data or {}).get("name", query.get("name", ""))
        if ".." in name:
            return _resp(200, f"<div class='rt-alert'>‘{esc(name)}’ 접근됨 — 서버 밖 파일 노출. "
                         "관리자 자격증명: <b>FLAG{path_traversal}</b></div>", title="경로 탐색",
                         exploited=True, flag=True)
        if name:
            return _resp(200, f"<div class='rt-reflect'>{esc(name)} 내용: (더미 텍스트)</div>", title=name)
        return _resp(400, "<p>파일명이 없습니다.</p>", title="오류")
    return _resp(404, "<p>없는 페이지입니다.</p>", title="404")


# ====================================================================
# C9. 저장된 속삭임 — A05 저장형 XSS · mixed · 보통
# ====================================================================
C9 = {
    "id": "stored-whisper", "title": "저장된 속삭임", "siteName": "방명록(영구)",
    "difficulty": "보통", "owasp": "A05 저장형 XSS", "tier": "mixed",
    "session": {"user": "guest", "cookies": "sid=sess_g9"},
    "entry": "/guestbook",
    "allyOpening": "글 남기면 그냥 저장되는 평범한 방명록이야.",
    "hints": ["남긴 글이 '그대로' 저장되어 다른 사람(관리자)에게도 보여.",
              "글 내용에 <script> 나 <svg onload=…> 같은 실행 태그를 넣어 저장해 봐.",
              "저장형 XSS는 관리자가 글을 '열람'할 때 그의 브라우저에서 실행돼."],
    "flag": "FLAG{stored_xss_admin}",
    "wrapUp": "저장된 입력이 이스케이프 없이 다시 출력 — 저장형 XSS. 출력 인코딩·CSP가 필요하다.",
}


def _c9(path, query, data):
    if path != "/guestbook":
        return _resp(404, "<p>없는 페이지입니다.</p>", title="404")
    msg = (data or {}).get("msg", query.get("msg", ""))
    form = ("<h2>📖 방명록</h2>"
            "<!-- 남긴 글이 그대로 저장·표시됩니다(이스케이프 없음) -->"
            "<form data-rt action='/guestbook' method='get'>"
            "<input name='msg' placeholder='방명록을 남겨보세요'><button type='submit'>남기기</button></form>"
            "<ul class='rt-list'><li>첫 방문 환영합니다!</li></ul>")
    comments = ["남긴 글이 그대로 저장·표시됩니다(이스케이프 없음)"]
    if not msg:
        return _resp(200, form, title="방명록", comments=comments)
    if _XSS_EXEC.search(msg):
        return _resp(200, form + "<div class='rt-alert'>글 저장됨. 잠시 후 <b>관리자</b>가 방명록을 열람 → "
                     "주입 스크립트 실행·세션 유출: <b>FLAG{stored_xss_admin}</b></div>",
                     title="방명록", comments=comments, exploited=True, flag=True)
    return _resp(200, form + f"<div class='rt-reflect'>글 저장됨: ‘{msg}’</div>", title="방명록", comments=comments)


# ====================================================================
# C10. 뒤바뀐 역할 — A08/A01 권한 변조 · mixed · 보통
# ====================================================================
C10 = {
    "id": "swapped-role", "title": "뒤바뀐 역할", "siteName": "직원 대시보드",
    "difficulty": "보통", "owasp": "A08 권한 변조", "tier": "mixed",
    "session": {"user": "user", "cookies": "sid=sess_u10; role=user"},
    "entry": "/dash",
    "allyOpening": "넌 일반 사용자라 관리 메뉴는 못 봐.",
    "hints": ["대시보드가 네 역할(role)을 '요청 값'으로 받고 있어.",
              "/panel?role=admin 처럼 role 값을 바꿔서 접근해 봐.",
              "클라이언트가 보낸 역할을 서버가 그대로 믿는 게 문제야."],
    "flag": "FLAG{role_tampering}",
    "wrapUp": "클라이언트가 보낸 역할 값을 서버가 신뢰 — 권한 변조(A08). 권한은 서버 세션으로만 판단해야.",
}


def _c10(path, query, data):
    if path == "/dash":
        return _resp(200, "<h2>🗂️ 직원 대시보드</h2><p>현재 역할: <b>user</b></p>"
                     "<!-- 역할을 요청 파라미터 role 로 받습니다 -->"
                     "<form data-rt action='/panel' method='get'>"
                     "<input name='role' value='user'><button type='submit'>관리 패널 열기</button></form>",
                     title="대시보드", comments=["역할을 요청 파라미터 role 로 받습니다"])
    if path == "/panel":
        role = (data or {}).get("role", query.get("role", "user"))
        if role in ("admin", "staff", "manager"):
            return _resp(200, f"<div class='rt-alert'>role={esc(role)} 로 관리 패널 접근됨. "
                         "관리 토큰: <b>FLAG{role_tampering}</b></div>", title="관리 패널", exploited=True, flag=True)
        return _resp(200, "<div class='rt-error'>403 · 권한 없음(user)</div>", title="403")
    return _resp(404, "<p>없는 페이지입니다.</p>", title="404")


# ====================================================================
# C11. 느린 자백 — A03 시간 기반 블라인드 SQLi · raw · 어려움
# ====================================================================
_BLIND = re.compile(r"sleep\s*\(|waitfor\s+delay|pg_sleep|benchmark\s*\(", re.I)
C11 = {
    "id": "slow-confession", "title": "느린 자백", "siteName": "재고 조회",
    "difficulty": "어려움", "owasp": "A03 블라인드 SQLi(시간)", "tier": "raw",
    "session": {"user": "guest", "cookies": "(비로그인)"},
    "entry": "/stock",
    "allyOpening": "재고 수만 보여주는 조회야. 숫자만 넣으면 돼.",
    "hints": ["화면 결과는 같아도 '응답 시간'이 입력에 따라 달라질 수 있어.",
              "id 에 1 AND sleep(3) 같은 지연 구문을 주입해 봐.",
              "내용 차이 없이 '시간'만으로 참/거짓을 판별하는 게 블라인드 SQLi야."],
    "flag": "FLAG{time_based_sqli}",
    "wrapUp": "내용은 같고 응답 시간만 달라짐 — 시간 기반 블라인드 SQLi. 파라미터 바인딩이 필요하다.",
}


def _c11(path, query, data):
    if path != "/stock":
        return _resp(404, "<p>없는 페이지입니다.</p>", title="404")
    raw = (data or {}).get("id", query.get("id", ""))
    form = ("<h2>📦 재고 조회</h2>"
            "<form data-rt action='/stock' method='get'>"
            "<input name='id' placeholder='상품 번호'><button type='submit'>조회</button></form>")
    if not raw:
        return _resp(200, form, title="재고 조회")
    if _BLIND.search(raw):
        return _resp(200, form + "<div class='rt-alert'>재고: 42개 · <b>응답시간 3.01s</b> — "
                     "화면은 같지만 입력이 지연을 유발(블라인드 SQLi). 추출 플래그: <b>FLAG{time_based_sqli}</b></div>",
                     title="재고", exploited=True, flag=True)
    return _resp(200, form + f"<div class='rt-reflect'>재고: 42개 · 응답시간 0.02s (질의 {esc(raw)})</div>", title="재고")


# ====================================================================
# C12. 예측된 열쇠 — A07 약한 세션(예측 가능) · mixed · 보통
# ====================================================================
C12 = {
    "id": "guessed-key", "title": "예측된 열쇠", "siteName": "주문 조회",
    "difficulty": "보통", "owasp": "A07 인증 실패(약한 세션)", "tier": "mixed",
    "session": {"user": "customer", "cookies": "sid=1007"},
    "entry": "/mysession",
    "allyOpening": "네 세션으로 네 주문만 볼 수 있어.",
    "hints": ["세션 번호(sid)가 순차적이라 다른 번호를 추측할 수 있어.",
              "/order?sid=1000 처럼 작은(관리자) 번호로 바꿔 조회해 봐.",
              "예측 가능한 세션 식별자는 타인 세션 탈취로 이어져."],
    "flag": "FLAG{predictable_session}",
    "wrapUp": "순차·예측 가능한 세션 번호로 타인 세션 접근 — 인증 실패(A07). 추측 불가한 난수 토큰이 필요하다.",
}


def _c12(path, query, data):
    if path == "/mysession":
        return _resp(200, "<h2>🧾 주문 조회</h2><p>내 세션: <b>sid=1007</b></p>"
                     "<!-- 세션 번호가 순차적입니다 -->"
                     "<form data-rt action='/order' method='get'>"
                     "<input name='sid' value='1007'><button type='submit'>주문 보기</button></form>",
                     title="주문 조회", comments=["세션 번호가 순차적입니다"])
    if path == "/order":
        sid = (data or {}).get("sid", query.get("sid", "1007"))
        if sid and sid != "1007":
            tag = "관리자" if sid in ("1000", "1", "1001") else "타인"
            return _resp(200, f"<div class='rt-alert'>sid={esc(sid)}({tag}) 세션으로 주문 열람됨 — "
                         "세션 탈취 성공: <b>FLAG{predictable_session}</b></div>", title="타인 주문",
                         exploited=True, flag=True)
        return _resp(200, "<div class='rt-reflect'>내 주문: 커피 1잔</div>", title="내 주문")
    return _resp(404, "<p>없는 페이지입니다.</p>", title="404")


# ====================================================================
# C13. 평문의 문 — A04 민감정보 평문 노출 · guided · 쉬움
# ====================================================================
C13 = {
    "id": "plaintext-door", "title": "평문의 문", "siteName": "결제 영수증",
    "difficulty": "쉬움", "owasp": "A04 민감정보 평문", "tier": "guided",
    "session": {"user": "buyer", "cookies": "sid=sess_b13"},
    "entry": "/receipt",
    "allyOpening": "영수증이야. 결제만 확인하면 돼.",
    "hints": ["영수증 '상세 보기'를 열어 응답 본문을 끝까지 확인해 봐.",
              "민감정보(카드번호)가 마스킹 없이 평문으로 들어 있을 수 있어.",
              "전송·저장 시 민감정보는 마스킹·암호화돼야 하는데 그대로 노출돼."],
    "flag": "FLAG{sensitive_plaintext}",
    "wrapUp": "응답 본문에 카드번호가 평문 노출 — 민감정보 보호 실패(A04). 마스킹·암호화 저장이 필요하다.",
}


def _c13(path, query, data):
    if path == "/receipt":
        return _resp(200, "<h2>🧾 결제 영수증</h2><ul class='rt-list'>"
                     "<li><a href='/receipt/view'>영수증 상세 보기</a></li></ul>", title="영수증")
    if path == "/receipt/view":
        return _resp(200, "<h2>영수증 #8842</h2><p>금액 12,000원 · 승인</p>"
                     "<div class='rt-alert'>본문에 카드번호 평문 노출: 4111-1111-1111-1111 — "
                     "<b>FLAG{sensitive_plaintext}</b></div>", title="영수증 상세", exploited=True, flag=True)
    return _resp(404, "<p>없는 페이지입니다.</p>", title="404")


# ====================================================================
# C14. 틈새 명령 — A05 명령 주입 · raw · 어려움
# ====================================================================
_CMDI = re.compile(r"[;|&`]|\$\(")
C14 = {
    "id": "command-gap", "title": "틈새 명령", "siteName": "네트워크 도구",
    "difficulty": "어려움", "owasp": "A05 명령 주입", "tier": "raw",
    "session": {"user": "admin-tool", "cookies": "sid=sess_t14"},
    "entry": "/ping",
    "allyOpening": "주소 넣으면 ping 쳐주는 도구야. 호스트만 넣어.",
    "hints": ["입력한 host가 서버의 ping 명령에 '그대로' 들어가.",
              "host 에 example.test; whoami 처럼 ; | && 로 명령을 이어붙여 봐.",
              "입력이 셸 명령으로 해석되면 OS 명령 주입이야."],
    "flag": "FLAG{command_injection}",
    "wrapUp": "입력이 셸 명령에 그대로 삽입 — OS 명령 주입(A05). 입력 검증·셸 미사용(인자 분리)이 필요하다.",
}


def _c14(path, query, data):
    if path != "/ping":
        return _resp(404, "<p>없는 페이지입니다.</p>", title="404")
    host = (data or {}).get("host", query.get("host", ""))
    form = ("<h2>🛰️ 네트워크 도구</h2>"
            "<!-- host 를 그대로 ping 명령에 넣습니다 -->"
            "<form data-rt action='/ping' method='get'>"
            "<input name='host' placeholder='example.test'><button type='submit'>ping</button></form>")
    comments = ["host 를 그대로 ping 명령에 넣습니다"]
    if not host:
        return _resp(200, form, title="네트워크 도구", comments=comments)
    if _CMDI.search(host):
        return _resp(200, form + "<div class='rt-alert'>명령 주입 실행됨 → <code>uid=0(root)</code> · "
                     "<b>FLAG{command_injection}</b></div>", title="명령 주입", comments=comments,
                     exploited=True, flag=True)
    return _resp(200, form + f"<div class='rt-reflect'>PING {esc(host)} … 64 bytes, 응답 정상</div>",
                 title="ping", comments=comments)


CHALLENGES = {"c1": C1, "c2": C2, "c3": C3, "c4": C4, "c5": C5, "c6": C6, "c7": C7, "c8": C8,
              "c9": C9, "c10": C10, "c11": C11, "c12": C12, "c13": C13, "c14": C14}
_VISITORS = {"c1": _c1, "c2": _c2, "c3": _c3, "c4": _c4, "c5": _c5, "c6": _c6, "c7": _c7, "c8": _c8,
             "c9": _c9, "c10": _c10, "c11": _c11, "c12": _c12, "c13": _c13, "c14": _c14}
ORDER = ["c1", "c2", "c3", "c4", "c5", "c6", "c7", "c8", "c9", "c10", "c11", "c12", "c13", "c14"]


def catalog():
    return [{"id": cid, "title": CHALLENGES[cid]["title"], "owasp": CHALLENGES[cid]["owasp"],
             "difficulty": CHALLENGES[cid]["difficulty"], "tier": CHALLENGES[cid]["tier"]}
            for cid in ORDER]


# ---- 등반: 10층(풀이 더 크면 랜덤 10개 추출). 시드 결정적·중복 없음 → 이어하기·공정성(X3) ----
MAX_FLOORS = 10


def _floors():
    return min(MAX_FLOORS, len(ORDER))


def _order(seed):
    o = list(ORDER)
    random.Random(str(seed)).shuffle(o)
    return o[:_floors()]


def climb():
    """새 등반 시작: 시드 발급. 풀에서 랜덤 10개를 뽑아 출제(시드로 재현, FE에 미리 노출 안 함)."""
    return {"seed": secrets.token_hex(4), "floors": _floors()}


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
