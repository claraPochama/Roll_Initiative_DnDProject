import sqlite3
import random
import re
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DB_PATH = PROJECT_ROOT / "db" / "dnd_initiative_work.sqlite"

ENCOUNTER_NAME = "L3 Trio vs 4 Goblins + 1 Bugbear"
NUM_RUNS = 5000  # start with 200, then scale to 10000

ROUND_CAP_DEFAULT = 20

# -------------------------
# Dice helpers
# -------------------------

def roll(rng: random.Random, sides: int) -> int:
    return rng.randint(1, sides)

def roll_dice_expr(rng: random.Random, expr: str) -> int:
    """
    Parse dice like '2d6+3' or '1d8+3' or '2d8+2'
    """
    expr = expr.replace(" ", "")
    m = re.fullmatch(r"(\d+)d(\d+)([+-]\d+)?", expr)
    if not m:
        raise ValueError(f"Bad dice expr: {expr}")
    n = int(m.group(1))
    d = int(m.group(2))
    mod = int(m.group(3)) if m.group(3) else 0
    total = sum(roll(rng, d) for _ in range(n)) + mod
    return total

def roll_damage(rng: random.Random, base_expr: str, is_crit: bool) -> int:
    """
    If crit: double the dice count, keep flat modifier the same.
    Example: 1d8+3 crit -> 2d8+3
    """
    expr = base_expr.replace(" ", "")
    m = re.fullmatch(r"(\d+)d(\d+)([+-]\d+)?", expr)
    if not m:
        raise ValueError(f"Bad damage expr: {expr}")
    n = int(m.group(1))
    d = int(m.group(2))
    mod = int(m.group(3)) if m.group(3) else 0
    if is_crit:
        n *= 2
    return sum(roll(rng, d) for _ in range(n)) + mod

# -------------------------
# Rules: crit ranges / features
# -------------------------

def is_crit(threshold_str: str, d20_roll: int) -> bool:
    """
    threshold_str is '20' or '19-20' (from pc template)
    """
    if threshold_str == "20":
        return d20_roll == 20
    if threshold_str == "19-20":
        return d20_roll >= 19
    # fallback: natural 20
    return d20_roll == 20

def acts_before_target(participants, actor_name: str, target_name: str) -> bool:
    """
    Determine if actor's init_order is before target's init_order.
    """
    a = participants[actor_name]["init_order"]
    t = participants[target_name]["init_order"]
    return a < t

# -------------------------
# Target selection
# -------------------------

def pick_target_pc(monsters_alive: list[str]) -> str:
    """
    PCs focus Bugbear first, then Goblins.
    """
    if "Bugbear" in monsters_alive:
        return "Bugbear"
    # otherwise pick lowest-numbered goblin
    goblins = sorted([m for m in monsters_alive if m.startswith("Goblin_")])
    return goblins[0]

def pick_target_mon(participants: dict, pcs_alive: list[str]) -> str:
    """
    Monsters target lowest current HP PC.
    Tie-breaker: lowest init_order (earlier actor) just to be deterministic.
    """
    return sorted(
        pcs_alive,
        key=lambda n: (participants[n]["hp"], participants[n]["init_order"])
    )[0]

# -------------------------
# Main simulation
# -------------------------

def main():
    conn = sqlite3.connect(DB_PATH, timeout=30)
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA busy_timeout = 30000;")
    try:
        conn.execute("PRAGMA journal_mode=WAL;")
    except Exception:
        pass

    # Encounter template id + round cap
    row = conn.execute("""
        SELECT encounter_template_id, round_cap 
        FROM encounter_template 
        WHERE name = ?;""",
        (ENCOUNTER_NAME,)
    ).fetchone()
    if not row:
        raise RuntimeError(f"Encounter template not found: {ENCOUNTER_NAME}")
    et_id, round_cap = row[0], row[1] or ROUND_CAP_DEFAULT

    members = conn.execute("""
        SELECT side, slot_name, pc_id, monster_key
        FROM encounter_template_member
        WHERE encounter_template_id = ?
        ORDER BY side, slot_name;
    """, (et_id,)).fetchall()

    if not members:
        raise RuntimeError("No encounter members found.")

    print(f"Simulating encounter_template_id={et_id} for {NUM_RUNS} runs...")

    for run_n in range(1, NUM_RUNS + 1):
        seed = random.randint(1, 2**31 - 1)
        rng = random.Random(seed)

        # Insert simulation_run placeholder
        cur = conn.execute("""
            INSERT INTO simulation_run
              (encounter_template_id, seed, party_victory, winner, rounds_taken,
               total_damage_party, total_damage_monsters, notes_flags_json)
            VALUES (?, ?, 0, 'timeout', 0, 0, 0, ?);
        """, (et_id, seed, '{"phase":"combat"}'))
        run_id = cur.lastrowid

        # -------------------------
        # Instantiate participants dict keyed by slot_name
        # -------------------------
        participants = {}

        for side, slot_name, pc_id, monster_key in members:
            if pc_id is not None:
                pc = conn.execute("""
                    SELECT pc_id, name, ac, max_hp, dex_mod, attack_bonus, damage_dice, crits_on, features_enabled
                    FROM dim_pc_template
                    WHERE pc_id = ?;
                """, (pc_id,)).fetchone()
                if not pc:
                    raise RuntimeError(f"PC template missing: {pc_id}")
                _, _, ac, hp, dex_mod, atk_bonus, dmg_dice, crits_on, features = pc
                participants[slot_name] = {
                    "side": "party",
                    "template_type": "pc",
                    "pc_id": pc_id,
                    "monster_key": None,
                    "ac": int(ac),
                    "hp_start": int(hp),
                    "hp": int(hp),
                    "init_mod": int(dex_mod),
                    "attack_bonus": int(atk_bonus),
                    "damage_dice": str(dmg_dice),
                    "crits_on": str(crits_on),
                    "features": str(features) if features is not None else "",
                    # counters
                    "damage_dealt": 0,
                    "damage_taken": 0,
                    "attacks": 0,
                    "hits": 0,
                    "crits": 0,
                    # flags
                    "opening_burst_triggered": 0,
                    "hunters_mark_cast": 0,
                    "hunters_mark_bonus_damage": 0,
                }
            else:
                mon = conn.execute("""
                    SELECT monster_key, monster_name, armor_class, hit_points, dex_mod, attack_bonus, damage_dice
                    FROM dim_monster
                    WHERE monster_key = ?;
                """, (monster_key,)).fetchone()
                if not mon:
                    raise RuntimeError(f"Monster missing: monster_key={monster_key}")
                _, _, ac, hp, dex_mod, atk_bonus, dmg_dice = mon
                participants[slot_name] = {
                    "side": "monsters",
                    "template_type": "monster",
                    "pc_id": None,
                    "monster_key": int(monster_key),
                    "ac": int(ac),
                    "hp_start": int(hp),
                    "hp": int(hp),
                    "init_mod": int(dex_mod) if dex_mod is not None else 0,
                    "attack_bonus": int(atk_bonus) if atk_bonus is not None else 0,
                    "damage_dice": str(dmg_dice) if dmg_dice is not None else "1d4+0",
                    "crits_on": "20",  # monsters crit only on nat 20
                    "features": "",
                    # counters
                    "damage_dealt": 0,
                    "damage_taken": 0,
                    "attacks": 0,
                    "hits": 0,
                    "crits": 0,
                    # flags (unused)
                    "opening_burst_triggered": 0,
                    "hunters_mark_cast": 0,
                    "hunters_mark_bonus_damage": 0,
                }

        # -------------------------
        # Initiative
        # -------------------------
        init_list = []
        for name, p in participants.items():
            r = roll(rng, 20)
            p["init_roll_d20"] = r
            p["init_total"] = r + p["init_mod"]
            init_list.append(name)

        rng.shuffle(init_list)
        init_list.sort(key=lambda n: (participants[n]["init_total"], participants[n]["init_mod"]), reverse=True)
        for order, n in enumerate(init_list, start=1):
            participants[n]["init_order"] = order

        # -------------------------
        # Feature state
        # -------------------------
        marked_target = None  # Hunter's Mark target name
        opening_burst_available = True  # Rogue bonus available once

        # First-round tracking
        damage_party_before_first_monster_turn = 0
        monsters_downed_before_first_monster_turn = 0
        party_downed_before_first_player_turn = 0
        first_monster_acted = False
        first_player_acted = False
        bugbear_killed_round = None

        # -------------------------
        # Combat loop
        # -------------------------
        def alive_party():
            return [n for n, p in participants.items() if p["side"] == "party" and p["hp"] > 0]

        def alive_monsters():
            return [n for n, p in participants.items() if p["side"] == "monsters" and p["hp"] > 0]

        winner = "timeout"
        rounds_taken = 0

        for round_no in range(1, round_cap + 1):
            rounds_taken = round_no

            for actor in init_list:
                ap = participants[actor]
                if ap["hp"] <= 0:
                    continue

                # mark the moment the first monster takes a turn
                if ap["side"] == "monsters" and not first_monster_acted:
                    first_monster_acted = True
                if ap["side"] == "party" and not first_player_acted:
                    first_player_acted = True

                pcs_alive = alive_party()
                mons_alive = alive_monsters()

                if not pcs_alive:
                    winner = "monsters"
                    break
                if not mons_alive:
                    winner = "party"
                    break

                # Ranger casts Hunter's Mark on its first turn of round 1
                if actor == "Ranger" and round_no == 1 and ap["hunters_mark_cast"] == 0:
                    # Choose target: Bugbear if alive else first goblin
                    target = pick_target_pc(mons_alive)
                    marked_target = target
                    ap["hunters_mark_cast"] = 1

                # Choose target
                if ap["side"] == "party":
                    target = pick_target_pc(mons_alive)
                else:
                    target = pick_target_mon(participants, pcs_alive)

                tp = participants[target]
                if tp["hp"] <= 0:
                    continue

                # Attack roll
                ap["attacks"] += 1
                d20_roll = roll(rng, 20)

                # Assassinate Advantage rule 
                used_assassinate_advantage = False
                if actor == "Rogue" and round_no == 1:
                    # Advantage if target hasn't taken a turn yet (i.e., target init_order is after Rogue)
                    target_has_not_taken_turn = participants[target]["init_order"] > participants["Rogue"]["init_order"]

                    if target_has_not_taken_turn:
                        d20_roll_2 = roll(rng, 20)
                        d20_roll = max(d20_roll, d20_roll_2)
                        used_assassinate_advantage = True

                hit = (d20_roll + ap["attack_bonus"]) >= tp["ac"]
                crit = is_crit(ap["crits_on"], d20_roll)

                if hit:
                    ap["hits"] += 1
                    if crit:
                        ap["crits"] += 1

                    dmg = roll_damage(rng, ap["damage_dice"], is_crit=crit)

                    # Hunter's Mark bonus damage (Ranger hits marked target)
                    if actor == "Ranger" and marked_target == target:
                        hm = roll_damage(rng, "1d6+0", is_crit=crit)
                        dmg += hm
                        ap["hunters_mark_bonus_damage"] += hm

                    # Opening burst (+2d6 once) if Rogue acts before target's first turn
                    # Opening burst ONLY if Rogue used Assassinate Advantage on this attack, and it hits
                    if actor == "Rogue" and opening_burst_available and used_assassinate_advantage:
                        bonus = roll_damage(rng, "2d6+0", is_crit=False)  # bonus dice do not crit in this simplified model
                        dmg += bonus
                        ap["opening_burst_triggered"] = 1
                        opening_burst_available = False

                    # Apply damage
                    tp["hp"] = max(0, tp["hp"] - dmg)
                    ap["damage_dealt"] += dmg
                    tp["damage_taken"] += dmg

                    # First-round pre-monster-turn tracking
                    if not first_monster_acted and ap["side"] == "party":
                        damage_party_before_first_monster_turn += dmg
                        if tp["hp"] <= 0 and tp["side"] == "monsters":
                            monsters_downed_before_first_monster_turn += 1

                    if not first_player_acted and ap["side"] == "monsters":
                        if tp["hp"] <= 0 and tp["side"] == "party":
                            party_downed_before_first_player_turn += 1

                    # Track bugbear death
                    if target == "Bugbear" and tp["hp"] == 0 and bugbear_killed_round is None:
                        bugbear_killed_round = round_no

                # Check end-of-fight mid-round
                if not alive_party():
                    winner = "monsters"
                    break
                if not alive_monsters():
                    winner = "party"
                    break

            if winner != "timeout":
                break

        party_victory = 1 if winner == "party" else 0

        # -------------------------
        # Write participant_run rows
        # -------------------------
        total_damage_party = 0
        total_damage_monsters = 0

        for name, p in participants.items():
            if p["side"] == "party":
                total_damage_party += p["damage_dealt"]
            else:
                total_damage_monsters += p["damage_dealt"]

            conn.execute("""
                INSERT INTO participant_run
                  (run_id, side, name, template_type, pc_id, monster_key,
                   hp_start, hp_end, alive_end,
                   init_roll_d20, init_mod, init_total, init_order,
                   damage_dealt_total, damage_taken_total, attacks_made, hits_landed, crits_landed,
                   opening_burst_triggered, hunters_mark_cast, hunters_mark_bonus_damage)
                VALUES (?, ?, ?, ?, ?, ?,
                        ?, ?, ?,
                        ?, ?, ?, ?,
                        ?, ?, ?, ?, ?,
                        ?, ?, ?);
            """, (
                run_id,
                p["side"],
                name,
                p["template_type"],
                p["pc_id"],
                p["monster_key"],
                p["hp_start"],
                p["hp"],
                1 if p["hp"] > 0 else 0,
                p["init_roll_d20"],
                p["init_mod"],
                p["init_total"],
                p["init_order"],
                p["damage_dealt"],
                p["damage_taken"],
                p["attacks"],
                p["hits"],
                p["crits"],
                p["opening_burst_triggered"],
                p["hunters_mark_cast"],
                p["hunters_mark_bonus_damage"],
            ))

        # first_round_events
        conn.execute("""
            INSERT INTO first_round_events
              (run_id, damage_party_before_first_monster_turn,
               monsters_downed_before_first_monster_turn,
               party_downed_before_first_player_turn)
            VALUES (?, ?, ?, ?);
        """, (
            run_id,
            damage_party_before_first_monster_turn,
            monsters_downed_before_first_monster_turn,
            party_downed_before_first_player_turn
        ))

        # update simulation_run
        conn.execute("""
            UPDATE simulation_run
            SET party_victory = ?,
                winner = ?,
                rounds_taken = ?,
                total_damage_party = ?,
                total_damage_monsters = ?,
                bugbear_killed_round = ?
            WHERE run_id = ?;
        """, (
            party_victory,
            winner,
            rounds_taken,
            total_damage_party,
            total_damage_monsters,
            bugbear_killed_round,
            run_id
        ))

        conn.commit()

        if run_n % 500 == 0:
            print(f"Run {run_n}/{NUM_RUNS} done (winner={winner}, rounds={rounds_taken})")

    conn.close()
    print("Combat simulations complete.")

if __name__ == "__main__":
    main()
