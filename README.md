{WIP!}
Roll Initiative: A Data-Driven Analysis of First-Mover Advantage

*Executive Summary*

“... Roll initiative!” says your dungeon master.

In turn-based games, this single moment often decides the tempo of everything that follows. 
It begins the same way: a dice roll, a number, to determine an order.
Sometimes the fastest character goes first; Sometimes they don’t. It looks random and fair,

This project explores initiative as a measurable system. By simulating thousands of combat encounters and analyzing their outcomes, it examines how initiative order shapes combat outcomes, damage, and win rate. 


*What each file does*

SQL

•	sql/schema.sql: 
Creates all database tables and constraints (dimensions + fact tables).

•	sql/analysis_queries.sql: 
Saved queries used to answer the research questions (win rate, survival, early damage, etc.).

Database setup

•	src/bootstrap_new_db.py: 
Creates a fresh SQLite database and applies schema.sql.

•	src/db_healthcheck.py: 
Quick checks that tables exist and row counts look sane (useful after ETL and after simulation).

ETL (load & clean CSVs into dimension tables)

•	src/etl_load_pc_templates.py: 
Loads party templates from CSV into the DB (first-time load).

•	src/etl_load_pc_templates_upsert.py: 
Same goal as above, but supports re-running safely (updates existing rows instead of duplicating).

•	src/etl_load_monsters_goblin_bugbear.py: 
Loads the monster templates needed for the v1 encounter (Goblins + Bugbear).

Encounter setup

•	src/seed_encounter_members.py: 
Creates the fixed encounter template (3 PCs vs 4 Goblins + 1 Bugbear) and inserts encounter members.

Simulation

•	src/simulate_combat.py: 
Runs N simulations (e.g., 5,000+) and writes results into:

simulation_run (one row per battle), 
participant_run (one row per participant per battle), 
first_round_events (early damage / early downs). 

Analysis & visuals

•	tableau/dashboard.twbx: 
Tableau workbook using the SQLite DB (or extracted CSVs) to build final visuals.
