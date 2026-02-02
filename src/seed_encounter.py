import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "db" / "dnd_initiative_work.sqlite"


def main():

    # timeout + busy_timeout helps with temporary locks
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA busy_timeout = 30000;")  # 30s

    conn.execute("""
        INSERT INTO encounter_template (name, description, target_selection_pc, target_selection_mon, round_cap)
        VALUES
            ('L3 Trio vs 4 Goblins + 1 Bugbear',
            'Fighter(Champion), Rogue(Assassin), Ranger(Gloom Stalker) vs 4 Goblins and 1 Bugbear. PCs focus bugbear first.',
            'bugbear_first',
            'lowest_hp',
            20);
    """)
    conn.commit()
    conn.close()

if __name__ == "__main__":
    main()

