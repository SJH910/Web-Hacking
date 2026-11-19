"""게임 정적 제공 경로 회귀 검사. 스캔이나 외부 요청은 실행하지 않는다."""
import http.client
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from http.server import ThreadingHTTPServer

import scanner


class GameRoutesTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.root = Path(cls.temp.name) / 'out'
        cls.root.mkdir()
        (cls.root / 'index.html').write_text('<h1>용범의 탑</h1>', encoding='utf-8')
        (cls.root / 'intro').mkdir()
        (cls.root / 'intro/index.html').write_text('인트로', encoding='utf-8')
        (cls.root / 'style.css').write_text('body { color: black; }')
        (Path(cls.temp.name) / 'private.txt').write_text('private')
        (cls.root / 'outside.txt').symlink_to(Path(cls.temp.name) / 'private.txt')
        cls.patch = patch.object(scanner, 'GAME_DIR', cls.root)
        cls.patch.start()
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), scanner.Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        cls.patch.stop()
        cls.temp.cleanup()

    def get(self, path):
        conn = http.client.HTTPConnection('127.0.0.1', self.server.server_port)
        try:
            conn.request('GET', path)
            response = conn.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            conn.close()

    def test_dashboard_still_served(self):
        status, _, body = self.get('/')
        self.assertEqual(status, 200)
        self.assertIn(b'tab-game', body)

    def test_game_redirect(self):
        status, headers, _ = self.get('/game')
        self.assertEqual(status, 308)
        self.assertEqual(headers['Location'], '/game/')

    def test_game_and_intro(self):
        for path in ['/game/', '/game/intro/', '/game/intro/?test=1']:
            with self.subTest(path=path):
                status, headers, _ = self.get(path)
                self.assertEqual(status, 200)
                self.assertIn('text/html', headers['Content-Type'])

    def test_css_type(self):
        status, headers, _ = self.get('/game/style.css')
        self.assertEqual(status, 200)
        self.assertIn('text/css', headers['Content-Type'])

    def test_traversal_and_symlink_rejected(self):
        for path in ['/game/../private.txt', '/game/%2e%2e/private.txt', '/game/%2Fetc/passwd', '/game/%00', '/game/outside.txt']:
            with self.subTest(path=path):
                self.assertEqual(self.get(path)[0], 404)

    def test_missing_asset(self):
        self.assertEqual(self.get('/game/missing.js')[0], 404)

    def test_missing_build(self):
        with patch.object(scanner, 'GAME_DIR', self.root / 'not-built'):
            self.assertEqual(self.get('/game/')[0], 503)


if __name__ == '__main__':
    unittest.main()
