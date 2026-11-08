-- Add optional per-repair diagnosis without rewriting existing repair history.
SET SESSION lock_wait_timeout=5;
CREATE TABLE IF NOT EXISTS ems_work_order_repair_diagnosis (
 repair_id BIGINT NOT NULL PRIMARY KEY,
 diagnosis VARCHAR(2000) NOT NULL,
 CONSTRAINT fk_repair_diagnosis_repair FOREIGN KEY (repair_id) REFERENCES ems_work_order_repair(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
