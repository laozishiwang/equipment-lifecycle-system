-- Preserve code and description as they were when a repair was recorded.
SET SESSION lock_wait_timeout=5;
CREATE TABLE IF NOT EXISTS ems_repair_fault_code (
 repair_id BIGINT NOT NULL PRIMARY KEY,
 fault_code_id BIGINT NOT NULL,
 code VARCHAR(64) NOT NULL, category VARCHAR(80) NOT NULL, part VARCHAR(80) NOT NULL, symptom VARCHAR(80) NOT NULL,
 CONSTRAINT fk_repair_fault_code_repair FOREIGN KEY (repair_id) REFERENCES ems_work_order_repair(id),
 CONSTRAINT fk_repair_fault_code_catalog FOREIGN KEY (fault_code_id) REFERENCES ems_fault_code(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;
