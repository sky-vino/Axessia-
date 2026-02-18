import sqlite3

conn = sqlite3.connect("ai_cache.db", check_same_thread=False)
conn.execute("""
CREATE TABLE IF NOT EXISTS cache (
  rule_id TEXT PRIMARY KEY,
  explanation TEXT
)
""")

def get_cached(rule_id):
    row = conn.execute(
        "SELECT explanation FROM cache WHERE rule_id=?",
        (rule_id,)
    ).fetchone()
    return row[0] if row else None

def set_cached(rule_id, text):
    conn.execute(
        "INSERT OR REPLACE INTO cache VALUES (?, ?)",
        (rule_id, text)
    )
    conn.commit()
