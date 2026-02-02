import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCHEMA_PATH = PROJECT_ROOT / "sql" / "schema.sql"

# New DB file (separate from the one PyCharm is browsing heavily)
NEW_DB_PATH = PROJECT_ROOT / "db" / "dnd_initiative_work.sqlite"

def main():
    NEW_DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    print("Schema:", SCHEMA_PATH)
    print("New DB:", NEW_DB_PATH)

    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")

    conn = sqlite3.connect(NEW_DB_PATH, timeout=30)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA busy_timeout = 30000;")

    # WAL helps reduce lock pain when you inspect in PyCharm
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
    except Exception:
        pass

    conn.executescript(schema_sql)
    conn.commit()
    conn.close()

    print("✅ New database created and schema applied.")

if __name__ == "__main__":
    main()
