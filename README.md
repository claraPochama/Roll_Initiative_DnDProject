# Roll Initiative: A Data-Driven Analysis of First-Mover Advantage in D&D 5E Rules


This project explores initiative by running 5000 combat encounters through a controlled simulation model to examine how action order shapes combat outcomes, damage, and win rate. 
The outcomes are analysed and presented with SQL, Python, and Tableau. 

The simulation results confirm that initiative order positively correlates with win rate, but they also reveal that victory emerges from interacting factors rather than order alone. The effect depends on a chain of interactions: early turn order influences early burst damage, which changes who gets downed first; that survivability shift then determines total party damage and ultimately the outcome. 

This project taught me two things: (1) “Initiative advantage” is not a standalone variable, but mediated by model rules (targeting, burst windows, and snowball effects). (2) Simulation conclusions must be framed as scenario-specific, not as general game balance claims. 

Next, I plan to stress-test the model by randomizing or weighting monster targeting to measure how robust the initiative–win relationship remains.


## Data Sources
Static monster and equipment data were obtained from the Kaggle dataset [“Dungeons & Dragons” (shadowtime2000)](https://www.kaggle.com/datasets/shadowtime2000/dungeons-dragons/data), which aggregates structured data derived from the [D&D 5e API](https://www.dnd5eapi.co/), licensed under the MIT License. 
Only fields relevant to combat simulation (e.g., AC, hit points, attack bonuses, damage dice) were selected and curated for this project. 


## What each file does

### SQL

•	sql/schema.sql: 
Creates all database tables and constraints (dimensions + fact tables).

•	sql/analysis_queries.sql: 
Saved queries used to answer the research questions (win rate, survival, early damage, etc.).

### Database setup

•	src/bootstrap_new_db.py: 
Creates a fresh SQLite database and applies schema.sql.

•	src/db_healthcheck.py: 
Quick checks that tables exist and row counts look sane (useful after ETL and after simulation).

### ETL (load & clean CSVs into dimension tables)

•	src/etl_load_pc_templates.py: 
Loads party templates from CSV into the DB (first-time load).

•	src/etl_load_pc_templates_upsert.py: 
Same goal as above, but supports re-running safely (updates existing rows instead of duplicating).

•	src/etl_load_monsters_goblin_bugbear.py: 
Loads the monster templates needed for the v1 encounter (Goblins + Bugbear).

### Encounter setup

•	src/seed_encounter_members.py: 
Creates the fixed encounter template (3 PCs vs 4 Goblins + 1 Bugbear) and inserts encounter members.

### Simulation

•	src/simulate_combat.py: 
Runs N simulations (e.g., 5,000+) and writes results into:

simulation_run (one row per battle), 
participant_run (one row per participant per battle), 
first_round_events (early damage / early downs). 

### Analysis & visuals

•	tableau/dashboard.twbx: 
Tableau workbook using the SQLite DB (or extracted CSVs) to build final visuals.
