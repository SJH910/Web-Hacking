"""안전장치 — 이 도구는 학습용 격리 환경 전용이다.

모든 HTTP 요청은 반드시 guarded_request()를 거친다. 여기서 대상 호스트를
허가 목록으로 제한하고, 능동 모드에서 제외 경로를 막고, 속도·총량을 제한한다.
이 파일을 우회해 요청을 보내는 코드를 만들지 말 것.
"""
import ipaddress
import re
import socket
import threading
import time
import urllib.request
import urllib.error
from urllib.parse import urlparse

# --- 허가된 대상 호스트 (이 외에는 전부 거부) ---
# 로컬 랩만. 외부 공인 주소는 차단한다.
ALLOWED_HOSTNAMES = {"127.0.0.1", "localhost", "::1", "web", "jiacenter-vuln-web-1"}


def _ip_class(ip) -> str:
    """ip 객체를 local/public/blocked로 분류.
    주의: 169.254.x(링크로컬)는 파이썬에서 is_private 도 True 이므로, 반드시
    링크로컬/예약/멀티캐스트를 '먼저' 차단한 뒤 사설 여부를 본다."""
    # 링크로컬(169.254.x — 클라우드 메타데이터 포함)·멀티캐스트·예약·미지정은 차단
    if ip.is_link_local or ip.is_multicast or ip.is_reserved or ip.is_unspecified:
        return "blocked"
    if ip.is_loopback or ip.is_private:
        return "local"
    return "public"


def classify_host(url: str):
    """대상 호스트를 분류한다. 반환: (kind, reason)
      - "local"  : 루프백/사설/허가 목록 — 능동(공격) 스캔 허용
      - "public" : 공개 인터넷 호스트 — 수동(관찰) 분석만 허용
      - "blocked": 호스트 없음·DNS 실패·링크로컬/예약 주소 — 요청 금지
    """
    host = (urlparse(url).hostname or "").lower()
    if not host:
        return ("blocked", "호스트가 없습니다")
    if host in ALLOWED_HOSTNAMES:
        return ("local", "")
    # 숫자 IP
    try:
        return (_ip_class(ipaddress.ip_address(host)), "")
    except ValueError:
        pass
    # 호스트명 → 실제 해석 결과로 분류 (DNS 리바인딩성 내부 우회 방지)
    try:
        return (_ip_class(ipaddress.ip_address(socket.gethostbyname(host))), "")
    except OSError:
        return ("blocked", "DNS 조회에 실패했습니다")


def host_allowed(url: str) -> bool:
    """요청을 보내도 되는 대상인지(local 또는 public). blocked만 거부."""
    return classify_host(url)[0] != "blocked"


def is_local(url: str) -> bool:
    """능동(공격) 스캔이 허용되는 로컬/사설 대상인지."""
    return classify_host(url)[0] == "local"


# 절대 차단 — passive·active 무관하게 아예 요청하지 않는다.
# GET만으로도 부작용(외부 요청·세션 종료·삭제·초기화)이 나는 경로.
ALWAYS_BLOCK = [
    r"/embed",                       # SSRF — 서버가 입력 URL로 외부 요청
    r"/logout",
    r"/(delete|remove|reset|drop|shutdown|wipe)",
    r"/board/posts/\d+/(edit|delete)",
]

# 능동 모드 제외 경로 — passive 크롤·관찰은 하되 공격 페이로드는 보내지 않는다.
# 사용자가 UI에서 추가/수정 가능.
DEFAULT_EXCLUDES = ALWAYS_BLOCK + [
    r"/admin(/|$)",
    r"/signup",
    r"/attendance",
    r"/board/posts/new",
    r"/my(/|$)",
]


class Limiter:
    """속도 제한 + 총 요청 수 상한. 스캔 세션마다 하나."""

    def __init__(self, min_interval=0.2, max_requests=800):
        self.min_interval = min_interval
        self.max_requests = max_requests
        self.count = 0
        self._last = 0.0
        self._lock = threading.Lock()

    def gate(self):
        with self._lock:
            if self.count >= self.max_requests:
                raise LimitExceeded(f"요청 상한({self.max_requests}) 도달 — 스캔 중단")
            wait = self.min_interval - (time.monotonic() - self._last)
            if wait > 0:
                time.sleep(wait)
            self._last = time.monotonic()
            self.count += 1


class LimitExceeded(Exception):
    pass


class BlockedTarget(Exception):
    pass


def path_excluded(url: str, patterns) -> bool:
    path = urlparse(url).path or "/"
    return any(re.search(p, path) for p in patterns)


def guarded_request(url, *, method="GET", data=None, headers=None, cookies=None,
                    limiter=None, active=False, excludes=None, timeout=8,
                    allow_blocked=False):
    """모든 요청의 단일 통로. 안전장치를 통과한 요청만 실제로 나간다.

    - active=True 인데 제외 경로면 BlockedTarget.
    - 허가되지 않은 호스트면 BlockedTarget.
    - limiter로 속도·총량 제한.
    - allow_blocked=True 는 '실습 콘솔'의 명시적 opt-in에서만 쓴다. ALWAYS_BLOCK
      (파괴·SSRF) 경로를 허용하되, 호스트 제한(로컬/사설)은 절대 풀지 않는다.
    반환: dict(status, headers(dict), body(str), url, elapsed)  또는 error.
    """
    kind, reason = classify_host(url)
    if kind == "blocked":
        raise BlockedTarget(f"차단된 대상: {url} ({reason or '허용되지 않는 주소'})")
    # 공개 사이트에는 능동(공격) 요청을 보내지 않는다 — 인가 없는 공격은 불법.
    if active and kind != "local":
        raise BlockedTarget(
            "능동(공격) 스캔은 로컬/사설 대상에만 허용됩니다. "
            "공개 사이트는 수동(passive) 분석만 가능합니다(인가 없는 공격은 불법).")
    # 절대 차단 경로: 기본은 passive·active 무관하게 아예 요청하지 않는다.
    # allow_blocked 는 사용자가 실습 콘솔에서 경고에 동의한 경우에만 True.
    if path_excluded(url, ALWAYS_BLOCK) and not allow_blocked:
        raise BlockedTarget(f"차단 경로(부작용 위험, 요청 안 함): {url}")
    if active and excludes and path_excluded(url, excludes):
        raise BlockedTarget(f"제외 경로(능동 스캔 금지): {url}")
    if limiter:
        limiter.gate()

    hdrs = {"User-Agent": "vulnscan-edu/0.2 (educational security analyzer)"}
    if headers:
        hdrs.update(headers)
    if cookies:
        hdrs["Cookie"] = "; ".join(f"{k}={v}" for k, v in cookies.items())

    body = data.encode() if isinstance(data, str) else data
    req = urllib.request.Request(url, data=body, headers=hdrs, method=method)
    t0 = time.monotonic()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read(2_000_000)  # 2MB 상한
            return _pack(resp.status, resp.headers, raw, resp.geturl(), t0)
    except urllib.error.HTTPError as e:
        raw = e.read(2_000_000) if hasattr(e, "read") else b""
        return _pack(e.code, e.headers, raw, url, t0)
    except (urllib.error.URLError, socket.timeout, OSError) as e:
        return {"error": str(e), "url": url, "status": 0, "headers": {}, "body": "",
                "elapsed": round(time.monotonic() - t0, 3)}


def _pack(status, headers, raw, url, t0):
    try:
        text = raw.decode("utf-8", errors="replace")
    except Exception:
        text = ""
    return {
        "status": status,
        "headers": {k: v for k, v in headers.items()},
        "body": text,
        "url": url,
        "elapsed": round(time.monotonic() - t0, 3),
        "error": None,
    }
