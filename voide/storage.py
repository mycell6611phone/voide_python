# File: workspace/voide/storage.py
self._ensure_table()


def _ensure_table(self) -> None:
cur = self._conn.cursor()
cur.execute(
'''
CREATE TABLE IF NOT EXISTS items (
key TEXT PRIMARY KEY,
value TEXT,
created_at REAL
)
'''
)
self._conn.commit()


def upsert(self, key: str, value: Dict[str, Any]) -> None:
t = time.time()
cur = self._conn.cursor()
cur.execute(
'''
INSERT INTO items(key, value, created_at) VALUES (?, ?, ?)
ON CONFLICT(key) DO UPDATE SET value=excluded.value, created_at=excluded.created_at
''', (key, json.dumps(value), t)
)
self._conn.commit()


def get(self, key: str, ttl: float | None = None) -> Dict[str, Any] | None:
cur = self._conn.cursor()
row = cur.execute(
'SELECT value, created_at FROM items WHERE key=?', (key,)
).fetchone()
if not row:
return None
val, ts = row
if ttl is not None and time.time() - ts > ttl:
return None
return json.loads(val)


def query(self, pattern: str, k: int = 8) -> List[Dict[str, Any]]:
cur = self._conn.cursor()
rows = cur.execute(
'''SELECT value FROM items WHERE value LIKE ? ORDER BY created_at DESC LIMIT ?''',
(f"%{pattern}%", k)
).fetchall()
return [json.loads(r[0]) for r in rows]


class JSONLog:
"""Append JSON lines to a file with ISO timestamps."""
def __init__(self, path: str) -> None:
self.path = path
Path(path).parent.mkdir(parents=True, exist_ok=True)


def append(self, record: Dict[str, Any]) -> None:
line = json.dumps({**record, "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())})
with open(self.path, "a", encoding="utf-8") as f:
f.write(line + "
")
