'''

import sqlite3
import pandas as pd

DB_PATH = "db/dnd_initiative.sqlite"
CSV_PATH = "data/raw/pc_templates.csv"

conn = sqlite3.connect(DB_PATH)
df = pd.read_csv(CSV_PATH)

df.to_sql(
    "dim_pc_template",
    conn,
    if_exists="append",
    index=False
)

conn.commit()
conn.close()

print("PC templates loaded successfully.")

'''

# Rewritten after DB somehow “write-blocked”

import sqlite3
import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "db" / "dnd_initiative.sqlite"
CSV_PATH = PROJECT_ROOT / "data" / "raw" / "pc_templates.csv"

df = pd.read_csv(CSV_PATH).rename(columns={"class": "class_name"})

conn = sqlite3.connect(DB_PATH)
cur = conn.cursor()

cols = list(df.columns)
placeholders = ",".join(["?"] * len(cols))
colnames = ",".join(cols)

sql = f"""
INSERT OR REPLACE INTO dim_pc_template ({colnames})
VALUES ({placeholders})
"""

cur.executemany(sql, df.itertuples(index=False, name=None))
conn.commit()
conn.close()

print("PC templates upserted successfully (insert or replace).")
