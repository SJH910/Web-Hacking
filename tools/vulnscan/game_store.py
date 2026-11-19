"""등반·랭킹 영속 저장(B5·B6). 표준 라이브러리 sqlite3만 쓴다. 호출자(엔진)가 락을 잡는다.

shortcut: 등반 전체를 JSON 한 덩어리로 저장한다. 동시 접속이 많아지거나 질의가 필요해지면 컬럼으로 분리한다.
"""
import json
import sqlite3
import time
from pathlib import Path

MAX_RUNS = 1000


class Store:
    def __init__(self, path=":memory:"):
        if path != ":memory:":
            Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.db = sqlite3.connect(str(path), check_same_thread=False)
        self.db.executescript("""
            CREATE TABLE IF NOT EXISTS runs(id TEXT PRIMARY KEY, data TEXT NOT NULL, updated REAL NOT NULL);
            CREATE TABLE IF NOT EXISTS creates(request_id TEXT PRIMARY KEY, run_id TEXT NOT NULL);
            CREATE TABLE IF NOT EXISTS ranks(run_id TEXT PRIMARY KEY, name TEXT NOT NULL, floor INTEGER NOT NULL,
                score INTEGER NOT NULL, trust INTEGER NOT NULL, hints INTEGER NOT NULL);
        """)

    def get_run(self, run_id):
        row = self.db.execute("SELECT data FROM runs WHERE id=?", (run_id,)).fetchone()
        return json.loads(row[0]) if row else None

    def put_run(self, r):
        self.db.execute("INSERT INTO runs VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data, updated=excluded.updated",
                        (r["id"], json.dumps(r, ensure_ascii=False), time.time()))
        # 오래된 등반 정리(랭킹에 오른 기록은 ranks에 남는다)
        self.db.execute("DELETE FROM runs WHERE id IN (SELECT id FROM runs ORDER BY updated DESC LIMIT -1 OFFSET ?)", (MAX_RUNS,))
        self.db.execute("DELETE FROM creates WHERE run_id NOT IN (SELECT id FROM runs)")
        self.db.commit()

    def get_create(self, request_id):
        row = self.db.execute("SELECT run_id FROM creates WHERE request_id=?", (request_id,)).fetchone()
        return row[0] if row else None

    def put_create(self, request_id, run_id):
        self.db.execute("INSERT OR IGNORE INTO creates VALUES(?,?)", (request_id, run_id))
        self.db.commit()

    def add_rank(self, run_id, name, floor, score, trust, hints):
        self.db.execute("INSERT OR IGNORE INTO ranks VALUES(?,?,?,?,?,?)", (run_id, name, floor, score, trust, hints))
        self.db.commit()

    def top_ranks(self, limit=100):
        rows = self.db.execute("SELECT name,floor,score,trust,hints FROM ranks ORDER BY score DESC, trust DESC, hints ASC, rowid ASC LIMIT ?",
                               (limit,)).fetchall()
        return [{"rank": i + 1, "name": n, "floor": f, "score": s, "trust": t, "hints": h} for i, (n, f, s, t, h) in enumerate(rows)]
