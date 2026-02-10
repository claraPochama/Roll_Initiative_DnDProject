
--- A) Outcome distribution ---

SELECT winner, COUNT(*) AS n
FROM simulation_run
WHERE notes_flags_json LIKE '%"phase":"combat"%'
GROUP BY winner;
--- A-1) Win rate ---
SELECT AVG(party_victory) AS party_win_rate
FROM simulation_run
WHERE notes_flags_json LIKE '%"phase":"combat"%';

--- A-1) Party average initiative total vs win rate ---
WITH party_init AS (
  SELECT
    sr.run_id,
    AVG(pr.init_total) AS party_init_avg
  FROM simulation_run sr
  JOIN participant_run pr ON pr.run_id = sr.run_id
  WHERE sr.notes_flags_json LIKE '%"phase":"combat"%'
    AND pr.side = 'party'
  GROUP BY sr.run_id
)
SELECT
  ROUND(party_init_avg, 2) AS party_init_avg,
  AVG(sr.party_victory) AS win_rate,
  COUNT(*) AS runs
FROM party_init
JOIN simulation_run sr ON sr.run_id = party_init.run_id
GROUP BY ROUND(party_init_avg, 2)
ORDER BY party_init_avg;


--- B) Does “Rogue beats Bugbear” affect win rate? ---
WITH rb AS (
  SELECT
    r.run_id,
    CASE
      WHEN (r.init_total > b.init_total)
        OR (r.init_total = b.init_total AND r.init_mod > b.init_mod)
      THEN 1 ELSE 0
    END AS rogue_beats_bugbear
  FROM participant_run r
  JOIN participant_run b ON r.run_id = b.run_id
  JOIN simulation_run sr ON sr.run_id = r.run_id
  WHERE sr.notes_flags_json LIKE '%"phase":"combat"%'
    AND r.name = 'Rogue'
    AND b.name = 'Bugbear'
)
SELECT
  rogue_beats_bugbear,
  AVG(sr.party_victory) AS win_rate,
  COUNT(*) AS runs
FROM rb
JOIN simulation_run sr ON sr.run_id = rb.run_id
GROUP BY rogue_beats_bugbear;


--- C) Alpha-strike: damage before first monster turn vs win rate ---
SELECT
  CASE
    WHEN damage_party_before_first_monster_turn < 5 THEN '0-4'
    WHEN damage_party_before_first_monster_turn < 15 THEN '5-14'
    WHEN damage_party_before_first_monster_turn < 25 THEN '15-24'
    ELSE '25+'
  END AS dmg_bucket,
  AVG(sr.party_victory) AS win_rate,
  COUNT(*) AS runs
FROM first_round_events fre
JOIN simulation_run sr ON sr.run_id = fre.run_id
WHERE sr.notes_flags_json LIKE '%"phase":"combat"%'
GROUP BY dmg_bucket
ORDER BY runs DESC;

--- C-1) Discrete Alpha-strike damage data ---
SELECT
  fre.run_id,
  fre.damage_party_before_first_monster_turn,
  fre.monsters_downed_before_first_monster_turn,
  fre.party_downed_before_first_monster_turn,
  sr.party_victory,
  sr.rounds_taken
FROM first_round_events fre
JOIN simulation_run sr ON sr.run_id = fre.run_id
WHERE sr.notes_flags_json LIKE '%"phase":"combat"%';

--- D) Did opening burst correlate with winning? ---
SELECT
  opening_burst_triggered,
  AVG(sr.party_victory) AS win_,
  AVG(sr.rounds_taken) AS avg_rounds,
  COUNT(*) AS runsrate
FROM participant_run pr
JOIN simulation_run sr ON sr.run_id = pr.run_id
WHERE sr.notes_flags_json LIKE '%"phase":"combat"%'
  AND pr.name = 'Rogue'
GROUP BY opening_burst_triggered;

--- E) Average damage dealt per participant (overall) ---
SELECT
  pr.side,
  pr.name,
  AVG(pr.damage_dealt_total) AS avg_damage_dealt,
  AVG(pr.damage_taken_total) AS avg_damage_taken,
  AVG(pr.hits_landed) AS avg_hits,
  AVG(pr.crits_landed) AS avg_crits,
  COUNT(*) AS runs
FROM participant_run pr
JOIN simulation_run sr ON sr.run_id = pr.run_id
WHERE sr.notes_flags_json LIKE '%"phase":"combat"%'
GROUP BY pr.side, pr.name
ORDER BY avg_damage_dealt DESC;

--- F) Party vs Monsters average total damage (per run) ---
SELECT
  AVG(sr.total_damage_party) AS avg_party_total_damage,
  AVG(sr.total_damage_monsters) AS avg_monsters_total_damage,
  AVG(sr.rounds_taken) AS avg_rounds,
  COUNT(*) AS runs
FROM simulation_run sr
WHERE sr.notes_flags_json LIKE '%"phase":"combat"%';

--- G) Average damage dealt by participant, split by win/loss ---
SELECT
  sr.party_victory,
  pr.side,
  pr.name,
  AVG(pr.damage_dealt_total) AS avg_damage_dealt,
  AVG(pr.damage_taken_total) AS avg_damage_taken,
  COUNT(*) AS runs
FROM participant_run pr
JOIN simulation_run sr ON sr.run_id = pr.run_id
WHERE sr.notes_flags_json LIKE '%"phase":"combat"%'
GROUP BY sr.party_victory, pr.side, pr.name
ORDER BY sr.party_victory DESC, pr.side, avg_damage_dealt DESC;

--- H) Ranger: average Hunter’s Mark bonus contribution
SELECT
  AVG(hunters_mark_cast) AS hm_cast_rate,
  AVG(hunters_mark_bonus_damage) AS avg_hm_bonus_damage,
  AVG(damage_dealt_total) AS avg_total_damage,
  AVG(CASE WHEN damage_dealt_total > 0 THEN 1.0 * hunters_mark_bonus_damage / damage_dealt_total ELSE 0 END) AS avg_hm_share
FROM participant_run pr
JOIN simulation_run sr ON sr.run_id = pr.run_id
WHERE sr.notes_flags_json LIKE '%"phase":"combat"%'
  AND pr.name = 'Ranger';

--- I) Rogue: average damage when burst triggers vs not ---
SELECT
  opening_burst_triggered,
  AVG(damage_dealt_total) AS avg_rogue_damage,
  AVG(crits_landed) AS avg_rogue_crits,
  AVG(hits_landed) AS avg_rogue_hits,
  COUNT(*) AS runs
FROM participant_run pr
JOIN simulation_run sr ON sr.run_id = pr.run_id
WHERE sr.notes_flags_json LIKE '%"phase":"combat"%'
  AND pr.name = 'Rogue'
GROUP BY opening_burst_triggered;

--- J) Monsters: average damage per monster type (Goblin vs Bugbear) ---
SELECT
  CASE
    WHEN pr.name LIKE 'Goblin_%' THEN 'Goblin'
    WHEN pr.name = 'Bugbear' THEN 'Bugbear'
    ELSE pr.name
  END AS monster_type,
  AVG(pr.damage_dealt_total) AS avg_damage_dealt,
  AVG(pr.damage_taken_total) AS avg_damage_taken,
  AVG(pr.alive_end) AS survival_rate,
  COUNT(*) AS rows
FROM participant_run pr
JOIN simulation_run sr ON sr.run_id = pr.run_id
WHERE sr.notes_flags_json LIKE '%"phase":"combat"%'
  AND pr.side = 'monsters'
GROUP BY monster_type
ORDER BY avg_damage_dealt DESC;

--- K) Survival Rate for everyone ---
SELECT
  side,
  name,
  COUNT(*)                         AS runs,
  ROUND(AVG(alive_end), 4)         AS survival_rate
FROM participant_run
GROUP BY side, name
ORDER BY side, survival_rate DESC, name;


--- (One table version) ---
SELECT
  sr.run_id,
  sr.party_victory,
  sr.rounds_taken,
  pr.side,
  pr.name,
  pr.init_total,
  pr.init_order,
  pr.damage_dealt_total,
  pr.damage_taken_total,
  pr.hits_landed,
  pr.crits_landed,
  pr.opening_burst_triggered,
  pr.hunters_mark_cast,
  pr.hunters_mark_bonus_damage
FROM participant_run pr
JOIN simulation_run sr ON sr.run_id = pr.run_id
WHERE sr.notes_flags_json LIKE '%"phase":"combat"%';


--- Last check ---
SELECT MIN(rounds_taken), MAX(rounds_taken)
FROM simulation_run
WHERE notes_flags_json LIKE '%"phase":"combat"%';


SELECT monsters_downed_before_first_monster_turn
fROM first_round_events
GROUP BY monsters_downed_before_first_monster_turn;