import sqlite3
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "db" / "dnd_initiative_work.sqlite"

ENCOUNTER_NAME = "L3 Trio vs 4 Goblins + 1 Bugbear"

PCS = [
    ("Fighter", "PC_FTR_CHAMPION_L3"),
    ("Rogue",   "PC_ROG_ASSASSIN_L3"),
    ("Ranger",  "PC_RGR_GLOOMSTALKER_L3"),
]

def main():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA busy_timeout = 30000;")
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
    except Exception:
        pass

    # Finds the encounter template by name "L3 Trio vs 4 Goblins + 1 Bugbear"
    row = conn.execute(
        """SELECT encounter_template_id FROM encounter_template 
           WHERE name = ?;""",
        (ENCOUNTER_NAME,)
    ).fetchone()
    if not row:
        raise RuntimeError(f"Encounter template not found: {ENCOUNTER_NAME}")
    et_id = row[0]

    # Get monster keys
    goblin_key = conn.execute(
        """SELECT monster_key FROM dim_monster 
        WHERE lower(monster_name)='goblin';"""
    ).fetchone()
    bugbear_key = conn.execute(
        """SELECT monster_key FROM dim_monster 
           WHERE lower(monster_name)='bugbear';"""
    ).fetchone()

    if not goblin_key or not bugbear_key:
        raise RuntimeError("Goblin or Bugbear missing in dim_monster. Run etl_load_monsters_goblin_bugbear.py first.")

    goblin_key = goblin_key[0]
    bugbear_key = bugbear_key[0]

    # Insert PCs
    for slot_name, pc_id in PCS:
        conn.execute("""
            INSERT OR IGNORE INTO encounter_template_member
              (encounter_template_id, side, slot_name, pc_id, monster_key, quantity)
            VALUES (?, 'party', ?, ?, NULL, 1);
        """, (et_id, slot_name, pc_id))

    # Insert 4 goblins as separate slots
    for i in range(1, 5):
        conn.execute("""
            INSERT OR IGNORE INTO encounter_template_member
              (encounter_template_id, side, slot_name, pc_id, monster_key, quantity)
            VALUES (?, 'monsters', ?, NULL, ?, 1);
        """, (et_id, f"Goblin_{i}", goblin_key))

    # Insert bugbear
    conn.execute("""
        INSERT OR IGNORE INTO encounter_template_member
          (encounter_template_id, side, slot_name, pc_id, monster_key, quantity)
        VALUES (?, 'monsters', 'Bugbear', NULL, ?, 1);
    """, (et_id, bugbear_key))

    conn.commit()

    # Quick view
    rows = conn.execute("""
        SELECT side, slot_name, pc_id, monster_key
        FROM encounter_template_member
        WHERE encounter_template_id = ?
        ORDER BY side, slot_name;
    """, (et_id,)).fetchall()

    conn.close()

    print("✅ encounter_template_member seeded:")
    for r in rows:
        print(r)

if __name__ == "__main__":
    main()
