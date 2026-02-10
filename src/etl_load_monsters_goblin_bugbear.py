import sqlite3
import pandas as pd
import ast
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "db" / "dnd_initiative_work.sqlite"
CSV_PATH = PROJECT_ROOT / "data" / "raw" / "monsters.csv"

TARGETS = {"goblin", "bugbear"}

def calc_mod(score: int) -> int:
    return (int(score) - 10) // 2

def parse_primary_attack(actions_str: str):
    """
    Extract first weapon attack's hit dice expression from "actions".
    Returns (attack_bonus, damage_dice, actions_raw)
    """
    if not isinstance(actions_str, str) or not actions_str.strip():
        return None, None, None

    try:
        actions = ast.literal_eval(actions_str)  # actions stored as text like "[{'name':..., 'desc':...}, ...]"
        if not isinstance(actions, list):
            return None, None, actions_str

        for action in actions:
            desc = str(action.get("desc", ""))
            if "Weapon Attack" in desc and "to hit" in desc:
                m_to_hit = re.search(r"\+(\d+)\s+to hit", desc)
                m_dice = re.search(r"\(([^)]+)\)", desc)
                atk = int(m_to_hit.group(1)) if m_to_hit else None
                dice = m_dice.group(1).replace(" ", "") if m_dice else None
                return atk, dice, actions_str

        return None, None, actions_str
    except Exception:
        # If parsing fails, keep raw actions text
        return None, None, actions_str

def main():
    df = pd.read_csv(CSV_PATH)

    # Filter to Goblin + Bugbear (exact names)
    df["name_lower"] = df["name"].astype(str).str.lower()
    df = df[df["name_lower"].isin(TARGETS)].copy()

    if df.empty:
        raise RuntimeError("Could not find Goblin/Bugbear in monsters.csv (check name column).")

    # Build curated rows
    curated = []
    for _, r in df.iterrows():

        # use the 1st "hits" found in the 1st weapon attack description.
        atk_bonus, dmg_dice, actions_raw = parse_primary_attack(r.get("actions"))

        curated.append({
            "monster_name": r["name"],
            "challenge_rating": float(r.get("challenge_rating")) if pd.notna(r.get("challenge_rating")) else None,
            "armor_class": int(r.get("armor_class")) if pd.notna(r.get("armor_class")) else None,
            "hit_points": int(r.get("hit_points")) if pd.notna(r.get("hit_points")) else None,
            "dex_mod": calc_mod(r.get("dexterity")) if pd.notna(r.get("dexterity")) else None,
            "attack_bonus": atk_bonus,
            "damage_dice": dmg_dice,
            "actions_json": actions_raw
        })

    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA busy_timeout = 30000;")
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
    except Exception:
        pass

    upsert_sql = """
    INSERT INTO dim_monster
      (monster_name, challenge_rating, armor_class, hit_points, dex_mod, attack_bonus, damage_dice, actions_json)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ON CONFLICT(monster_name) DO UPDATE SET
      challenge_rating = excluded.challenge_rating,
      armor_class      = excluded.armor_class,
      hit_points       = excluded.hit_points,
      dex_mod          = excluded.dex_mod,
      attack_bonus     = excluded.attack_bonus,
      damage_dice      = excluded.damage_dice,
      actions_json     = excluded.actions_json;
    """

    for row in curated:
        conn.execute(upsert_sql, (
            row["monster_name"],
            row["challenge_rating"],
            row["armor_class"],
            row["hit_points"],
            row["dex_mod"],
            row["attack_bonus"],
            row["damage_dice"],
            row["actions_json"],
        ))

    conn.commit()

    # Show what keys we got (useful for encounter_template_member)
    out = conn.execute(
        "SELECT monster_key, monster_name, armor_class, hit_points, dex_mod, attack_bonus, damage_dice "
        "FROM dim_monster WHERE lower(monster_name) IN ('goblin','bugbear') ORDER BY monster_name;"
    ).fetchall()

    conn.close()

    print("✅ Loaded/updated monsters into dim_monster:")
    for row in out:
        print(row)

if __name__ == "__main__":
    main()
