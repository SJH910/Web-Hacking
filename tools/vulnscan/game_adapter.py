"""vulnscan 소견 JSON → 게임 증거·명령 출력으로 굽는 어댑터(B7, 선택). 저작 도구이며 서버 런타임에서는 쓰지 않는다.

입력은 이미 저장된 소견 {owasp,title,severity,status,evidence,note} 목록이다. 이 모듈은 어떤 요청도 보내지 않는다.
결과를 문제 dict의 evidence·commands에 붙여 넣으면 game_model.parse_problem이 같은 규칙으로 검증한다.
사용: python game_adapter.py <scan.json> [최대 개수]   (scan.json = /api/scan 응답 또는 findings 배열)
"""
import json
import re
import sys
from pathlib import Path

VERDICT = {"vuln": "취약", "safe": "양호", "manual": "증거 부족"}
_CTRL = re.compile(r"[\x00-\x08\x0b-\x1f\x7f]")


def _clean(value, limit):
    return _CTRL.sub("", str(value or "")).strip()[:limit]


def bake(findings, max_items=3):
    """소견 → (evidence, commands, verdict). status가 vuln·safe·manual인 것만 앞에서 max_items개 사용."""
    usable = [f for f in findings if isinstance(f, dict) and f.get("status") in VERDICT][:max_items]
    evidence, commands = [], []
    for i, f in enumerate(usable, 1):
        number, owasp, title = f"E{i}", _clean(f.get("owasp"), 8) or "-", _clean(f.get("title"), 80) or "소견"
        detail = _clean(f.get("evidence"), 200) or title
        note = _clean(f.get("note"), 200)
        evidence.append({"number": number, "title": title, "detail": detail, "tag": owasp})
        out = f"[{owasp}] {title}\n{detail}" + (f"\n{note}" if note else "")
        commands.append({"key": f"inspect{i}", "pattern": f"^inspect {number.lower()}$", "output": out, "reveals": [number]})
    statuses = {f["status"] for f in usable}
    verdict = "취약" if "vuln" in statuses else "증거 부족" if "manual" in statuses or not statuses else "양호"
    return evidence, commands, verdict


def main(argv):
    if not 2 <= len(argv) <= 3:
        print(__doc__)
        return 2
    data = json.loads(Path(argv[1]).read_text(encoding="utf-8"))
    findings = data.get("findings", []) if isinstance(data, dict) else data
    evidence, commands, verdict = bake(findings, int(argv[2]) if len(argv) == 3 else 3)
    print(json.dumps({"evidence": evidence, "commands": commands, "verdict": verdict}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
