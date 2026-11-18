"""OWASP A01~A10 점검.

각 함수는 finding dict 리스트를 반환한다:
  {owasp, title, severity, status, evidence, note}
  severity: critical|high|medium|low|info
  status:   vuln(취약 확인) | safe(양호) | manual(수동/화이트박스 필요) | error

정직성 원칙: 원격 스캔으로 자동 탐지 가능한 것만 vuln/safe로 판정한다.
소스·서버 접근이 필요한 항목(A03·A06·A08·A09 등)은 manual로 표시해 과장하지 않는다.
"""
import html
import re
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse

from safeguards import guarded_request, BlockedTarget

SECURITY_HEADERS = {
    "content-security-policy": "A02",
    "x-frame-options": "A02",
    "x-content-type-options": "A02",
    "referrer-policy": "A02",
    "strict-transport-security": "A04",
}

# 반사형 XSS 탐지용 마커(스크립트 실행 아님 — 반사 여부만 확인)
XSS_MARKER = "vulnscan<x7y>"
# SQL 오류 유발 입력
SQL_PROBE = "'"
SQL_ERROR_SIGNS = [
    "you have an error in your sql syntax", "unclosed quotation mark",
    "sqlite3.", "near \"", "sql syntax", "psycopg2", "ORA-0", "SQLSTATE",
    "OperationalError", "ProgrammingError",
]
DEBUG_SIGNS = ["Traceback (most recent call last)", "Django Version",
               "You're seeing this error because", "Request Method:",
               "Werkzeug Debugger", "Whitman", "Using the URLconf"]


def _f(owasp, title, severity, status, evidence="", note=""):
    return {"owasp": owasp, "title": title, "severity": severity,
            "status": status, "evidence": evidence, "note": note}


# ---------- A02 설정 / 정보 노출 ----------
def check_a02(base, resp, **kw):
    out = []
    h = {k.lower(): v for k, v in resp["headers"].items()}
    for name, cat in SECURITY_HEADERS.items():
        if cat != "A02":
            continue
        if name not in h:
            out.append(_f("A02", f"보안 헤더 누락: {name}", "low", "vuln",
                          evidence=f"응답에 {name} 없음"))
        else:
            out.append(_f("A02", f"보안 헤더 있음: {name}", "info", "safe",
                          evidence=f"{name}: {h[name][:80]}"))
    server = h.get("server", "")
    if server and re.search(r"\d", server):
        out.append(_f("A02", "서버 버전 노출", "low", "vuln",
                      evidence=f"Server: {server}"))
    xpb = h.get("x-powered-by")
    if xpb:
        out.append(_f("A02", "X-Powered-By 노출", "low", "vuln", evidence=f"X-Powered-By: {xpb}"))
    return out


# ---------- A04 암호화 / 전송 보호 ----------
def check_a04(base, resp, **kw):
    out = []
    scheme = urlparse(resp["url"]).scheme
    if scheme == "http":
        out.append(_f("A04", "평문(HTTP) 전송", "medium", "vuln",
                      evidence=f"{resp['url']} — HTTPS 아님",
                      note="자격증명·쿠키가 평문 구간에서 노출될 수 있음"))
    h = {k.lower(): v for k, v in resp["headers"].items()}
    # Set-Cookie 플래그 (헤더가 합쳐졌을 수 있어 조각으로 검사)
    setck = h.get("set-cookie", "")
    for m in re.finditer(r"([A-Za-z0-9_\-]+)=", setck):
        name = m.group(1)
        seg = setck  # urllib은 쿠키를 콤마로 합치므로 전체 문자열 기준으로 플래그 유무만 본다
        flags = []
        if "httponly" not in seg.lower():
            flags.append("HttpOnly 없음")
        if "secure" not in seg.lower():
            flags.append("Secure 없음")
        if flags:
            out.append(_f("A04", f"쿠키 보호 플래그 미흡: {name}", "medium", "vuln",
                          evidence=f"{name}: {', '.join(flags)}",
                          note="쿠키별 정확한 플래그는 로그인 응답까지 확인 권장"))
        break  # 대표 1건만 (중복 방지)
    if scheme == "http" and "strict-transport-security" not in h:
        out.append(_f("A04", "HSTS 없음", "low", "vuln", evidence="Strict-Transport-Security 헤더 없음"))
    return out


# ---------- A10 예외 처리 (DEBUG/상세 오류 노출) ----------
def check_a10(base, resp, limiter=None, **kw):
    out = []
    # 존재할 법하지 않은 경로/잘못된 타입으로 오류 유도 (GET, 비파괴적)
    probe = base.rstrip("/") + "/vulnscan_nonexistent_zzz/"
    r = guarded_request(probe, limiter=limiter)
    body = r.get("body", "")
    hit = [s for s in DEBUG_SIGNS if s in body]
    if hit:
        out.append(_f("A10", "상세 오류/DEBUG 페이지 노출", "high", "vuln",
                      evidence=f"{probe} → {r['status']}, 흔적: {hit[0]}",
                      note="운영에서 DEBUG=off, 커스텀 오류 페이지 필요"))
    else:
        out.append(_f("A10", "오류 페이지에서 디버그 흔적 없음", "info", "safe",
                      evidence=f"{probe} → {r['status']}"))
    return out


# ---------- A05 인젝션 (반사형 XSS / SQL 오류) : 능동 ----------
def check_a05(base, resp, pages=None, limiter=None, excludes=None, **kw):
    out = []
    targets = _param_urls(pages or [])
    if not targets:
        out.append(_f("A05", "주입 지점(GET 파라미터) 없음", "info", "manual",
                      note="크롤에서 쿼리 파라미터를 못 찾음. 로그인 후 폼은 수동 점검 필요"))
        return out
    xss_found = sqli_found = False
    for url, param in targets[:30]:
        if xss_found and sqli_found:
            break
        try:
            _probe_param(url, param, out, limiter, excludes,
                         xss_found, sqli_found)
        except BlockedTarget:
            continue  # 제외 지점은 건너뛰고 다음 파라미터로
        # out에 추가됐는지로 발견 여부 갱신
        xss_found = any(f["title"].startswith("반사형 XSS") for f in out)
        sqli_found = any("SQL 인젝션" in f["title"] for f in out)
    if not out:
        out.append(_f("A05", "반사형 XSS·SQL 오류 미검출", "info", "safe",
                      note="오류/불리언 기반만 점검함. 블라인드/저장형은 수동 필요"))
    return out


def _probe_param(url, param, out, limiter, excludes, xss_found, sqli_found):
    # 반사형 XSS
    if not xss_found:
        r = guarded_request(_set_param(url, param, XSS_MARKER),
                            limiter=limiter, active=True, excludes=excludes)
        if r.get("body") and XSS_MARKER in r["body"] and html.escape(XSS_MARKER) not in r["body"]:
            out.append(_f("A05", "반사형 XSS 가능", "high", "vuln",
                          evidence=f"{param} 파라미터, 마커가 이스케이프 없이 반사됨: {r['url']}"))
    # SQL 인젝션 — 오류 기반 + 불리언 기반
    if not sqli_found:
        r = guarded_request(_set_param(url, param, SQL_PROBE),
                            limiter=limiter, active=True, excludes=excludes)
        low = (r.get("body") or "").lower()
        sign = next((s for s in SQL_ERROR_SIGNS if s.lower() in low), None)
        if sign:
            out.append(_f("A05", "SQL 인젝션 가능(오류 기반)", "critical", "vuln",
                          evidence=f"{param} 파라미터에 ' 주입 시 SQL 오류 노출: '{sign}'"))
        else:
            hit = _boolean_sqli(url, param, limiter, excludes)
            if hit:
                out.append(_f("A05", "SQL 인젝션 가능(불리언 기반)", "critical", "vuln",
                              evidence=hit,
                              note="참 조건과 거짓 조건의 응답이 다름 → 입력이 SQL 논리에 주입됨"))


# ---------- A01 접근통제 (IDOR 힌트) : 능동(약) ----------
def check_a01(base, resp, pages=None, limiter=None, excludes=None, **kw):
    out = []
    # 숫자 pk로 보이는 경로(.../<n>/)를 찾아 비로그인 접근 가능 여부만 가볍게 본다
    cand = [u for u in (pages or []) if re.search(r"/\d+/?($|\?)", urlparse(u).path)]
    if not cand:
        out.append(_f("A01", "숫자 ID 경로 미발견", "info", "manual",
                      note="IDOR는 인증·소유권 맥락이 필요해 수동 진단 권장(S1 영역)"))
        return out
    sample = cand[0]
    r = guarded_request(sample, limiter=limiter, active=True, excludes=excludes)
    if r.get("status") == 200:
        out.append(_f("A01", "숫자 ID 리소스가 인증 없이 200", "medium", "manual",
                      evidence=f"{sample} → 200",
                      note="소유권 검사 누락 여부는 다른 사용자 세션으로 교차 확인 필요(수동)"))
    out.append(_f("A01", "SSRF·권한우회는 수동 진단", "info", "manual",
                  note="SSRF(/embed 등)는 제외 경로라 자동 공격하지 않음. 통제된 수동 점검"))
    return out


# ---------- 원격 스캔으로 판정 불가한 항목 ----------
def check_manual_only(base, resp, **kw):
    return [
        _f("A03", "공급망(의존성)", "info", "manual",
           note="requirements.txt 등 의존성 파일을 pip-audit/npm audit로 점검(원격 스캔 불가)"),
        _f("A06", "안전하지 않은 설계", "info", "manual",
           note="재설정 토큰 예측성 등 설계 결함은 로직 분석 필요"),
        _f("A07", "인증 실패", "info", "manual",
           note="로그인 시도 제한·세션 고정은 로그인 흐름 대상 수동 점검(무차별 대입은 이 도구 범위 밖)"),
        _f("A08", "무결성 실패", "info", "manual",
           note="업로드 검증·쿠키 권한값은 기능별 수동 점검"),
        _f("A09", "로깅·경보", "info", "manual",
           note="로그인 실패·민감조회 기록 여부는 서버 로그 관찰 필요(원격 불가)"),
    ]


# ---------- 유틸 ----------
def _param_urls(pages):
    seen, out = set(), []
    for u in pages:
        qs = parse_qs(urlparse(u).query)
        for p in qs:
            key = (urlparse(u).path, p)
            if key not in seen:
                seen.add(key)
                out.append((u, p))
    return out


def _boolean_sqli(url, param, limiter, excludes):
    """참 조건 vs 거짓 조건 주입의 응답 차이로 SQLi 판정. 반환: 증거 문자열 또는 None.

    두 입력 모두 같은 접두어로 시작하므로(검색어 자체 효과 상쇄), 응답 길이 차이는
    SQL 논리 해석 차이에서만 나온다 → 오탐이 낮다.
    """
    # 참: 작은따옴표로 문자열을 닫고 OR 참 → LIKE '%'가 전체 매칭
    # 거짓: 같은 구조에 AND 거짓 → 결과 없음
    # 두 입력 모두 주입 구문이므로, 응답 차이는 SQL 논리 해석에서만 나온다.
    t = guarded_request(_set_param(url, param, "' OR '1'='1"),
                        limiter=limiter, active=True, excludes=excludes)
    f = guarded_request(_set_param(url, param, "' AND '1'='2"),
                        limiter=limiter, active=True, excludes=excludes)
    bt, bf = t.get("body") or "", f.get("body") or ""
    if not bt or not bf or t.get("status") != 200 or f.get("status") != 200:
        return None
    # 참(전체 반환)이 거짓(빈 결과)보다 충분히 길면 주입 성립
    if len(bt) - len(bf) > 80:
        return (f"{param}: 참 조건(' OR '1'='1) 응답 {len(bt)}B > "
                f"거짓 조건(' AND '1'='2) 응답 {len(bf)}B, 차이 {len(bt)-len(bf)}B")
    return None


def _set_param(url, param, value):
    parts = urlparse(url)
    qs = parse_qs(parts.query)
    qs[param] = [value]
    return urlunparse(parts._replace(query=urlencode(qs, doseq=True)))


PASSIVE = [check_a02, check_a04]
ACTIVE = [check_a10, check_a05, check_a01]
ALWAYS = [check_manual_only]
