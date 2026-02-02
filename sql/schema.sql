-- schema.sql
-- D&D 5e-inspired initiative study (SQLite)
-- Facts: simulation_run, participant_run, first_round_events
-- Dims: dim_monster, dim_equipment_weapon, dim_class (optional), dim_pc_template
-- Templates: encounter_template, encounter_template_member

PRAGMA foreign_keys = ON;

-- -------------------------
-- Dimension tables
-- -------------------------

-- Minimal class dimension (optional; you can populate from classes.csv if you want)
CREATE TABLE IF NOT EXISTS dim_class (
  class_key       INTEGER PRIMARY KEY,
  class_name      TEXT NOT NULL UNIQUE
);

-- Weapons only (curated from equipment.csv)
CREATE TABLE IF NOT EXISTS dim_equipment_weapon (
  weapon_key      INTEGER PRIMARY KEY,
  weapon_name     TEXT NOT NULL UNIQUE,
  weapon_type     TEXT,              -- melee/ranged
  damage_dice     TEXT,              -- e.g. "1d8"
  damage_type     TEXT,              -- piercing/slashing/etc
  properties_json TEXT               -- optional, store as JSON string
);

-- Monsters (curated from monsters.csv). Keep flexible: CSVs vary a lot.
CREATE TABLE IF NOT EXISTS dim_monster (
  monster_key      INTEGER PRIMARY KEY,
  monster_name     TEXT NOT NULL UNIQUE,
  challenge_rating REAL,
  armor_class      INTEGER,
  hit_points       INTEGER,
  dex_mod          INTEGER,
  attack_bonus     INTEGER,           -- if you curate a "primary attack"
  damage_dice      TEXT,              -- e.g. "1d6+2"
  actions_json     TEXT               -- optional: raw actions from CSV as JSON-ish text
);

-- PC templates you control (from pc_templates.csv)
CREATE TABLE IF NOT EXISTS dim_pc_template (
  pc_id             TEXT PRIMARY KEY,  -- e.g. "PC_RGR_GLOOMSTALKER_L3"
  name              TEXT NOT NULL,
  class_name        TEXT NOT NULL,
  subclass          TEXT,
  level             INTEGER NOT NULL,
  proficiency_bonus INTEGER NOT NULL,
  str               INTEGER,
  dex               INTEGER,
  con               INTEGER,
  int               INTEGER,
  wis               INTEGER,
  cha               INTEGER,
  str_mod           INTEGER,
  dex_mod           INTEGER,
  con_mod           INTEGER,
  armor_name        TEXT,
  ac                INTEGER NOT NULL,
  max_hp            INTEGER NOT NULL,
  weapon_name       TEXT NOT NULL,
  attack_ability    TEXT NOT NULL,     -- STR/DEX
  attack_bonus      INTEGER NOT NULL,
  damage_dice       TEXT NOT NULL,     -- e.g. "1d8+3"
  crits_on          TEXT NOT NULL,     -- "20" or "19-20"
  features_enabled  TEXT              -- semi-structured flags
);

-- -------------------------
-- Encounter templates
-- -------------------------

CREATE TABLE IF NOT EXISTS encounter_template (
  encounter_template_id INTEGER PRIMARY KEY,
  name                  TEXT NOT NULL UNIQUE,
  description           TEXT,
  target_selection_pc   TEXT NOT NULL,  -- e.g. "bugbear_first"
  target_selection_mon  TEXT NOT NULL,  -- e.g. "lowest_hp"
  round_cap             INTEGER NOT NULL DEFAULT 20,
  created_at_utc        TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);

-- Each row defines one participant "slot" in the encounter template.
-- Use pc_id for party members, monster_key for monsters.
CREATE TABLE IF NOT EXISTS encounter_template_member (
  encounter_template_id INTEGER NOT NULL,
  side                  TEXT NOT NULL CHECK (side IN ('party','monsters')),
  slot_name             TEXT NOT NULL, -- e.g. "Fighter", "Goblin_1"
  pc_id                 TEXT,          -- FK to dim_pc_template (party)
  monster_key           INTEGER,       -- FK to dim_monster (monsters)
  quantity              INTEGER NOT NULL DEFAULT 1, -- usually 1 per slot; can be >1 if you prefer grouping
  PRIMARY KEY (encounter_template_id, slot_name),
  FOREIGN KEY (encounter_template_id) REFERENCES encounter_template(encounter_template_id) ON DELETE CASCADE,
  FOREIGN KEY (pc_id) REFERENCES dim_pc_template(pc_id),
  FOREIGN KEY (monster_key) REFERENCES dim_monster(monster_key)
);

-- -------------------------
-- Simulation facts
-- -------------------------

CREATE TABLE IF NOT EXISTS simulation_run (
  run_id                 INTEGER PRIMARY KEY,
  encounter_template_id   INTEGER NOT NULL,
  seed                   INTEGER,              -- optional: store PRNG seed for reproducibility
  party_victory           INTEGER NOT NULL CHECK (party_victory IN (0,1)),
  winner                 TEXT NOT NULL CHECK (winner IN ('party','monsters','timeout')),
  rounds_taken            INTEGER NOT NULL,
  total_damage_party      INTEGER NOT NULL DEFAULT 0,
  total_damage_monsters   INTEGER NOT NULL DEFAULT 0,
  bugbear_killed_round    INTEGER,              -- NULL if never killed / or if no bugbear
  first_monster_turn_round INTEGER DEFAULT 1,   -- sanity check field
  notes_flags_json        TEXT,                 -- JSON text: {"opening_burst_used":true,"hunters_mark_active":true}
  created_at_utc          TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
  FOREIGN KEY (encounter_template_id) REFERENCES encounter_template(encounter_template_id)
);

CREATE TABLE IF NOT EXISTS participant_run (
  run_id                 INTEGER NOT NULL,
  side                   TEXT NOT NULL CHECK (side IN ('party','monsters')),
  name                   TEXT NOT NULL,                 -- "Rogue", "Goblin_3"
  template_type          TEXT NOT NULL CHECK (template_type IN ('pc','monster')),
  pc_id                  TEXT,                          -- if pc
  monster_key            INTEGER,                       -- if monster
  hp_start               INTEGER NOT NULL,
  hp_end                 INTEGER NOT NULL,
  alive_end              INTEGER NOT NULL CHECK (alive_end IN (0,1)),
  -- initiative
  init_roll_d20          INTEGER NOT NULL CHECK (init_roll_d20 BETWEEN 1 AND 20),
  init_mod               INTEGER NOT NULL,
  init_total             INTEGER NOT NULL,
  init_order             INTEGER NOT NULL,              -- 1 = acts first
  -- performance
  damage_dealt_total     INTEGER NOT NULL DEFAULT 0,
  damage_taken_total     INTEGER NOT NULL DEFAULT 0,
  attacks_made           INTEGER NOT NULL DEFAULT 0,
  hits_landed            INTEGER NOT NULL DEFAULT 0,
  crits_landed           INTEGER NOT NULL DEFAULT 0,
  -- feature flags / counters (only meaningful for some PCs)
  opening_burst_triggered  INTEGER NOT NULL DEFAULT 0 CHECK (opening_burst_triggered IN (0,1)),
  hunters_mark_cast        INTEGER NOT NULL DEFAULT 0 CHECK (hunters_mark_cast IN (0,1)),
  hunters_mark_bonus_damage INTEGER NOT NULL DEFAULT 0,
  PRIMARY KEY (run_id, side, name),
  FOREIGN KEY (run_id) REFERENCES simulation_run(run_id) ON DELETE CASCADE,
  FOREIGN KEY (pc_id) REFERENCES dim_pc_template(pc_id),
  FOREIGN KEY (monster_key) REFERENCES dim_monster(monster_key)
);

-- Optional but powerful for your initiative questions
CREATE TABLE IF NOT EXISTS first_round_events (
  run_id                                   INTEGER PRIMARY KEY,
  damage_party_before_first_monster_turn    INTEGER NOT NULL DEFAULT 0,
  monsters_downed_before_first_monster_turn INTEGER NOT NULL DEFAULT 0,
  party_downed_before_first_monster_turn    INTEGER NOT NULL DEFAULT 0,
  FOREIGN KEY (run_id) REFERENCES simulation_run(run_id) ON DELETE CASCADE
);

-- -------------------------
-- Helpful indexes
-- -------------------------
CREATE INDEX IF NOT EXISTS idx_simrun_encounter ON simulation_run(encounter_template_id);
CREATE INDEX IF NOT EXISTS idx_participant_side ON participant_run(side);
CREATE INDEX IF NOT EXISTS idx_participant_initorder ON participant_run(init_order);
CREATE INDEX IF NOT EXISTS idx_participant_template ON participant_run(template_type, pc_id, monster_key);
