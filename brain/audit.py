"""Tamper-evident audit log (Aaron, Module B).
Each row stores hash = sha256(previous hash + this row's JSON). Editing any old row breaks every later hash.
"""
import hashlib, json, sqlite3, threading

class AuditLog:
    def __init__(self, path="chakravyuh.db"):
        self.db = sqlite3.connect(path, check_same_thread=False)
        self.lock = threading.Lock()
        self.db.execute("CREATE TABLE IF NOT EXISTS audit (id INTEGER PRIMARY KEY, body TEXT, hash TEXT)")
        self.db.commit()

    def _last_hash(self):
        row = self.db.execute("SELECT hash FROM audit ORDER BY id DESC LIMIT 1").fetchone()
        return row[0] if row else "0" * 64

    def append(self, record: dict):
        with self.lock:
            body = json.dumps(record, sort_keys=True)
            h = hashlib.sha256((self._last_hash() + body).encode()).hexdigest()
            self.db.execute("INSERT INTO audit (body, hash) VALUES (?, ?)", (body, h))
            self.db.commit()
            return h

    def verify(self):
        prev = "0" * 64
        for rid, body, h in self.db.execute("SELECT id, body, hash FROM audit ORDER BY id"):
            if hashlib.sha256((prev + body).encode()).hexdigest() != h:
                return {"ok": False, "broken_at": rid}
            prev = h
        return {"ok": True}

    def rows(self, limit=50):
        return [{"id": r, "body": json.loads(b), "hash": h[:12]} for r, b, h in
                self.db.execute("SELECT id, body, hash FROM audit ORDER BY id DESC LIMIT ?", (limit,))]
