import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "db" / "dnd_initiative.sqlite"

def list_tables(conn: sqlite3.Connection):
    cur = conn.execute("""
        SELECT name
        FROM sqlite_master
        WHERE type='table' AND name NOT LIKE 'sqlite_%'
        ORDER BY name;
    """)
    return [r[0] for r in cur.fetchall()]

def list_columns(conn: sqlite3.Connection, table: str):
    cur = conn.execute(f"PRAGMA table_info({table});")
    # (cid, name, type, notnull, dflt_value, pk)
    return cur.fetchall()

def row_count(conn: sqlite3.Connection, table: str) -> int:
    try:
        cur = conn.execute(f"SELECT COUNT(*) FROM {table};")
        return int(cur.fetchone()[0])
    except Exception:
        return -1

def main():
    print("DB path:", DB_PATH)
    print("DB exists:", DB_PATH.exists())
    if DB_PATH.exists():
        print("DB size (KB):", DB_PATH.stat().st_size // 1024)

    # timeout + busy_timeout helps with temporary locks
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA busy_timeout = 30000;")  # 30s

    # Try enabling WAL (better concurrency). If it fails, no big deal.
    try:
        mode = conn.execute("PRAGMA journal_mode=WAL;").fetchone()[0]
        print("journal_mode:", mode)
    except Exception as e:
        print("journal_mode change failed:", e)

    tables = list_tables(conn)
    print("\nTables:", tables)

    for t in tables:
        cols = list_columns(conn, t)
        print(f"\n[{t}] columns:")
        for cid, name, ctype, notnull, dflt, pk in cols:
            print(f"  - {name} {ctype} {'NOT NULL' if notnull else ''} {'PK' if pk else ''}".strip())
        print(f"  rows: {row_count(conn, t)}")

    # Write test (creates a temp table). If this fails, you truly can't write.
    print("\nWrite test:")
    try:
        conn.execute("CREATE TABLE IF NOT EXISTS __write_test (id INTEGER PRIMARY KEY, note TEXT);")
        conn.execute("INSERT INTO __write_test(note) VALUES ('hello');")
        conn.commit()
        print("✅ Write test passed (DB is writable).")
    except Exception as e:
        print("❌ Write test failed (DB may be locked / read-only):", repr(e))
    finally:
        # Cleanup
        try:
            conn.execute("DROP TABLE IF EXISTS __write_test;")
            conn.commit()
        except Exception:
            pass
        conn.close()

if __name__ == "__main__":
    main()
