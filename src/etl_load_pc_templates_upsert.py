import sqlite3
import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "db" / "dnd_initiative_work.sqlite"   # <-- use the NEW DB
CSV_PATH = PROJECT_ROOT / "data" / "raw" / "pc_templates.csv"

def main():
    df = pd.read_csv(CSV_PATH).rename(columns={"class": "class_name"})

    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA busy_timeout = 30000;")

    cols = list(df.columns)
    colnames = ",".join(cols)
    placeholders = ",".join(["?"] * len(cols))

    sql = f"""
    INSERT OR REPLACE INTO dim_pc_template ({colnames})
    VALUES ({placeholders});
    """

    conn.executemany(sql, df.itertuples(index=False, name=None))
    conn.commit()
    conn.close()

    print("✅ PC templates upserted into:", DB_PATH)

if __name__ == "__main__":
    main()
