-- Rollback for SIMGEN production-freshness data (generated).
-- Deletes ONLY generated rows. Run against the noted DB.

USE sl323;
DELETE FROM st_river_r WHERE tm > '2026-06-11 00:00:00';
USE sl323;
DELETE FROM st_pptn_r WHERE tm > '2026-06-11 00:00:00';
USE sl323;
DELETE FROM st_pump_r WHERE tm > '2026-06-11 00:00:00';
USE sl323;
DELETE FROM st_pump_pa WHERE tm > '2026-06-11 00:00:00';
USE sl323;
DELETE FROM st_gate_r WHERE tm > '2026-04-01 00:00:00';
USE sl323;
DELETE FROM st_was_r WHERE tm > '2026-06-11 00:00:00';
USE sl325;
DELETE FROM wq_pcp_d WHERE bak1='SIMGEN';
