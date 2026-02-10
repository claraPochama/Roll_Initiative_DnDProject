import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "db" / "dnd_initiative_work.sqlite"

def list_tables(conn: sqlite3.Connection):
    cur = conn.execute("""
        SELECT * FROM dim_monster;


    """)
    return cur.fetchall()


def main():

    # timeout + busy_timeout helps with temporary locks
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA busy_timeout = 30000;")  # 30s

    tables = list_tables(conn)

    for t in tables:
        print(t, " ")
        conn.close()

if __name__ == "__main__":
    main()

