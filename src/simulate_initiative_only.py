# test: the simulation skeleton (initiative-only)

import sqlite3
import random
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "db" / "dnd_initiative_work.sqlite"

ENCOUNTER_NAME = "L3 Trio vs 4 Goblins + 1 Bugbear"
NUM_RUNS = 20  # start small; later bump to 10_000

def d20(rng: random.Random) -> int:
    return rng.randint(1, 20)

def main():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA busy_timeout = 30000;")

    # Find encounter_template_id
    row = conn.execute(
        "SELECT encounter_template_id FROM encounter_template WHERE name = ?;",
        (ENCOUNTER_NAME,)
    ).fetchone()
    if not row:
        raise RuntimeError(f"Encounter template not found: {ENCOUNTER_NAME}")
    et_id = row[0]

    # Loads encounter members from encounter_template_member
    members = conn.execute("""
        SELECT side, slot_name, pc_id, monster_key
        FROM encounter_template_member
        WHERE encounter_template_id = ?
        ORDER BY side, slot_name;
    """, (et_id,)).fetchall()

    if not members:
        raise RuntimeError("No encounter_template_member rows found. Did you seed them?")

    print(f"Loaded {len(members)} members for encounter_template_id={et_id}")

    for run_n in range(1, NUM_RUNS + 1):
        seed = random.randint(1, 2**31 - 1)
        rng = random.Random(seed)

        # Insert a simulation_run row (winner info unknown yet, so placeholder)
        # We'll update later in full combat sim. For now, mark as timeout/placeholder.
        cur = conn.execute("""
            INSERT INTO simulation_run
              (encounter_template_id, seed, party_victory, winner, rounds_taken,
               total_damage_party, total_damage_monsters, notes_flags_json)
            VALUES (?, ?, 0, 'timeout', 0, 0, 0, ?);
        """, (et_id, seed, '{"phase":"initiative_only"}'))
        run_id = cur.lastrowid

        # Build participants: pull stats from either dim_pc_template or dim_monster
        participants = []
        for side, slot_name, pc_id, monster_key in members:
            if pc_id is not None:  # PC
                pc = conn.execute("""
                    SELECT pc_id, name, ac, max_hp, dex_mod
                    FROM dim_pc_template
                    WHERE pc_id = ?;
                """, (pc_id,)).fetchone()
                if not pc:
                    raise RuntimeError(f"PC template missing: {pc_id}")
                _, pc_name, ac, hp, dex_mod = pc
                participants.append({
                    "side": "party",
                    "name": slot_name,           # keep slot name stable ("Rogue")
                    "template_type": "pc",
                    "pc_id": pc_id,
                    "monster_key": None,
                    "ac": int(ac),
                    "hp_start": int(hp),
                    "init_mod": int(dex_mod),
                })
            else:  # Monster
                mon = conn.execute("""
                    SELECT monster_key, monster_name, armor_class, hit_points, dex_mod
                    FROM dim_monster
                    WHERE monster_key = ?;
                """, (monster_key,)).fetchone()
                if not mon:
                    raise RuntimeError(f"Monster missing: monster_key={monster_key}")
                _, mon_name, ac, hp, dex_mod = mon
                participants.append({
                    "side": "monsters",
                    "name": slot_name,           # keep slot name stable ("Goblin_1")
                    "template_type": "monster",
                    "pc_id": None,
                    "monster_key": int(monster_key),
                    "ac": int(ac),
                    "hp_start": int(hp),
                    "init_mod": int(dex_mod) if dex_mod is not None else 0,
                })

        # Roll initiative
        for p in participants:
            roll = d20(rng)
            p["init_roll_d20"] = roll
            p["init_total"] = roll + p["init_mod"]

        # Sort by initiative_total desc, then init_mod desc, then random tie-break
        rng.shuffle(participants)
        participants.sort(key=lambda x: (x["init_total"], x["init_mod"]), reverse=True)

        # Write participant_run rows
        for order, p in enumerate(participants, start=1):
            conn.execute("""
                INSERT INTO participant_run
                  (run_id, side, name, template_type, pc_id, monster_key,
                   hp_start, hp_end, alive_end,
                   init_roll_d20, init_mod, init_total, init_order,
                   damage_dealt_total, damage_taken_total, attacks_made, hits_landed, crits_landed,
                   opening_burst_triggered, hunters_mark_cast, hunters_mark_bonus_damage)
                VALUES (?, ?, ?, ?, ?, ?,
                        ?, ?, 1,
                        ?, ?, ?, ?,
                        0, 0, 0, 0, 0,
                        0, 0, 0);
            """, (
                run_id,
                p["side"],
                p["name"],
                p["template_type"],
                p["pc_id"],
                p["monster_key"],
                p["hp_start"],
                p["hp_start"],   # hp_end = hp_start for now
                p["init_roll_d20"],
                p["init_mod"],
                p["init_total"],
                order,
            ))

        conn.commit()
        print(f"Run {run_n}/{NUM_RUNS} inserted (run_id={run_id}, seed={seed})")

    conn.close()
    print("✅ Initiative-only simulations complete.")

if __name__ == "__main__":
    main()
