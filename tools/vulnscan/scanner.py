#!/usr/bin/env python3
"""웹페이지 취약점 분석 도구 — 로컬 백엔드 + 대시보드.

학습용 격리 환경 전용. 대상은 로컬/사설 호스트만 허용(safeguards.py).

실행:
    python3 scanner.py            # http://127.0.0.1:8900 에서 대시보드 열림
    python3 scanner.py --port 8901

대시보드에서 대상 URL·모드(passive/active)를 넣고 스캔한다.
"""
import argparse
import json
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urljoin, urlparse

import checks
from llm_review import review_one_a05
from safeguards import (ALWAYS_BLOCK, DEFAULT_EXCLUDES, Limiter, LimitExceeded,
                        BlockedTarget, guarded_request, host_allowed, path_excluded,
                        classify_host, is_local)

STATIC = Path(__file__).parent / "static"
LINK_RE = re.compile(r'(?:href|action|src)=["\']([^"\'#]+)["\']', re.I)
FORM_RE = re.compile(r'<form\b[^>]*>(.*?)</form>', re.I | re.S)
FORM_ACTION_RE = re.compile(r'action=["\']([^"\']*)["\']', re.I)
FORM_METHOD_RE = re.compile(r'method=["\']([^"\']*)["\']', re.I)
INPUT_NAME_RE = re.compile(r'<(?:input|textarea|select)\b[^>]*\bname=["\']([^"\']+)["\']', re.I)


def _forms_to_param_urls(base_url, body):
    """GET 폼에서 (action?필드=TEST) URL을 만들어 주입 지점으로 쓴다."""
    urls = []
    for fm in FORM_RE.finditer(body or ""):
        block = fm.group(0)
        method = (FORM_METHOD_RE.search(block) or [None, "get"])[1].lower() \
            if FORM_METHOD_RE.search(block) else "get"
        if method != "get":
            continue  # POST 폼은 자동 제출하지 않음(부작용 방지)
        am = FORM_ACTION_RE.search(block)
        action = urljoin(base_url, am.group(1)) if am and am.group(1) else base_url
        names = INPUT_NAME_RE.findall(block)
        if not names:
            continue
        q = "&".join(f"{n}=TEST" for n in names)
        urls.append(action + ("&" if urlparse(action).query else "?") + q)
    return urls


def crawl(base, limiter, max_pages=40, excludes=None):
    """같은 호스트만, 얕게 크롤해 페이지·파라미터 URL을 모은다. GET만.
    절대 차단 경로는 아예 요청하지 않고, GET 폼의 파라미터도 주입 지점으로 수집."""
    root = urlparse(base)
    seen, queue, pages = set(), [base], []
    while queue and len(pages) < max_pages:
        url = queue.pop(0)
        if url in seen:
            continue
        seen.add(url)
        if not host_allowed(url) or path_excluded(url, ALWAYS_BLOCK):
            continue
        try:
            r = guarded_request(url, limiter=limiter)
        except BlockedTarget:
            continue
        if r.get("error") or not r.get("body"):
            pages.append(url)
            continue
        pages.append(r["url"])
        ctype = r["headers"].get("Content-Type", "")
        if "html" not in ctype.lower():
            continue
        for found in _forms_to_param_urls(r["url"], r["body"]):
            if found not in pages:
                pages.append(found)
        for m in LINK_RE.finditer(r["body"]):
            link = urljoin(url, m.group(1))
            p = urlparse(link)
            if p.scheme not in ("http", "https") or p.netloc != root.netloc:
                continue
            link = p._replace(fragment="").geturl()
            if link not in seen and link not in queue:
                queue.append(link)
    return pages


def run_scan(target, mode, extra_excludes, rate, max_requests):
    """스캔 실행 → 결과 dict."""
    if not target.startswith(("http://", "https://")):
        target = "http://" + target
    kind, reason = classify_host(target)
    if kind == "blocked":
        return {"ok": False, "error": f"차단된 대상입니다: {target}\n{reason or '허용되지 않는 주소'}"}
    active = (mode == "active")
    # 공개 사이트는 수동 분석만. 능동(공격)은 로컬/사설 대상에만.
    if active and kind != "local":
        return {"ok": False, "error":
                f"'{target}' 은(는) 공개 사이트로 보입니다.\n"
                "능동(공격) 스캔은 로컬/사설 대상에만 허용됩니다 — 인가 없는 공격은 불법입니다.\n"
                "공개 사이트는 수동(passive) 모드로 분석하세요(헤더·쿠키·버전 노출 등 비침투 점검)."}

    excludes = list(DEFAULT_EXCLUDES) + [e for e in (extra_excludes or []) if e.strip()]
    limiter = Limiter(min_interval=max(0.05, rate), max_requests=max_requests)
    findings, log = [], []
    log.append("공개 사이트 — 수동(비침투) 분석만 수행합니다." if kind == "public"
               else "로컬/사설 대상.")
    try:
        root = guarded_request(target, limiter=limiter)
        if root.get("error"):
            return {"ok": False, "error": f"대상에 접근 실패: {root['error']}"}
        log.append(f"대상 응답 {root['status']} ({root['elapsed']}s)")

        pages = crawl(target, limiter, excludes=excludes)
        log.append(f"크롤: {len(pages)}개 URL 발견")
        param_urls = [u for u in pages if urlparse(u).query]
        log.append(f"파라미터 있는 URL: {len(param_urls)}개")

        suite = list(checks.PASSIVE)
        if active:
            suite += checks.ACTIVE
            log.append("능동 모드: 제외 경로·속도제한 적용하여 공격 요청 전송")
        else:
            log.append("수동(passive) 모드: 공격 요청 없이 관찰만")
        suite += checks.ALWAYS

        for fn in suite:
            try:
                findings += fn(target, root, pages=pages, limiter=limiter, excludes=excludes)
            except BlockedTarget as e:
                log.append(f"차단: {e}")
            except LimitExceeded as e:
                log.append(f"중단: {e}")
                break
            except Exception as e:  # 개별 체크 실패는 전체를 막지 않음
                log.append(f"{fn.__name__} 오류: {e}")
    except LimitExceeded as e:
        log.append(f"중단: {e}")
    except BlockedTarget as e:
        return {"ok": False, "error": str(e)}

    order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4}
    findings.sort(key=lambda f: (f["status"] != "vuln", order.get(f["severity"], 9)))
    summary = _summary(findings)
    return {"ok": True, "target": target, "mode": mode, "requests": limiter.count,
            "findings": findings, "summary": summary, "log": log}


def run_probe(url, method="GET", data=None, allow_blocked=False):
    """실습용 단일 요청. 안전장치(로컬 전용·차단경로)를 거쳐 응답을 그대로 돌려준다.
    대시보드 '실습 미션/콘솔'이 쓴다. allow_blocked 는 사용자 opt-in에서만 True."""
    if not url:
        return {"ok": False, "error": "URL이 비었습니다."}
    if not url.startswith(("http://", "https://")):
        url = "http://" + url
    if not host_allowed(url):
        return {"ok": False, "error": "로컬/사설 호스트만 허용됩니다(127.0.0.1·localhost 등)."}
    limiter = Limiter(min_interval=0.0, max_requests=1)
    try:
        r = guarded_request(url, method=method, data=data, limiter=limiter,
                            active=True, allow_blocked=allow_blocked)
    except BlockedTarget as e:
        return {"ok": False, "blocked": True, "error": str(e)}
    except LimitExceeded as e:
        return {"ok": False, "error": str(e)}
    except Exception as e:  # 잘못된 URL 등도 핸들러를 죽이지 않게
        return {"ok": False, "error": f"요청 처리 실패: {e}"}
    if r.get("error"):
        return {"ok": False, "error": r["error"]}
    body = r.get("body", "")
    return {"ok": True, "url": r["url"], "status": r["status"],
            "elapsed": r.get("elapsed"), "len": len(body), "body": body[:6000],
            "headers": {k: v for k, v in list(r.get("headers", {}).items())[:24]}}


def _summary(findings):
    s = {"vuln": 0, "safe": 0, "manual": 0,
         "critical": 0, "high": 0, "medium": 0, "low": 0}
    for f in findings:
        if f["status"] in s:
            s[f["status"]] += 1
        if f["status"] == "vuln" and f["severity"] in s:
            s[f["severity"]] += 1
    return s


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        data = body if isinstance(body, bytes) else body.encode()
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        path = urlparse(self.path).path
        if path in ("/", "/index.html"):
            f = STATIC / "index.html"
            return self._send(200, f.read_bytes(), "text/html; charset=utf-8")
        if path == "/api/defaults":
            return self._send(200, json.dumps({"excludes": DEFAULT_EXCLUDES}))
        return self._send(404, json.dumps({"error": "not found"}))

    def do_POST(self):
        path = urlparse(self.path).path
        if path not in ("/api/scan", "/api/probe"):
            return self._send(404, json.dumps({"error": "not found"}))
        try:
            n = int(self.headers.get("Content-Length", 0))
            req = json.loads(self.rfile.read(n) or b"{}")
        except Exception as e:
            return self._send(400, json.dumps({"ok": False, "error": f"잘못된 요청: {e}"}))
        if path == "/api/probe":
            result = run_probe(
                url=(req.get("url") or "").strip(),
                method=(req.get("method") or "GET").upper(),
                data=req.get("data"),
                allow_blocked=bool(req.get("allow_blocked")),
            )
            return self._send(200, json.dumps(result, ensure_ascii=False))
        result = run_scan(
            target=(req.get("target") or "").strip(),
            mode=req.get("mode", "passive"),
            extra_excludes=req.get("excludes") or [],
            rate=float(req.get("rate", 0.2)),
            max_requests=int(req.get("max_requests", 800)),
        )
        port = getattr(self.server, "llm_port", None)
        if port and result["ok"] and result["mode"] == "active":
            review_one_a05(result["findings"], port)
        self._send(200, json.dumps(result, ensure_ascii=False))

    def log_message(self, *a):  # 콘솔 소음 억제
        pass


def main():
    ap = argparse.ArgumentParser(description="웹 취약점 분석 도구(학습용, 로컬 전용)")
    ap.add_argument("--port", type=int, default=8900)
    ap.add_argument("--host", default="127.0.0.1")  # 대시보드도 로컬에만 바인딩
    ap.add_argument("--llm-port", type=int, help="로컬 LLM API 포트 (A05 한 건 분석)")
    args = ap.parse_args()
    if args.llm_port is not None and not 1 <= args.llm_port <= 65535:
        ap.error("--llm-port must be between 1 and 65535")
    srv = ThreadingHTTPServer((args.host, args.port), Handler)
    srv.llm_port = args.llm_port
    print(f"대시보드: http://{args.host}:{args.port}  (학습용·로컬 전용. Ctrl+C 종료)")
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        print("\n종료")


if __name__ == "__main__":
    main()
