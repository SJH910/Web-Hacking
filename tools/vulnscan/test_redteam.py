"""레드팀(파훼자) 챌린지 엔진 테스트. 네트워크·실행 없음: 순수 함수 검증."""
import unittest

import redteam


def h(method, parts, body=None):
    return redteam.handle(method, parts, body or {})


ALL = ("c1", "c2", "c3", "c4", "c5", "c6", "c7", "c8",
       "c9", "c10", "c11", "c12", "c13", "c14")
FLOORS = min(10, len(ALL))


class Catalog(unittest.TestCase):
    def test_catalog(self):
        st, obj = h("GET", ["catalog"])
        self.assertEqual(st, 200)
        ids = [c["id"] for c in obj["challenges"]]
        self.assertEqual(ids, list(ALL))

    def test_start_no_flag_leak(self):
        for cid in ALL:
            st, obj = h("GET", [cid, "start"])
            self.assertEqual(st, 200)
            self.assertNotIn("flag", obj)
            self.assertEqual(obj["cleared"], False)

    def test_unknown(self):
        self.assertEqual(h("GET", ["zzz", "start"])[0], 404)
        self.assertEqual(h("POST", ["c1", "bogus"], {})[0], 404)


class C1Idor(unittest.TestCase):
    def test_inbox_clue(self):
        _, o = h("POST", ["c1", "visit"], {"path": "/inbox"})
        self.assertIn("note ids are sequential", o["sourceComments"])
        self.assertFalse(o["exploited"])

    def test_own_note(self):
        _, o = h("POST", ["c1", "visit"], {"path": "/note?id=18"})
        self.assertEqual(o["owner"], "visitor")
        self.assertFalse(o["exploited"])
        self.assertFalse(o["flagRevealed"])

    def test_idor_flag(self):
        _, o = h("POST", ["c1", "visit"], {"path": "/note?id=19"})
        self.assertEqual(o["owner"], "admin")
        self.assertTrue(o["exploited"])
        self.assertTrue(o["flagRevealed"])
        self.assertIn("FLAG{idor_sequential_notes}", o["html"])

    def test_other_staff_idor_no_flag(self):
        _, o = h("POST", ["c1", "visit"], {"path": "/note?id=20"})
        self.assertTrue(o["exploited"])
        self.assertFalse(o["flagRevealed"])

    def test_missing_404(self):
        _, o = h("POST", ["c1", "visit"], {"path": "/note?id=999"})
        self.assertEqual(o["status"], 404)

    def test_submit(self):
        _, o = h("POST", ["c1", "submit"], {"flag": "FLAG{idor_sequential_notes}"})
        self.assertTrue(o["cleared"])
        self.assertIn("IDOR", o["wrapUp"])


class C2Xss(unittest.TestCase):
    def test_board_form_and_clue(self):
        _, o = h("POST", ["c2", "visit"], {"path": "/board"})
        self.assertIn("data-rt", o["html"])             # 폼 포함
        self.assertTrue(any("이스케이프" in c for c in o["sourceComments"]))
        self.assertFalse(o["exploited"])

    def test_benign_reflect_not_exploit(self):
        _, o = h("POST", ["c2", "visit"], {"path": "/board", "data": {"q": "안녕"}})
        self.assertIn("안녕", o["html"])
        self.assertFalse(o["exploited"])
        self.assertFalse(o["flagRevealed"])

    def test_xss_payload_flag(self):
        for payload in ["<svg onload=alert(1)>", "<script>x</script>", "<img src=x onerror=y>"]:
            _, o = h("POST", ["c2", "visit"], {"path": "/board", "data": {"q": payload}})
            self.assertTrue(o["exploited"], payload)
            self.assertTrue(o["flagRevealed"], payload)
            self.assertIn("FLAG{reflected_xss_admin_cookie}", o["html"])

    def test_submit(self):
        _, o = h("POST", ["c2", "submit"], {"flag": "FLAG{reflected_xss_admin_cookie}"})
        self.assertTrue(o["cleared"])


class C3Sqli(unittest.TestCase):
    def test_login_form(self):
        _, o = h("POST", ["c3", "visit"], {"path": "/login"})
        self.assertIn("data-rt", o["html"])
        self.assertFalse(o["exploited"])

    def test_wrong_login(self):
        _, o = h("POST", ["c3", "visit"], {"path": "/login", "data": {"user": "bob", "pw": "x"}})
        self.assertFalse(o["exploited"])
        self.assertIn("실패", o["html"])

    def test_quote_shows_sql_error_clue(self):
        _, o = h("POST", ["c3", "visit"], {"path": "/login", "data": {"user": "'", "pw": ""}})
        self.assertFalse(o["exploited"])
        self.assertIn("SQL 오류", o["html"])

    def test_sqli_bypass_flag(self):
        for inj in ["' OR '1'='1", "' or 1=1 --", "admin'--"]:
            _, o = h("POST", ["c3", "visit"], {"path": "/login", "data": {"user": inj, "pw": "x"}})
            self.assertTrue(o["exploited"], inj)
            self.assertTrue(o["flagRevealed"], inj)
            self.assertIn("FLAG{auth_bypass_sqli}", o["html"])

    def test_submit(self):
        _, o = h("POST", ["c3", "submit"], {"flag": "FLAG{auth_bypass_sqli}"})
        self.assertTrue(o["cleared"])


class Climb(unittest.TestCase):
    def test_climb_issues_seed(self):
        st, o = h("GET", ["climb"])
        self.assertEqual(st, 200)
        self.assertTrue(o["seed"])
        self.assertEqual(o["floors"], FLOORS)          # 풀 14 중 랜덤 10층

    def test_floor_deterministic_no_dup(self):
        _, c = h("GET", ["climb"])
        seed = c["seed"]
        cids = []
        for n in range(1, FLOORS + 1):
            st, f = h("GET", ["floor", seed, str(n)])
            self.assertEqual(st, 200)
            self.assertEqual(f["floor"], n)
            self.assertEqual(f["floors"], FLOORS)
            cids.append(f["challengeId"])
        self.assertEqual(len(set(cids)), FLOORS)       # 중복 없음
        _, again = h("GET", ["floor", seed, "1"])
        self.assertEqual(again["challengeId"], cids[0])

    def test_floor_out_of_range(self):
        _, c = h("GET", ["climb"])
        self.assertEqual(h("GET", ["floor", c["seed"], str(FLOORS + 1)])[0], 404)

    def test_different_seeds_vary(self):  # 풀>10이므로 시드마다 구성이 다를 수 있음
        import redteam
        self.assertEqual(redteam._floors(), 10)
        self.assertEqual(len(redteam._order("aaa")), 10)


class NewChallenges(unittest.TestCase):
    def ex(self, cid, path, data=None):  # 익스플로잇 성공이면 (exploited, flagRevealed)
        _, o = h("POST", [cid, "visit"], {"path": path, "data": data or {}})
        return o

    def test_c4_ssrf(self):
        self.assertFalse(self.ex("c4", "/preview", {"url": "http://example.test"})["exploited"])
        o = self.ex("c4", "/preview", {"url": "http://127.0.0.1/admin"})
        self.assertTrue(o["exploited"]); self.assertTrue(o["flagRevealed"])
        self.assertIn("FLAG{ssrf_internal_access}", o["html"])

    def test_c5_forced_browsing(self):
        self.assertIn("admin-backup", self.ex("c5", "/robots.txt")["sourceComments"][0])
        o = self.ex("c5", "/admin-backup/")
        self.assertTrue(o["exploited"]); self.assertIn("FLAG{forced_browsing}", o["html"])

    def test_c6_price_tampering(self):
        self.assertFalse(self.ex("c6", "/checkout", {"price": "10000"})["exploited"])
        o = self.ex("c6", "/checkout", {"price": "0"})
        self.assertTrue(o["exploited"]); self.assertIn("FLAG{price_tampering}", o["html"])

    def test_c7_verbose_error(self):
        self.assertFalse(self.ex("c7", "/vault", {"id": "1"})["exploited"])
        o = self.ex("c7", "/vault", {"id": "abc"})
        self.assertTrue(o["exploited"]); self.assertIn("FLAG{verbose_error_leak}", o["html"])

    def test_c8_path_traversal(self):
        self.assertFalse(self.ex("c8", "/download", {"name": "guide.txt"})["exploited"])
        o = self.ex("c8", "/download", {"name": "../../secret"})
        self.assertTrue(o["exploited"]); self.assertIn("FLAG{path_traversal}", o["html"])

    def test_new_submit(self):
        for cid, fl in [("c4", "FLAG{ssrf_internal_access}"), ("c5", "FLAG{forced_browsing}"),
                        ("c6", "FLAG{price_tampering}"), ("c7", "FLAG{verbose_error_leak}"),
                        ("c8", "FLAG{path_traversal}")]:
            _, o = h("POST", [cid, "submit"], {"flag": fl})
            self.assertTrue(o["cleared"], cid)


class MoreChallenges(unittest.TestCase):
    def ex(self, cid, path, data=None):
        _, o = h("POST", [cid, "visit"], {"path": path, "data": data or {}})
        return o

    def test_c9_stored_xss(self):
        self.assertFalse(self.ex("c9", "/guestbook", {"msg": "안녕"})["exploited"])
        o = self.ex("c9", "/guestbook", {"msg": "<script>x</script>"})
        self.assertTrue(o["exploited"]); self.assertIn("FLAG{stored_xss_admin}", o["html"])

    def test_c10_role(self):
        self.assertFalse(self.ex("c10", "/panel", {"role": "user"})["exploited"])
        o = self.ex("c10", "/panel", {"role": "admin"})
        self.assertTrue(o["exploited"]); self.assertIn("FLAG{role_tampering}", o["html"])

    def test_c11_blind_sqli(self):
        self.assertFalse(self.ex("c11", "/stock", {"id": "1"})["exploited"])
        o = self.ex("c11", "/stock", {"id": "1 AND sleep(3)"})
        self.assertTrue(o["exploited"]); self.assertIn("FLAG{time_based_sqli}", o["html"])

    def test_c12_session(self):
        self.assertFalse(self.ex("c12", "/order", {"sid": "1007"})["exploited"])
        o = self.ex("c12", "/order", {"sid": "1000"})
        self.assertTrue(o["exploited"]); self.assertIn("FLAG{predictable_session}", o["html"])

    def test_c13_plaintext(self):
        self.assertFalse(self.ex("c13", "/receipt")["exploited"])
        o = self.ex("c13", "/receipt/view")
        self.assertTrue(o["exploited"]); self.assertIn("FLAG{sensitive_plaintext}", o["html"])

    def test_c14_cmdi(self):
        self.assertFalse(self.ex("c14", "/ping", {"host": "example.test"})["exploited"])
        o = self.ex("c14", "/ping", {"host": "example.test; whoami"})
        self.assertTrue(o["exploited"]); self.assertIn("FLAG{command_injection}", o["html"])


class Hints(unittest.TestCase):
    def test_hint_bounds(self):
        self.assertEqual(h("POST", ["c1", "hint"], {"level": 1})[0], 200)
        self.assertEqual(h("POST", ["c1", "hint"], {"level": 9})[0], 400)


if __name__ == "__main__":
    unittest.main()
